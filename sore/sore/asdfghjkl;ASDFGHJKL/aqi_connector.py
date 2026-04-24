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

from schemas import AQIPayload

load_dotenv()

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger()

DEFAULT_CITY = "Delhi"


@dataclass(frozen=True)
class AQIConnectorConfig:
    cpcb_api_url: str
    cpcb_api_key: str
    iqair_api_url: str
    iqair_api_key: str
    kafka_servers: str
    kafka_topic: str
    kafka_dlq_topic: str
    city: str


def get_aqi_config() -> AQIConnectorConfig:
    load_dotenv()
    return AQIConnectorConfig(
        cpcb_api_url=os.getenv("CPCB_API_URL", ""),
        cpcb_api_key=os.getenv("CPCB_API_KEY", ""),
        iqair_api_url=os.getenv("IQAIR_API_URL", "https://api.airvisual.com/v2/nearest_city"),
        iqair_api_key=os.getenv("IQAIR_API_KEY", ""),
        kafka_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        kafka_topic=os.getenv("AQI_KAFKA_TOPIC", "aqi"),
        kafka_dlq_topic=os.getenv("AQI_DLQ_KAFKA_TOPIC", "aqi_dlq"),
        city=os.getenv("AQI_CITY", DEFAULT_CITY),
    )


def _serialize_message(payload: Any) -> bytes:
    return json.dumps(payload, default=str).encode("utf-8")


async def create_kafka_producer(config: AQIConnectorConfig) -> AIOKafkaProducer:
    producer = AIOKafkaProducer(bootstrap_servers=config.kafka_servers.split(","))
    await producer.start()
    return producer


@retry(
    retry=retry_if_exception_type((httpx.HTTPError, OSError, ValueError)),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    reraise=True,
)
async def fetch_cpcb(session: httpx.AsyncClient, config: AQIConnectorConfig) -> dict[str, Any]:
    if not config.cpcb_api_url:
        raise ValueError("CPCB API URL is not configured")
    params = {
        "api_key": config.cpcb_api_key,
        "city": config.city,
    }
    response = await session.get(config.cpcb_api_url, params=params, timeout=20.0)
    response.raise_for_status()
    return response.json()


@retry(
    retry=retry_if_exception_type((httpx.HTTPError, OSError, ValueError)),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(3),
    reraise=True,
)
async def fetch_iqair(session: httpx.AsyncClient, config: AQIConnectorConfig) -> dict[str, Any]:
    params = {
        "key": config.iqair_api_key,
        "city": config.city,
    }
    response = await session.get(config.iqair_api_url, params=params, timeout=20.0)
    response.raise_for_status()
    return response.json()


def normalize_aqi(value: float) -> int:
    if value is None:
        return 0
    rounded = int(round(value))
    return int(min(max(rounded, 0), 500))


def parse_aqi_payload(data: dict[str, Any], source: str, city: str) -> AQIPayload:
    if source == "cpcb":
        raw_value = float(data.get("aqi_index_current") or data.get("aqi") or 0.0)
        pm25 = float(data.get("pm25") or data.get("pm2_5") or 0.0)
        pm10 = float(data.get("pm10") or data.get("pm_10") or 0.0)
        no2 = float(data.get("no2") or data.get("nitrogen_dioxide") or 0.0)
        station_id = str(data.get("station_id") or data.get("stationId") or "unknown")
        latitude = float(data.get("lat") or data.get("latitude") or 0.0)
        longitude = float(data.get("lon") or data.get("longitude") or 0.0)
        timestamp = datetime.fromisoformat(data.get("timestamp_utc")) if data.get("timestamp_utc") else datetime.now(timezone.utc)
        city_name = str(data.get("city") or city)
    else:
        pollution = data.get("data", {}).get("current", {}).get("pollution", {})
        raw_value = float(pollution.get("aqius") or pollution.get("aqi") or 0.0)
        pm25 = float(pollution.get("p2") or pollution.get("pm25") or 0.0)
        pm10 = float(pollution.get("p1") or pollution.get("pm10") or 0.0)
        no2 = float(pollution.get("n2") or pollution.get("no2") or 0.0)
        station_id = str(data.get("data", {}).get("city", {}).get("name") or city)
        latitude = float(data.get("data", {}).get("location", {}).get("coordinates", [0.0, 0.0])[1] or 0.0)
        longitude = float(data.get("data", {}).get("location", {}).get("coordinates", [0.0, 0.0])[0] or 0.0)
        timestamp = datetime.fromisoformat(data.get("data", {}).get("current", {}).get("pollution", {}).get("ts")) if data.get("data", {}).get("current", {}).get("pollution", {}).get("ts") else datetime.now(timezone.utc)
        city_name = str(data.get("data", {}).get("city", {}).get("name") or city)

    standardized = normalize_aqi(raw_value)
    return AQIPayload(
        aqi_index_current=float(raw_value),
        aqi_index_standardized=standardized,
        pm25=float(pm25),
        pm10=float(pm10),
        no2=float(no2),
        station_id=station_id,
        city=city_name,
        lat=float(latitude),
        lon=float(longitude),
        timestamp_utc=timestamp,
        is_trigger_condition=standardized > 400,
    )


async def publish_to_topic(producer: AIOKafkaProducer, topic: str, payload: dict[str, Any]) -> None:
    await producer.send_and_wait(topic, _serialize_message(payload))


async def publish_dlq(producer: AIOKafkaProducer, config: AQIConnectorConfig, error: str, raw_event: dict[str, Any]) -> None:
    dlq_payload = {
        "error": error,
        "source": "aqi_connector",
        "raw_event": raw_event,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await publish_to_topic(producer, config.kafka_dlq_topic, dlq_payload)


async def fetch_aqi_payload(config: AQIConnectorConfig) -> AQIPayload:
    async with httpx.AsyncClient() as client:
        try:
            response = await fetch_cpcb(client, config)
            return parse_aqi_payload(response, source="cpcb", city=config.city)
        except RetryError as exc:
            logger.warning("cpcb_primary_failed", error=str(exc), city=config.city)
            response = await fetch_iqair(client, config)
            return parse_aqi_payload(response, source="iqair", city=config.city)


async def ingest_aqi_cycle(producer: AIOKafkaProducer, config: AQIConnectorConfig) -> None:
    try:
        payload = await fetch_aqi_payload(config)
        await publish_to_topic(producer, config.kafka_topic, payload.model_dump())
        logger.info("aqi_event_published", topic=config.kafka_topic, city=payload.city, trigger=payload.is_trigger_condition)
    except Exception as exc:
        logger.error("aqi_ingest_failed", error=str(exc), city=config.city)
        raw_event = {"city": config.city, "timestamp_utc": datetime.now(timezone.utc).isoformat()}
        await publish_dlq(producer, config, str(exc), raw_event)


async def main() -> None:
    config = get_aqi_config()
    producer = await create_kafka_producer(config)
    logger.info("aqi_connector_started", city=config.city, topic=config.kafka_topic)
    try:
        while True:
            await ingest_aqi_cycle(producer, config)
            await asyncio.sleep(600)
    finally:
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(main())
