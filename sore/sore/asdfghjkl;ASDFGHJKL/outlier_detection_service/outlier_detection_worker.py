import asyncio
import json
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from .detectors.zscore_detector import ZScoreDetector
from .detectors.iqr_detector import IQRDetector
from .detectors.physical_limits import PhysicalLimits
from .rolling_window_repository import RollingWindowRepository
from .schemas.clean_schemas import CleanTelemetryEvent, CleanWeatherData, CleanAQIData
import structlog
from prometheus_client import Gauge
import aioredis

logger = structlog.get_logger()

outlier_rate_gauge = Gauge('outlier_rate_per_topic', 'Outlier rate', ['topic'])

class OutlierDetectionWorker:
    def __init__(self, kafka_config: dict, redis_url: str = 'redis://localhost:6379'):
        self.kafka_config = kafka_config
        self.repo = RollingWindowRepository(redis_url)
        self.redis = aioredis.from_url(redis_url)
        self.zscore_detector = ZScoreDetector(self.redis)
        self.iqr_detector = IQRDetector(self.redis)
        self.consumers = {
            'telemetry_filtered': AIOKafkaConsumer('telemetry_filtered', group_id='outlier_telemetry_group', **kafka_config),
            'weather_filtered': AIOKafkaConsumer('weather_filtered', group_id='outlier_weather_group', **kafka_config),
            'aqi_normalised': AIOKafkaConsumer('aqi_normalised', group_id='outlier_aqi_group', **kafka_config)
        }
        self.producer = AIOKafkaProducer(**kafka_config)

    async def start(self):
        await self.repo.connect()
        for consumer in self.consumers.values():
            await consumer.start()
        await self.producer.start()
        logger.info("OutlierDetectionWorker started")

        tasks = []
        for topic, consumer in self.consumers.items():
            tasks.append(self.process_topic(topic, consumer))
        await asyncio.gather(*tasks)

    async def process_topic(self, topic: str, consumer: AIOKafkaConsumer):
        outlier_count = 0
        total_count = 0
        async for msg in consumer:
            total_count += 1
            try:
                data = json.loads(msg.value.decode('utf-8'))
                if topic == 'telemetry_filtered':
                    cleaned = await self.process_telemetry(data)
                    await self.producer.send('telemetry_clean', json.dumps(cleaned.dict()).encode('utf-8'))
                elif topic == 'weather_filtered':
                    cleaned = await self.process_weather(data)
                    await self.producer.send('weather_clean', json.dumps(cleaned.dict()).encode('utf-8'))
                elif topic == 'aqi_normalised':
                    cleaned = await self.process_aqi(data)
                    await self.producer.send('aqi_clean', json.dumps(cleaned.dict()).encode('utf-8'))

                if cleaned.is_outlier:
                    outlier_count += 1

            except Exception as e:
                logger.error("Error processing message", topic=topic, error=str(e))

            # Update metric periodically
            if total_count % 100 == 0:
                rate = outlier_count / total_count if total_count > 0 else 0
                outlier_rate_gauge.labels(topic=topic).set(rate)

    async def process_telemetry(self, data: dict) -> CleanTelemetryEvent:
        worker_id = data['worker_id']
        smoothed_speed = data.get('estimated_speed_ms', 0)
        delivery_speed = data.get('delivery_speed_implied')

        is_outlier, reason = await self.iqr_detector.detect(worker_id, smoothed_speed, delivery_speed, data['timestamp'])

        # Data quality: 1.0 if no outlier, 0.8 if outlier, 0.5 if missing fields
        quality = 1.0
        if is_outlier:
            quality = 0.8
        # Assume no missing for now

        return CleanTelemetryEvent(
            **data,
            is_outlier=is_outlier,
            outlier_method="iqr" if is_outlier else None,
            outlier_field="speed" if is_outlier else None,
            outlier_z_score=None,
            imputed=False,
            imputed_value=None,
            data_quality_score=quality
        )

    async def process_weather(self, data: dict) -> CleanWeatherData:
        city = data['city']
        fields = ['rainfall_mm_per_hr', 'temperature_c']
        is_outlier = False
        method = None
        field = None
        z_score = None
        imputed = False
        imputed_val = None

        for f in fields:
            if f in data:
                is_gov = data.get('is_government_verified', False)
                out, z, imp = await self.zscore_detector.detect_and_impute(city, f, data[f], data['timestamp'], is_gov)
                if out:
                    is_outlier = True
                    method = "zscore"
                    field = f
                    z_score = z
                    if imp is not None:
                        imputed = True
                        imputed_val = imp
                        data[f] = imp  # Impute in data

        quality = 1.0 if not is_outlier else 0.8

        return CleanWeatherData(
            **data,
            is_outlier=is_outlier,
            outlier_method=method,
            outlier_field=field,
            outlier_z_score=z_score,
            imputed=imputed,
            imputed_value=imputed_val,
            data_quality_score=quality
        )

    async def process_aqi(self, data: dict) -> CleanAQIData:
        city = data.get('city', 'unknown')
        field = 'aqi_index_current'
        is_gov = data.get('is_government_verified', False)
        is_outlier = False
        method = None
        z_score = None
        imputed = False
        imputed_val = None

        if field in data:
            out, z, imp = await self.zscore_detector.detect_and_impute(city, field, data[field], data['timestamp'], is_gov)
            if out:
                is_outlier = True
                method = "zscore"
                z_score = z
                if imp is not None:
                    imputed = True
                    imputed_val = imp
                    data[field] = imp

        quality = 1.0 if not is_outlier else 0.8

        return CleanAQIData(
            **data,
            is_outlier=is_outlier,
            outlier_method=method,
            outlier_field=field if is_outlier else None,
            outlier_z_score=z_score,
            imputed=imputed,
            imputed_value=imputed_val,
            data_quality_score=quality
        )

    async def stop(self):
        for consumer in self.consumers.values():
            await consumer.stop()
        await self.producer.stop()
        await self.redis.close()