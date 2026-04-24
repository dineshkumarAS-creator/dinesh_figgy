import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog
from aiokafka import AIOKafkaProducer
from dotenv import load_dotenv
from tenacity import (  # type: ignore[import]
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from schemas import WeatherPayload

load_dotenv()

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger()

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
DEFAULT_CITY = "Bengaluru"


@dataclass(frozen=True)
class WeatherConnectorConfig:
    api_key: str
    imd_api_key: str
    imd_api_url: str
    kafka_servers: str
    kafka_topic: str
    kafka_dlq_topic: str
    city: str


def get_weather_config() -> WeatherConnectorConfig:
    load_dotenv()
    return WeatherConnectorConfig(
        api_key=os.getenv("OPENWEATHER_API_KEY", ""),
        imd_api_key=os.getenv("IMD_API_KEY", ""),
        imd_api_url=os.getenv("IMD_API_URL", ""),
        kafka_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        kafka_topic=os.getenv("WEATHER_KAFKA_TOPIC", "weather"),
        kafka_dlq_topic=os.getenv("WEATHER_DLQ_KAFKA_TOPIC", "weather_dlq"),
        city=os.getenv("OPENWEATHER_CITY", DEFAULT_CITY),
    )


def _serialize_message(payload: Any) -> bytes:
    return json.dumps(payload, default=str).encode("utf-8")


async def create_kafka_producer(config: WeatherConnectorConfig) -> AIOKafkaProducer:
    producer = AIOKafkaProducer(bootstrap_servers=config.kafka_servers.split(","))
    await producer.start()
    return producer


@retry(
    retry=retry_if_exception_type((httpx.HTTPError, OSError, ValueError)),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    reraise=True,
)
async def fetch_openweather(session: httpx.AsyncClient, config: WeatherConnectorConfig) -> dict[str, Any]:
    params = {
        "q": config.city,
        "appid": config.api_key,
        "units": "metric",
    }
    response = await session.get(OPENWEATHER_URL, params=params, timeout=20.0)
    response.raise_for_status()
    return response.json()


@retry(
    retry=retry_if_exception_type((httpx.HTTPError, OSError, ValueError)),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    reraise=True,
)
async def fetch_imd(session: httpx.AsyncClient, config: WeatherConnectorConfig) -> dict[str, Any]:
    if not config.imd_api_url:
        raise ValueError("IMD API URL is not configured")
    params = {
        "api_key": config.imd_api_key,
        "city": config.city,
    }
    response = await session.get(config.imd_api_url, params=params, timeout=20.0)
    response.raise_for_status()
    return response.json()


def parse_weather_payload(data: dict[str, Any], source: str, city: str) -> WeatherPayload:
    if source == "openweather":
        rainfall = data.get("rain", {}).get("1h") or data.get("rain", {}).get("3h") or 0.0
        wind_speed = data.get("wind", {}).get("speed", 0.0) * 3.6
        visibility = data.get("visibility", 10000)
        condition_code = data.get("weather", [{}])[0].get("id", 0)
        timestamp = datetime.fromtimestamp(data.get("dt", datetime.now(timezone.utc).timestamp()), tz=timezone.utc)
        latitude = data.get("coord", {}).get("lat", 0.0)
        longitude = data.get("coord", {}).get("lon", 0.0)
        temperature = data.get("main", {}).get("temp", 0.0)
        city_name = data.get("name", city)
    else:
        rainfall = float(data.get("rainfall_mm_per_hr") or data.get("rainfall") or data.get("hourlyRainfall") or 0.0)
        wind_speed = float(data.get("wind_speed_kmh") or data.get("windSpeedKmH") or data.get("wind_speed") or 0.0)
        visibility = int(data.get("visibility_m") or data.get("visibilityMeters") or data.get("visibility") or 10000)
        condition_code = int(data.get("weather_condition_code") or data.get("weatherCode") or 0)
        timestamp = datetime.fromisoformat(data.get("timestamp_utc")) if data.get("timestamp_utc") else datetime.now(timezone.utc)
        latitude = float(data.get("lat") or data.get("latitude") or 0.0)
        longitude = float(data.get("lon") or data.get("longitude") or 0.0)
        temperature = float(data.get("temperature_c") or data.get("temperatureC") or 0.0)
        city_name = str(data.get("city") or city)

    payload = WeatherPayload(
        rainfall_mm_per_hr=float(rainfall),
        temperature_c=float(temperature),
        wind_speed_kmh=float(wind_speed),
        visibility_m=int(visibility),
        weather_condition_code=int(condition_code),
        timestamp_utc=timestamp,
        city=city_name,
        lat=float(latitude),
        lon=float(longitude),
        is_trigger_condition=float(rainfall) > 40.0,
    )
    return payload


async def publish_to_topic(producer: AIOKafkaProducer, topic: str, payload: dict[str, Any]) -> None:
    await producer.send_and_wait(topic, _serialize_message(payload))


async def publish_dlq(producer: AIOKafkaProducer, config: WeatherConnectorConfig, error: str, raw_event: dict[str, Any]) -> None:
    dlq_payload = {
        "error": error,
        "source": "weather_connector",
        "raw_event": raw_event,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await publish_to_topic(producer, config.kafka_dlq_topic, dlq_payload)


async def fetch_weather_payload(config: WeatherConnectorConfig) -> WeatherPayload:
    async with httpx.AsyncClient() as client:
        try:
            response = await fetch_openweather(client, config)
            return parse_weather_payload(response, source="openweather", city=config.city)
        except RetryError as exc:
            logger.warning("openweather_primary_failed", error=str(exc), city=config.city)
            response = await fetch_imd(client, config)
            return parse_weather_payload(response, source="imd", city=config.city)


async def ingest_weather_cycle(producer: AIOKafkaProducer, config: WeatherConnectorConfig) -> None:
    try:
        payload = await fetch_weather_payload(config)
        await publish_to_topic(producer, config.kafka_topic, payload.model_dump())
        logger.info("weather_event_published", topic=config.kafka_topic, city=payload.city, trigger=payload.is_trigger_condition)
    except Exception as exc:
        logger.error("weather_ingest_failed", error=str(exc), city=config.city)
        raw_event = {"city": config.city, "timestamp_utc": datetime.now(timezone.utc).isoformat()}
        await publish_dlq(producer, config, str(exc), raw_event)


async def main() -> None:
    config = get_weather_config()
    producer = await create_kafka_producer(config)
    logger.info("weather_connector_started", city=config.city, topic=config.kafka_topic)
    try:
        while True:
            await ingest_weather_cycle(producer, config)
            await asyncio.sleep(300)
    finally:
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(main())
