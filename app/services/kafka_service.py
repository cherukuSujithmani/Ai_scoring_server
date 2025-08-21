# app/services/kafka_service.py
import asyncio
import json
import logging
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from app.models.dex_model import DexReputationModel
from app.utils.json_utils import json_serializer, json_deserializer
from app.services.stats import stats

logger = logging.getLogger(__name__)

class KafkaService:
    def __init__(self, brokers: str, consume_topic: str, produce_topic: str, group_id: str = "scoring-service"):
        self.brokers = brokers
        self.consume_topic = consume_topic
        self.produce_topic = produce_topic
        self.group_id = group_id
        self.consumer = None
        self.producer = None
        self.model = DexReputationModel()  # load ML model

    async def start(self):
        loop = asyncio.get_event_loop()

        # Producer setup
        self.producer = AIOKafkaProducer(
            loop=loop,
            bootstrap_servers=self.brokers,
            value_serializer=json_serializer,
        )
        await self.producer.start()

        # Consumer setup
        self.consumer = AIOKafkaConsumer(
            self.consume_topic,
            loop=loop,
            bootstrap_servers=self.brokers,
            group_id=self.group_id,
            value_deserializer=json_deserializer,
            auto_offset_reset="earliest"
        )
        await self.consumer.start()

        logger.info("Kafka service started. Listening for messages...")
        asyncio.create_task(self.consume())

    async def consume(self):
        try:
            async for msg in self.consumer:
                wallet_data = msg.value
                logger.debug(f"Received message: {wallet_data}")
                stats.total_consumed += 1

                try:
                    score = self.model.score_wallet(wallet_data)
                    output = {
                        "wallet": wallet_data.get("wallet"),
                        "score": score,
                    }

                    await self.produce(output)
                    stats.total_scored += 1

                except Exception as e:
                    logger.exception(f"Error processing wallet data: {e}")
                    stats.total_failed += 1

        except Exception as e:
            logger.exception(f"Consumer crashed: {e}")

    async def produce(self, message: dict):
        try:
            await self.producer.send_and_wait(self.produce_topic, message)
            logger.debug(f"Produced message: {message}")
            stats.total_produced += 1
        except Exception as e:
            logger.exception(f"Failed to produce message: {e}")

    async def stop(self):
        if self.consumer:
            await self.consumer.stop()
        if self.producer:
            await self.producer.stop()
        logger.info("Kafka service stopped.")
