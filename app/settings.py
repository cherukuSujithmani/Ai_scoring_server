# app/settings.py
import os
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables with defaults.
    """

    # Kafka
    kafka_bootstrap_servers: str = Field("localhost:9092", env="KAFKA_BOOTSTRAP_SERVERS")
    kafka_topic: str = Field("wallet-transactions", env="KAFKA_TOPIC")
    kafka_group_id: str = Field("scoring-service", env="KAFKA_GROUP_ID")
    kafka_auto_offset_reset: str = Field("earliest", env="KAFKA_AUTO_OFFSET_RESET")

    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: str = Field("logs/app.log", env="LOG_FILE")

    # Service
    service_name: str = Field("defi-reputation-service", env="SERVICE_NAME")
    environment: str = Field("development", env="ENVIRONMENT")

    # AI / Model config
    model_path: str = Field("models/reputation_model.pkl", env="MODEL_PATH")
    scoring_threshold: float = Field(0.5, env="SCORING_THRESHOLD")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Instantiate settings for app-wide use
settings = Settings()

# Example usage
if __name__ == "__main__":
    print("Kafka broker:", settings.kafka_bootstrap_servers)
    print("Kafka topic:", settings.kafka_topic)
    print("Log level:", settings.log_level)
    print("Model path:", settings.model_path)
