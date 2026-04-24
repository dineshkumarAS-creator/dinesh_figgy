import asyncio
import json
import time
from collections import defaultdict
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from .window_state_repository import WindowStateRepository
from .city_lookup import CityLookup
from .schemas.aligned_event import AlignedEvent
import structlog
from prometheus_client import Gauge, Histogram
import math

logger = structlog.get_logger()

window_completeness_gauge = Gauge('window_completeness_rate', 'Window completeness')
late_event_rate_gauge = Gauge('late_event_rate', 'Late event rate')
join_latency_histogram = Histogram('join_latency_ms', 'Join latency')

class TemporalAlignmentService:
    def __init__(self, kafka_config: dict, redis_url: str = 'redis://localhost:6379'):
        self.kafka_config = kafka_config
        self.repo = WindowStateRepository(redis_url)
        self.city_lookup = CityLookup(redis_url)
        self.consumers = {
            'telemetry_clean': AIOKafkaConsumer('telemetry_clean', group_id='alignment_telemetry', **kafka_config),
            'weather_clean': AIOKafkaConsumer('weather_clean', group_id='alignment_weather', **kafka_config),
            'aqi_clean': AIOKafkaConsumer('aqi_clean', group_id='alignment_aqi', **kafka_config),
            'events': AIOKafkaConsumer('events', group_id='alignment_events', **kafka_config)
        }
        self.producer = AIOKafkaProducer(**kafka_config)
        self.window_timers: Dict[str, asyncio.Task] = {}  # worker_minute -> task

    async def start(self):
        await self.repo.connect()
        await self.city_lookup.connect()
        for consumer in self.consumers.values():
            await consumer.start()
        await self.producer.start()
        logger.info("TemporalAlignmentService started")

        tasks = [self.process_topic(topic, consumer) for topic, consumer in self.consumers.items()]
        await asyncio.gather(*tasks)

    async def process_topic(self, topic: str, consumer: AIOKafkaConsumer):
        async for msg in consumer:
            try:
                data = json.loads(msg.value.decode('utf-8'))
                server_received_at = time.time()
                data['server_received_at'] = server_received_at

                # UTC sync
                if not self._validate_utc(data):
                    continue

                # Correct telemetry timestamp
                if topic == 'telemetry_clean':
                    await self._correct_telemetry_timestamp(data)

                # Add to window
                await self._add_to_window(topic, data)

            except Exception as e:
                logger.error("Error processing", topic=topic, error=str(e))

    def _validate_utc(self, data: dict) -> bool:
        ts = data.get('timestamp_utc')
        if not ts:
            logger.warning("Missing timestamp_utc", data=data)
            return False
        drift = abs(time.time() - ts)
        if drift > 300:  # 5 min
            logger.warning("Timestamp drift", drift=drift, data=data)
            # Publish to DLQ
            return False
        return True

    async def _correct_telemetry_timestamp(self, data: dict):
        worker_id = data['worker_id']
        offset = await self.repo.get_ntp_offset(worker_id)
        if offset:
            data['timestamp_utc'] += offset

    async def _add_to_window(self, topic: str, data: dict):
        if topic == 'telemetry_clean':
            worker_id = data['worker_id']
        elif topic in ['weather_clean', 'aqi_clean']:
            # For env data, we don't have worker, but will join later
            # Perhaps buffer globally or per city
            # For simplicity, since join on city, buffer per city
            worker_id = 'env'  # Placeholder
        else:
            worker_id = 'events'  # Placeholder

        minute_bucket = int(data['timestamp_utc'] // 60) * 60
        key = f'{worker_id}:{minute_bucket}'

        await self.repo.add_to_window(worker_id, minute_bucket, topic, data)

        # Schedule emit if not already
        if key not in self.window_timers:
            self.window_timers[key] = asyncio.create_task(self._schedule_emit(worker_id, minute_bucket))

    async def _schedule_emit(self, worker_id: str, minute_bucket: int):
        window_end = minute_bucket + 60
        now = time.time()
        wait_time = max(0, window_end - now + 30)  # Wait 30s after window close
        await asyncio.sleep(wait_time)
        await self._emit_window(worker_id, minute_bucket)
        del self.window_timers[f'{worker_id}:{minute_bucket}']

    async def _emit_window(self, worker_id: str, minute_bucket: int):
        start_time = time.time()
        buffer = await self.repo.get_and_delete_window(worker_id, minute_bucket)

        # Aggregate
        telemetry = [d for k, d in buffer.items() if k.startswith('telemetry_clean')]
        weather = [d for k, d in buffer.items() if k.startswith('weather_clean')]
        aqi = [d for k, d in buffer.items() if k.startswith('aqi_clean')]
        events = [d for k, d in buffer.items() if k.startswith('events')]

        if not telemetry:
            return  # No telemetry, skip

        # Aggregate telemetry
        lats = [t['smoothed_lat'] for t in telemetry]
        lons = [t['smoothed_lon'] for t in telemetry]
        speeds = [t['estimated_speed_ms'] for t in telemetry]
        attempts = sum(t.get('delivery_attempts', 0) for t in telemetry)
        app_states = [t.get('app_state') for t in telemetry if t.get('app_state')]
        stationary_count = sum(1 for t in telemetry if t.get('is_stationary'))
        quality_scores = [t['data_quality_score'] for t in telemetry]

        avg_lat = sum(lats) / len(lats)
        avg_lon = sum(lons) / len(lons)
        max_speed = max(speeds)
        majority_state = max(set(app_states), key=app_states.count) if app_states else None
        stationary_pct = stationary_count / len(telemetry)
        avg_quality = sum(quality_scores) / len(quality_scores)

        # City lookup
        city = await self.city_lookup.lookup_city(avg_lat, avg_lon)

        # Latest weather
        latest_weather = max(weather, key=lambda x: x['timestamp_utc']) if weather else None
        weather_city = latest_weather['city'] if latest_weather else None
        rainfall = latest_weather.get('smoothed_rainfall_mm_per_hr') if latest_weather else None
        weather_trigger = latest_weather.get('is_trigger', False) if latest_weather else False
        weather_quality = latest_weather.get('data_quality_score') if latest_weather else None

        # Latest AQI
        latest_aqi = max(aqi, key=lambda x: x['timestamp_utc']) if aqi else None
        aqi_city = latest_aqi['city'] if latest_aqi else None
        aqi_index = latest_aqi.get('aqi_index_current') if latest_aqi else None
        aqi_trigger = latest_aqi.get('is_trigger', False) if latest_aqi else False
        aqi_quality = latest_aqi.get('data_quality_score') if latest_aqi else None

        # Events overlapping
        active_events = []
        for e in events:
            if e['start_time'] <= minute_bucket + 60 and e['end_time'] >= minute_bucket:
                active_events.append(e['event_type'])
        event_trigger = len(active_events) > 0

        any_trigger = weather_trigger or aqi_trigger or event_trigger
        window_complete = len(telemetry) >= 3

        aligned = AlignedEvent(
            worker_id=worker_id,
            minute_bucket=minute_bucket,
            timestamp_utc=minute_bucket,
            avg_smoothed_lat=avg_lat,
            avg_smoothed_lon=avg_lon,
            max_speed_ms=max_speed,
            sum_delivery_attempts=attempts,
            majority_app_state=majority_state,
            stationary_pct=stationary_pct,
            avg_data_quality_score=avg_quality,
            weather_city=weather_city,
            latest_rainfall_mm_per_hr=rainfall,
            weather_is_trigger=weather_trigger,
            weather_data_quality_score=weather_quality,
            aqi_city=aqi_city,
            latest_aqi_index=aqi_index,
            aqi_is_trigger=aqi_trigger,
            aqi_data_quality_score=aqi_quality,
            active_events=active_events,
            event_trigger=event_trigger,
            any_trigger_active=any_trigger,
            window_complete=window_complete,
            telemetry_count=len(telemetry),
            server_received_at=time.time()
        )

        await self.producer.send('aligned_events', json.dumps(aligned.dict()).encode('utf-8'))

        latency = (time.time() - start_time) * 1000
        join_latency_histogram.observe(latency)
        window_completeness_gauge.set(1 if window_complete else 0)

        logger.info("Emitted aligned event", worker_id=worker_id, minute_bucket=minute_bucket, complete=window_complete)

    async def stop(self):
        for consumer in self.consumers.values():
            await consumer.stop()
        await self.producer.stop()
        await self.repo.redis.close()
        await self.city_lookup.redis.close()