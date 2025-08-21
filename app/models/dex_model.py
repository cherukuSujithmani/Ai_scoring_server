from __future__ import annotations
import time
from datetime import datetime
from typing import Dict, List, Any, Tuple

import numpy as np
import pandas as pd


class DexModel:
    """
    Production-ready extraction of the DEX reputation model from the notebook.
    Exposes:
      - preprocess_dex_transactions()
      - calculate_lp_features()/calculate_lp_score()
      - calculate_swap_features()/calculate_swap_score()
      - calculate_final_score()
      - process_wallet_complete()  -> (final_score, features_dict)
      - process_wallet()           -> success/failure payload ready for Kafka
    """

    # ---------------------------
    # Preprocessing
    # ---------------------------
    @staticmethod
    def preprocess_dex_transactions(wallet_data: Dict) -> pd.DataFrame:
        rows: List[Dict[str, Any]] = []
        wallet_address = wallet_data.get("wallet_address")

        for category_data in wallet_data.get("data", []):
            if category_data.get("protocolType") != "dexes":
                continue

            for tx in category_data.get("transactions", []):
                row = {
                    "wallet_address": wallet_address,
                    "document_id": tx.get("document_id"),
                    "action": tx.get("action"),
                    "timestamp": tx.get("timestamp"),
                    "protocol": tx.get("protocol", ""),
                    "pool_id": tx.get("poolId", ""),
                    "pool_name": tx.get("poolName", ""),
                }

                action = tx.get("action")
                if action == "swap":
                    token_in = tx.get("tokenIn", {}) or {}
                    token_out = tx.get("tokenOut", {}) or {}
                    row["amount_usd"] = max(
                        float(token_in.get("amountUSD", 0.0) or 0.0),
                        float(token_out.get("amountUSD", 0.0) or 0.0),
                    )
                    row["token_in_symbol"] = token_in.get("symbol", "")
                    row["token_out_symbol"] = token_out.get("symbol", "")

                elif action in ("deposit", "withdraw"):
                    token0 = tx.get("token0", {}) or {}
                    token1 = tx.get("token1", {}) or {}
                    row["amount_usd"] = float(token0.get("amountUSD", 0.0) or 0.0) + float(
                        token1.get("amountUSD", 0.0) or 0.0
                    )
                    row["token0_symbol"] = token0.get("symbol", "")
                    row["token1_symbol"] = token1.get("symbol", "")

                rows.append(row)

        df = pd.DataFrame(rows)
        if not df.empty and "timestamp" in df:
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="s", errors="coerce")
        return df

    # ---------------------------
    # LP features & score
    # ---------------------------
    @staticmethod
    def calculate_holding_time(deposits: pd.DataFrame, withdraws: pd.DataFrame) -> float:
        if deposits.empty:
            return 0.0

        holding_times: List[float] = []
        current_time = datetime.now().timestamp()

        for _, deposit in deposits.iterrows():
            deposit_time = float(deposit["timestamp"])
            future_withdraws = withdraws[withdraws["timestamp"] > deposit_time]
            if not future_withdraws.empty:
                withdraw_time = float(future_withdraws["timestamp"].min())
                holding_time_days = (withdraw_time - deposit_time) / 86400.0
            else:
                holding_time_days = (current_time - deposit_time) / 86400.0
            holding_times.append(holding_time_days)

        return float(np.mean(holding_times)) if holding_times else 0.0

    @classmethod
    def calculate_lp_features(cls, df: pd.DataFrame) -> Dict[str, float]:
        if df.empty:
            return {}

        deposits = df[df["action"] == "deposit"]
        withdraws = df[df["action"] == "withdraw"]

        total_deposit_usd = float(deposits["amount_usd"].sum()) if not deposits.empty else 0.0
        total_withdraw_usd = float(withdraws["amount_usd"].sum()) if not withdraws.empty else 0.0
        num_deposits = int(len(deposits))
        num_withdraws = int(len(withdraws))
        withdraw_ratio = (total_withdraw_usd / total_deposit_usd) if total_deposit_usd > 0 else 0.0
        account_age_days = (
            (float(df["timestamp"].max()) - float(df["timestamp"].min())) / 86400.0 if not df.empty else 0.0
        )
        avg_hold_time_days = cls.calculate_holding_time(deposits, withdraws)
        unique_pools = int(df["pool_id"].nunique())

        return {
            "total_deposit_usd": total_deposit_usd,
            "total_withdraw_usd": total_withdraw_usd,
            "num_deposits": num_deposits,
            "num_withdraws": num_withdraws,
            "withdraw_ratio": withdraw_ratio,
            "avg_hold_time_days": float(avg_hold_time_days),
            "account_age_days": float(account_age_days),
            "unique_pools": unique_pools,
        }

    @staticmethod
    def calculate_lp_score(features: Dict[str, float]) -> Tuple[float, Dict[str, Any]]:
        if not features:
            return 0.0, {}

        volume_score = min(features["total_deposit_usd"] / 10000.0 * 300.0, 300.0)
        frequency_score = min(features["num_deposits"] * 20.0, 200.0)
        retention_score = max(0.0, (1.0 - features["withdraw_ratio"]) * 250.0)
        holding_score = min(features["avg_hold_time_days"] / 30.0 * 150.0, 150.0)
        diversity_score = min(features["unique_pools"] * 20.0, 100.0)

        total = volume_score + frequency_score + retention_score + holding_score + diversity_score
        breakdown = {
            "volume_score": volume_score,
            "frequency_score": frequency_score,
            "retention_score": retention_score,
            "holding_score": holding_score,
            "diversity_score": diversity_score,
            "total_lp_score": total,
        }
        return float(total), breakdown

    # ---------------------------
    # Swap features & score
    # ---------------------------
    @staticmethod
    def _token_diversity(swaps: pd.DataFrame) -> int:
        if swaps.empty:
            return 0
        stable_tokens = {"USDC", "USDT", "DAI", "LUSD", "USDP", "TUSD", "FRAX"}
        tokens_in = set(swaps.get("token_in_symbol", pd.Series(dtype=str)).dropna())
        tokens_out = set(swaps.get("token_out_symbol", pd.Series(dtype=str)).dropna())
        all_tokens = tokens_in.union(tokens_out)
        stable_count = len(all_tokens.intersection(stable_tokens))
        volatile_count = len(all_tokens) - stable_count
        diversity_score = stable_count * 10 + volatile_count * 15
        return int(min(diversity_score, 150))

    @staticmethod
    def _swap_frequency(swaps: pd.DataFrame) -> float:
        if swaps.empty or len(swaps) < 2:
            return 0.0
        srt = swaps.sort_values("timestamp")
        diffs = srt["timestamp"].diff().dropna()
        hours = diffs / 3600.0
        avg = float(hours.mean())
        if avg <= 1:
            return 100.0
        elif avg <= 24:
            return 80.0
        elif avg <= 168:
            return 60.0
        elif avg <= 720:
            return 40.0
        else:
            return 20.0

    @classmethod
    def calculate_swap_features(cls, df: pd.DataFrame) -> Dict[str, float]:
        if df.empty:
            return {}

        swaps = df[df["action"] == "swap"]
        if swaps.empty:
            return {
                "total_swap_volume": 0.0,
                "num_swaps": 0,
                "unique_pools_swapped": 0,
                "avg_swap_size": 0.0,
                "token_diversity_score": 0,
                "swap_frequency_score": 0.0,
            }

        total_swap_volume = float(swaps["amount_usd"].sum())
        num_swaps = int(len(swaps))
        unique_pools_swapped = int(swaps["pool_id"].nunique())
        avg_swap_size = total_swap_volume / num_swaps if num_swaps > 0 else 0.0
        token_diversity_score = cls._token_diversity(swaps)
        swap_frequency_score = cls._swap_frequency(swaps)

        return {
            "total_swap_volume": total_swap_volume,
            "num_swaps": num_swaps,
            "unique_pools_swapped": unique_pools_swapped,
            "avg_swap_size": float(avg_swap_size),
            "token_diversity_score": int(token_diversity_score),
            "swap_frequency_score": float(swap_frequency_score),
        }

    @staticmethod
    def calculate_swap_score(features: Dict[str, float]) -> Tuple[float, Dict[str, Any]]:
        if not features:
            return 0.0, {}

        volume_score = min(features["total_swap_volume"] / 50000.0 * 250.0, 250.0)
        frequency_score = min(features["num_swaps"] * 10.0, 200.0)
        diversity_score = float(features["token_diversity_score"])
        activity_score = float(features["swap_frequency_score"])
        pool_diversity_score = min(features["unique_pools_swapped"] * 25.0, 100.0)

        total = volume_score + frequency_score + diversity_score + activity_score + pool_diversity_score
        breakdown = {
            "volume_score": volume_score,
            "frequency_score": frequency_score,
            "diversity_score": diversity_score,
            "activity_score": activity_score,
            "pool_diversity_score": pool_diversity_score,
            "total_swap_score": total,
        }
        return float(total), breakdown

    # ---------------------------
    # Tagging, Combine, End-to-end
    # ---------------------------
    @staticmethod
    def generate_user_tags(lp_features: Dict, swap_features: Dict) -> List[str]:
        tags: List[str] = []

        # LP levels
        td = lp_features.get("total_deposit_usd", 0)
        if td > 100000:
            tags.append("Whale LP")
        elif td > 10000:
            tags.append("Large LP")
        elif td > 1000:
            tags.append("Medium LP")
        elif td > 0:
            tags.append("Small LP")

        # Holding behavior
        ht = lp_features.get("avg_hold_time_days", 0)
        if ht > 90:
            tags.append("Long-term Holder")
        elif ht > 30:
            tags.append("Medium-term Holder")
        elif ht > 0:
            tags.append("Short-term Holder")

        # Swap volume
        sv = swap_features.get("total_swap_volume", 0)
        if sv > 500000:
            tags.append("Whale Trader")
        elif sv > 50000:
            tags.append("Large Trader")
        elif sv > 5000:
            tags.append("Active Trader")
        elif sv > 0:
            tags.append("Casual Trader")

        # Frequency tags
        if swap_features.get("num_swaps", 0) > 100:
            tags.append("High Frequency Trader")
        elif swap_features.get("num_swaps", 0) > 20:
            tags.append("Regular Trader")

        # Diversity
        if swap_features.get("token_diversity_score", 0) > 100:
            tags.append("Diversified Trader")
        elif lp_features.get("unique_pools", 0) > 3:
            tags.append("Multi-Pool LP")

        return tags

    @classmethod
    def calculate_final_score(
        cls, lp_score: float, swap_score: float, lp_features: Dict, swap_features: Dict
    ) -> Tuple[float, Dict[str, Any]]:
        lp_weight, swap_weight = 0.6, 0.4
        final_score = lp_score * lp_weight + swap_score * swap_weight
        user_tags = cls.generate_user_tags(lp_features, swap_features)

        complete_features = {
            **lp_features,
            **swap_features,
            "user_tags": user_tags,
            "lp_score": float(lp_score),
            "swap_score": float(swap_score),
            "final_score": float(final_score),
        }
        return float(final_score), complete_features

    # High-level pipeline (notebook parity)
    @classmethod
    def process_wallet_complete(cls, wallet_data: Dict) -> Tuple[float, Dict[str, Any], pd.DataFrame]:
        df = cls.preprocess_dex_transactions(wallet_data)
        if df.empty:
            return 0.0, {"error": "No valid transactions found"}, df

        lp_features = cls.calculate_lp_features(df)
        lp_score, lp_breakdown = cls.calculate_lp_score(lp_features)

        swap_features = cls.calculate_swap_features(df)
        swap_score, swap_breakdown = cls.calculate_swap_score(swap_features)

        final_score, complete_features = cls.calculate_final_score(
            lp_score, swap_score, lp_features, swap_features
        )
        complete_features["score_breakdown"] = {
            "lp_breakdown": lp_breakdown,
            "swap_breakdown": swap_breakdown,
        }
        return float(final_score), complete_features, df

    # ---------------------------
    # Payload builders for Kafka
    # ---------------------------
    @staticmethod
    def _choose_timestamp(df: pd.DataFrame, default_ts: int | None = None) -> int:
        if df is not None and not df.empty and "timestamp" in df:
            try:
                return int(df["timestamp"].min())
            except Exception:
                pass
        return int(default_ts or int(time.time()))

    @classmethod
    def process_wallet(cls, wallet_data: Dict) -> Tuple[Dict[str, Any], Dict[str, Any] | None]:
        """
        Returns (success_payload, failure_payload)
        Only one of them will be non-None.
        """
        t0 = time.time()
        try:
            z, features, df = cls.process_wallet_complete(wallet_data)
            if "error" in features:
                processing_ms = int((time.time() - t0) * 1000)
                failure = {
                    "wallet_address": wallet_data.get("wallet_address"),
                    "error": features["error"],
                    "timestamp": cls._choose_timestamp(df),
                    "processing_time_ms": processing_ms,
                    "categories": [
                        {
                            "category": "dexes",
                            "error": features["error"],
                            "transaction_count": int(len(df)) if df is not None else 0,
                        }
                    ],
                }
                return {}, failure

            processing_ms = int((time.time() - t0) * 1000)
            success = {
                "wallet_address": wallet_data.get("wallet_address"),
                "zscore": f"{z:.18f}",
                "timestamp": cls._choose_timestamp(df),
                "processing_time_ms": processing_ms,
                "categories": [
                    {
                        "category": "dexes",
                        "score": float(z),
                        "transaction_count": int(len(df)),
                        "features": {
                            # minimal set the challenge/test expects; you can add more if needed
                            "total_deposit_usd": float(features.get("total_deposit_usd", 0.0)),
                            "total_withdraw_usd": float(features.get("total_withdraw_usd", 0.0)),
                            "num_deposits": int(features.get("num_deposits", 0)),
                            "num_withdraws": int(features.get("num_withdraws", 0)),
                            "total_swap_volume": float(features.get("total_swap_volume", 0.0)),
                            "num_swaps": int(features.get("num_swaps", 0)),
                            "unique_pools": int(features.get("unique_pools", 0)),
                            # you may include other features if desired
                        },
                    }
                ],
            }
            return success, None
        except Exception as e:
            processing_ms = int((time.time() - t0) * 1000)
            failure = {
                "wallet_address": wallet_data.get("wallet_address"),
                "error": f"Exception during processing: {e}",
                "timestamp": int(time.time()),
                "processing_time_ms": processing_ms,
                "categories": [{"category": "dexes", "error": str(e), "transaction_count": 0}],
            }
            return {}, failure
