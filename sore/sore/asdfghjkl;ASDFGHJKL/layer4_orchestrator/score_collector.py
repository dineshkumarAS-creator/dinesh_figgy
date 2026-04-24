"""
Score Collector

Consumes ML model scores from Kafka and buffers them until all 3 models have scored
for the same (worker_id, minute_bucket) pair. Handles timeouts gracefully.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

import aioredis
import structlog
from aiokafka import AIOKafkaConsumer

from schemas import (
    LSTMScore,
    IsolationForestScore,
    GBMScore,
    ParametricTriggerResult,
    MLScoresMessage,
)

logger = structlog.get_logger()


class ScoreCollector:
    """Collects ML scores from Kafka and buffers by (worker_id, minute_bucket)."""

    def __init__(
        self,
        kafka_bootstrap_servers: str,
        redis_url: str,
        buffer_ttl_seconds: int = 10,
        wait_timeout_seconds: float = 2.0,
    ):
        """
        Initialize score collector.

        Args:
            kafka_bootstrap_servers: Kafka bootstrap servers
            redis_url: Redis connection URL
            buffer_ttl_seconds: PubSub buffer expires if not complete
            wait_timeout_seconds: Max wait for all 3 scores
        """
        self.kafka_servers = kafka_bootstrap_servers.split(",")
        self.redis_url = redis_url
        self.buffer_ttl = buffer_ttl_seconds
        self.wait_timeout = wait_timeout_seconds

        self.consumer: Optional[AIOKafkaConsumer] = None
        self.redis: Optional[aioredis.Redis] = None

        # Metrics
        self.score_sets_received = 0
        self.score_sets_complete = 0
        self.model_timeouts = {"lstm": 0, "isolation_forest": 0, "gbm": 0}

    async def start(self) -> None:
        """Start consumer and Redis connection."""
        # Redis connection
        self.redis = await aioredis.from_url(self.redis_url, decode_responses=True)

        # Kafka consumer
        self.consumer = AIOKafkaConsumer(
            "ml_scores",
            bootstrap_servers=self.kafka_servers,
            group_id="layer4_score_collection",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="earliest",
        )
        await self.consumer.start()
        logger.info("ScoreCollector started")

    async def stop(self) -> None:
        """Stop consumer and Redis."""
        if self.consumer:
            await self.consumer.stop()
        if self.redis:
            await self.redis.close()
        logger.info("ScoreCollector stopped")

    async def collect_scores(self):
        """
        Main loop: consume scores, buffer, and emit complete sets.

        Yields: (worker_id, minute_bucket, complete_scores_dict, has_timeout_flag)
        """
        try:
            async for msg in self.consumer:
                try:
                    raw_data = msg.value
                    score_msg = MLScoresMessage(**raw_data)

                    worker_id = score_msg.worker_id
                    minute_bucket = score_msg.minute_bucket
                    buffer_key = f"score_buffer:{worker_id}:{minute_bucket}"

                    # Get current buffer
                    buffer_json = await self.redis.get(buffer_key)
                    buffer = json.loads(buffer_json) if buffer_json else {}

                    # Add this score
                    buffer[score_msg.model_type] = {
                        "lstm": score_msg.lstm_score.model_dump() if score_msg.lstm_score else None,
                        "isolation_forest": score_msg.if_score.model_dump()
                        if score_msg.if_score
                        else None,
                        "gbm": score_msg.gbm_score.model_dump() if score_msg.gbm_score else None,
                        "parametric_trigger": score_msg.trigger_result.model_dump()
                        if score_msg.trigger_result
                        else None,
                    }.get(score_msg.model_type)

                    # Store feature vector if present
                    if score_msg.feature_vector:
                        buffer["feature_vector"] = score_msg.feature_vector

                    # Extend TTL
                    await self.redis.setex(
                        buffer_key, self.buffer_ttl, json.dumps(buffer, default=str)
                    )

                    self.score_sets_received += 1

                    # Check if complete (2 sec timeout)
                    loop = asyncio.get_event_loop()
                    start_time = loop.time()

                    while loop.time() - start_time < self.wait_timeout:
                        buffer_json = await self.redis.get(buffer_key)
                        current_buffer = json.loads(buffer_json) if buffer_json else {}

                        has_lstm = "lstm" in current_buffer and current_buffer["lstm"]
                        has_if = "isolation_forest" in current_buffer and current_buffer["isolation_forest"]
                        has_gbm = "gbm" in current_buffer and current_buffer["gbm"]
                        has_trigger = (
                            "parametric_trigger" in current_buffer
                            and current_buffer["parametric_trigger"]
                        )

                        # All 3 ML models + trigger
                        if has_lstm and has_if and has_gbm and has_trigger:
                            self.score_sets_complete += 1
                            await self.redis.delete(buffer_key)
                            logger.info(
                                "score_set_complete",
                                worker_id=worker_id,
                                minute_bucket=minute_bucket,
                            )
                            yield (
                                worker_id,
                                minute_bucket,
                                current_buffer,
                                False,  # no timeout
                            )
                            break

                        await asyncio.sleep(0.05)  # Check every 50ms

                    else:
                        # Timeout - use available scores + sentinel for missing
                        buffer_json = await self.redis.get(buffer_key)
                        final_buffer = json.loads(buffer_json) if buffer_json else {}

                        missing_models = []
                        if "lstm" not in final_buffer or not final_buffer["lstm"]:
                            final_buffer["lstm"] = None
                            missing_models.append("lstm")
                            self.model_timeouts["lstm"] += 1

                        if "isolation_forest" not in final_buffer or not final_buffer["isolation_forest"]:
                            final_buffer["isolation_forest"] = None
                            missing_models.append("isolation_forest")
                            self.model_timeouts["isolation_forest"] += 1

                        if "gbm" not in final_buffer or not final_buffer["gbm"]:
                            final_buffer["gbm"] = None
                            missing_models.append("gbm")
                            self.model_timeouts["gbm"] += 1

                        if "parametric_trigger" not in final_buffer or not final_buffer["parametric_trigger"]:
                            final_buffer["parametric_trigger"] = None

                        await self.redis.delete(buffer_key)

                        logger.warning(
                            "score_set_partial_timeout",
                            worker_id=worker_id,
                            minute_bucket=minute_bucket,
                            missing_models=missing_models,
                        )

                        self.score_sets_complete += 1
                        yield (
                            worker_id,
                            minute_bucket,
                            final_buffer,
                            True,  # timeout
                        )

                except Exception as e:
                    logger.exception("score_collection_error", error=str(e))

        except asyncio.CancelledError:
            logger.info("ScoreCollector cancelled")
        except Exception as e:
            logger.exception("score_collector_fatal", error=str(e))

    def get_metrics(self) -> dict:
        """Return current metrics."""
        total_timeout_events = sum(self.model_timeouts.values())
        timeout_rate = (
            (total_timeout_events / self.score_sets_received * 100)
            if self.score_sets_received > 0
            else 0
        )

        return {
            "score_sets_received": self.score_sets_received,
            "score_sets_complete": self.score_sets_complete,
            "model_timeouts": self.model_timeouts,
            "timeout_rate_percent": timeout_rate,
        }
