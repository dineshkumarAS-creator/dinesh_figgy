import asyncio
import json
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from .feature_store.redis_writer import RedisFeatureStoreWriter
from .feature_store.feast_writer import FeastFeatureStoreWriter
from .schemas.feature_vector import FeatureVector, FeatureQualityError
import structlog
from prometheus_client import Histogram

logger = structlog.get_logger()

e2e_latency = Histogram('e2e_feature_pipeline_latency_ms', 'End-to-end latency')

class Layer3Orchestrator:
    def __init__(self, kafka_config: dict, redis_url: str, env_extractor, beh_extractor, inc_extractor):
        self.kafka_config = kafka_config
        self.redis_url = redis_url
        self.env_extractor = env_extractor
        self.beh_extractor = beh_extractor
        self.inc_extractor = inc_extractor
        self.consumer = AIOKafkaConsumer('aligned_events', group_id='layer3_feature_extraction', **kafka_config)
        self.producer = AIOKafkaProducer(**kafka_config)
        self.redis_writer = RedisFeatureStoreWriter(redis_url)
        self.feast_writer = FeastFeatureStoreWriter('feature_store/feast_repo')

    async def start(self):
        await self.redis_writer.connect()
        await self.consumer.start()
        await self.producer.start()
        logger.info("Layer3Orchestrator started")

        async for msg in self.consumer:
            start_time = asyncio.get_event_loop().time()
            try:
                aligned_event = json.loads(msg.value.decode('utf-8'))

                # Concurrent context loading
                env_context, beh_context, inc_context = await asyncio.gather(
                    self.env_extractor.load_context(aligned_event['weather_city'] or aligned_event['aqi_city'], aligned_event),
                    self.beh_extractor.load_context(aligned_event['worker_id'], aligned_event),
                    self.inc_extractor.extract(aligned_event)  # Wait, income doesn't have load_context, it's direct
                )

                # Extract features
                env_features = self.env_extractor.extract(aligned_event, env_context)
                beh_features = self.beh_extractor.extract(aligned_event, beh_context)
                inc_features = inc_context  # Assuming extract returns features

                # Save contexts
                await asyncio.gather(
                    self.beh_extractor.save_context(aligned_event['worker_id'], beh_context),
                    asyncio.sleep(0)  # Income doesn't save
                )

                # Merge
                feature_vector = FeatureVector(
                    worker_id=aligned_event['worker_id'],
                    minute_bucket=aligned_event['minute_bucket'],
                    feature_pipeline_version='1.0.0',
                    computed_at=datetime.utcnow(),
                    **env_features.model_dump(),
                    **beh_features.model_dump(),
                    **inc_features.model_dump()
                )

                # Validate
                feature_vector.validate_quality()

                # Write to Redis
                await self.redis_writer.write(feature_vector)

                # Enqueue for Feast
                await self.feast_writer.write_batch([feature_vector])

                # Publish to Kafka
                await self.producer.send('feature_vectors', feature_vector.model_dump_json().encode('utf-8'))

                latency = (asyncio.get_event_loop().time() - start_time) * 1000
                e2e_latency.observe(latency)

            except FeatureQualityError as e:
                logger.warning("Feature quality error", error=str(e))
                # Publish to DLQ
                await self.producer.send('feature_vectors_dlq', msg.value)
            except Exception as e:
                logger.error("Pipeline error", error=str(e))

    async def stop(self):
        await self.consumer.stop()
        await self.producer.stop()
        await self.feast_writer.batch_flush()