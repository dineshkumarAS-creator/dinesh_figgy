import asyncio
import time
from typing import Dict, Any
import structlog
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from prometheus_client import Counter, Histogram

from normalisation_service.normalisers.weather_normaliser import WeatherNormaliser
from normalisation_service.normalisers.aqi_normaliser import AQINormaliser
from normalisation_service.normalisers.telemetry_normaliser import TelemetryNormaliser
from kafka.kafka_config import config

logger = structlog.get_logger()

# Metrics
NORMALISATION_ERRORS = Counter("normalisation_errors_total", "Normalisation errors", ["topic"])
NORMALISATION_LATENCY = Histogram("normalisation_latency_ms", "Normalisation latency", ["topic"])


class NormalisationWorker:
    def __init__(self):
        self.consumer: AIOKafkaConsumer = None
        self.producer: AIOKafkaProducer = None
        self.weather_normaliser = WeatherNormaliser()
        self.aqi_normaliser = AQINormaliser()
        self.telemetry_normaliser = TelemetryNormaliser()

        self.topic_mapping = {
            "weather": ("weather_normalised", self.weather_normaliser),
            "aqi": ("aqi_normalised", self.aqi_normaliser),
            "worker_telemetry": ("telemetry_normalised", self.telemetry_normaliser),
        }

    async def start(self):
        """Start the normalisation worker."""
        self.consumer = AIOKafkaConsumer(
            "weather", "aqi", "worker_telemetry",
            bootstrap_servers=config.bootstrap_servers,
            group_id="normalisation-service",
            auto_offset_reset="earliest",
        )
        await self.consumer.start()

        self.producer = AIOKafkaProducer(bootstrap_servers=config.bootstrap_servers)
        await self.producer.start()

        logger.info("Normalisation worker started")

    async def stop(self):
        """Stop the normalisation worker."""
        if self.consumer:
            await self.consumer.stop()
        if self.producer:
            await self.producer.stop()
        logger.info("Normalisation worker stopped")

    async def run(self):
        """Main processing loop."""
        try:
            async for message in self.consumer:
                topic = message.topic
                raw_event = message.value

                start_time = time.time()
                try:
                    normalised_topic, normaliser = self.topic_mapping[topic]
                    normalised_event = normaliser.normalise(raw_event)

                    # Publish normalised event
                    await self.producer.send_and_wait(
                        normalised_topic,
                        key=message.key,
                        value=normalised_event.model_dump()
                    )

                    latency = (time.time() - start_time) * 1000
                    NORMALISATION_LATENCY.labels(topic=topic).observe(latency)

                    logger.info(
                        "Event normalised",
                        topic=topic,
                        normalised_topic=normalised_topic,
                        latency_ms=latency
                    )

                except Exception as e:
                    NORMALISATION_ERRORS.labels(topic=topic).inc()
                    logger.error("Normalisation failed", topic=topic, error=str(e), raw_event=raw_event)

        except Exception as e:
            logger.error("Consumer error", error=str(e))
        finally:
            await self.stop()


async def main():
    worker = NormalisationWorker()
    await worker.start()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())