import asyncio
import json
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from .filter_state_repository import FilterStateRepository, WorkerFilterState
from .filters.kalman_gps import GPSKalmanFilter
from .filters.kalman_imu import IMUKalmanFilter
from .filters.weather_smoother import WeatherSmoother
from .schemas.filtered_schemas import FilteredTelemetryEvent, FilteredWeatherData
import structlog

logger = structlog.get_logger()

class NoiseFilterWorker:
    def __init__(self, kafka_config: dict, redis_url: str = 'redis://localhost:6379'):
        self.kafka_config = kafka_config
        self.repo = FilterStateRepository(redis_url)
        self.telemetry_consumer = AIOKafkaConsumer(
            'telemetry_normalised',
            group_id='filter_gps_group',
            **kafka_config
        )
        self.weather_consumer = AIOKafkaConsumer(
            'weather_normalised',
            group_id='filter_weather_group',
            **kafka_config
        )
        self.producer = AIOKafkaProducer(**kafka_config)

    async def start(self):
        await self.repo.connect()
        await self.telemetry_consumer.start()
        await self.weather_consumer.start()
        await self.producer.start()
        logger.info("NoiseFilterWorker started")

        # Run both consumers concurrently
        await asyncio.gather(
            self.process_telemetry(),
            self.process_weather()
        )

    async def process_telemetry(self):
        async for msg in self.telemetry_consumer:
            try:
                data = json.loads(msg.value.decode('utf-8'))
                worker_id = data['worker_id']
                # Assume data has lat, lon, accuracy_m, accel_x, etc., timestamp
                # Load state
                state = await self.repo.get_worker_state(worker_id)
                if not state:
                    state = WorkerFilterState()
                if not state.gps_filter:
                    state.gps_filter = GPSKalmanFilter()
                if not state.imu_filter:
                    state.imu_filter = IMUKalmanFilter()

                # Apply GPS filter
                smoothed_lat, smoothed_lon, est_speed, pos_uncertainty = state.gps_filter.update(
                    data['lat'], data['lon'], data['accuracy_m'], data['timestamp']
                )

                # Apply IMU filter
                smoothed_ax, smoothed_ay, smoothed_az, is_stationary = state.imu_filter.update(
                    data['accel_x'], data['accel_y'], data['accel_z'], data['timestamp']
                )

                # Save state
                await self.repo.set_worker_state(worker_id, state)

                # Create filtered event
                filtered = FilteredTelemetryEvent(
                    worker_id=worker_id,
                    timestamp=data['timestamp'],
                    smoothed_lat=smoothed_lat,
                    smoothed_lon=smoothed_lon,
                    estimated_speed_ms=est_speed,
                    position_uncertainty_m=pos_uncertainty,
                    smoothed_accel_x=smoothed_ax,
                    smoothed_accel_y=smoothed_ay,
                    smoothed_accel_z=smoothed_az,
                    is_stationary=is_stationary
                )

                # Publish
                await self.producer.send('telemetry_filtered', json.dumps(filtered.dict()).encode('utf-8'))

                # Log noise reduction (placeholder)
                logger.info("Filtered telemetry", worker_id=worker_id, noise_reduction_pct=0.0)  # Calculate if needed

            except Exception as e:
                logger.error("Error processing telemetry", error=str(e))

    async def process_weather(self):
        async for msg in self.weather_consumer:
            try:
                data = json.loads(msg.value.decode('utf-8'))
                city = data['city']
                # Load smoother
                smoother = await self.repo.get_weather_smoother(city)
                if not smoother:
                    smoother = WeatherSmoother()

                smoothed_rainfall = smoother.update(city, data['rainfall_mm_per_hr'], data['timestamp'])

                # Save
                await self.repo.set_weather_smoother(city, smoother)

                # Create filtered
                filtered = FilteredWeatherData(
                    city=city,
                    timestamp=data['timestamp'],
                    smoothed_rainfall_mm_per_hr=smoothed_rainfall
                )

                # Publish
                await self.producer.send('weather_filtered', json.dumps(filtered.dict()).encode('utf-8'))

            except Exception as e:
                logger.error("Error processing weather", error=str(e))

    async def stop(self):
        await self.telemetry_consumer.stop()
        await self.weather_consumer.stop()
        await self.producer.stop()
        await self.repo.disconnect()