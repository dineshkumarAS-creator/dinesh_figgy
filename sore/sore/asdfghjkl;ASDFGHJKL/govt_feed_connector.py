"""
Government Feed Connector

Fetches events from government sources (PIB, state portals) and publishes to Kafka.
Features:
  - RSS feed parsing
  - Event type detection
  - Location extraction with NLP
  - Deduplication via Redis
  - Dead-letter queue for failures
"""

import asyncio
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

import redis.asyncio as aioredis
import feedparser
import httpx
import structlog
from aiokafka import AIOKafkaProducer
from dotenv import load_dotenv
from pydantic import TypeAdapter, ValidationError

from config_schemas import GovtFeedConnectorConfig, ConfigFactory
from schemas import EventPayload, DLQEvent

load_dotenv()

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger()

_nlp = None

# Event type keywords for classification
EVENT_KEYWORDS = {
    "curfew": ["curfew", "section 144", "prohibitory order"],
    "strike": ["strike", "industrial action", "work stoppage"],
    "bandh": ["bandh", "complete shutdown"],
    "protest": ["protest", "demonstration", "rally", "march", "agitation"],
}

DEFAULT_SEVERITY = 3


# ==============================================================================
# NLP and Text Processing
# ==============================================================================


def get_spacy_model(model_name: str):
    """Lazy-load spaCy NLP model."""
    global _nlp
    if _nlp is not None:
        return _nlp
    try:
        import spacy
        _nlp = spacy.load(model_name)
        return _nlp
    except Exception as exc:
        logger.error("spacy_load_failed", error=str(exc), model=model_name)
        raise


def get_event_type(text: str) -> str:
    """Classify event type from text."""
    normalized = text.lower()
    for event, tokens in EVENT_KEYWORDS.items():
        for token in tokens:
            if token in normalized:
                return event
    return "other"


def extract_locations(text: str, config: GovtFeedConnectorConfig) -> tuple[Optional[str], list[str]]:
    """Extract city and zones from text using NLP."""
    try:
        nlp = get_spacy_model(config.spacy_model)
        doc = nlp(text)
        cities = [ent.text for ent in doc.ents if ent.label_ in {"GPE", "LOC"}]
    except Exception:
        cities = []
    
    city = cities[0] if cities else None
    zones = [
        chunk.strip() 
        for chunk in re.findall(
            r"([A-Z][a-z]+\s+Zone|Zone\s+[A-Z][a-z]+|\w+\s+zone)", 
            text, 
            flags=re.I
        )
    ]
    return city, list(dict.fromkeys(zones))


def normalize_severity(text: Optional[str]) -> int:
    """Extract severity (1-5) from text."""
    if not text:
        return DEFAULT_SEVERITY
    match = re.search(r"(\d+)", text)
    if match:
        value = int(match.group(1))
        return min(max(value, 1), 5)
    return DEFAULT_SEVERITY


def parse_timestamp(value: Any) -> datetime:
    """Parse timestamp from various formats."""
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.astimezone(timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def get_dedup_key(source_url: str, raw_title: str) -> str:
    """Generate deduplication key."""
    fingerprint = f"{source_url}|{raw_title}".encode("utf-8")
    return hashlib.sha256(fingerprint).hexdigest()


def _serialize(payload: Any) -> bytes:
    """Serialize payload to JSON bytes."""
    return json.dumps(payload, default=str).encode("utf-8")


# ==============================================================================
# Kafka and Redis Operations
# ==============================================================================


async def create_kafka_producer(config: GovtFeedConnectorConfig) -> AIOKafkaProducer:
    """Create Kafka producer."""
    producer = AIOKafkaProducer(
        bootstrap_servers=config.kafka_bootstrap_servers.split(",")
    )
    await producer.start()
    return producer


async def create_redis_client(config: GovtFeedConnectorConfig) -> aioredis.Redis:
    """Create Redis client."""
    return aioredis.from_url(config.redis_url, decode_responses=True)


async def publish_event(
    producer: AIOKafkaProducer, 
    topic: str, 
    payload: dict[str, Any]
) -> None:
    """Publish event to Kafka topic."""
    await producer.send_and_wait(topic, _serialize(payload))


async def publish_dlq(
    producer: AIOKafkaProducer, 
    config: GovtFeedConnectorConfig,
    error: str, 
    raw_event: dict[str, Any]
) -> None:
    """Publish failed event to DLQ."""
    dlq_payload = DLQEvent(
        original_event=raw_event,
        failure_reason=error,
        failed_service="govt_feed_connector",
        failure_timestamp_utc=datetime.now(timezone.utc),
    )
    await publish_event(
        producer, 
        config.kafka_dlq_topic, 
        dlq_payload.model_dump()
    )


async def dedupe_event(
    redis_client: aioredis.Redis, 
    key: str, 
    ttl: int
) -> bool:
    """Check if event is duplicate (not seen before). Returns True if new."""
    return await redis_client.set(key, "1", ex=ttl, nx=True) is not None


# ==============================================================================
# Feed Parsing
# ==============================================================================


async def fetch_feed(session: httpx.AsyncClient, url: str) -> list[dict[str, Any]]:
    """Fetch and parse RSS/JSON feed."""
    response = await session.get(url, timeout=20.0)
    response.raise_for_status()
    text = response.text
    
    # Try JSON first
    if (response.headers.get("content-type", "").startswith("application/json") 
        or text.strip().startswith("{")):
        data = response.json()
        if isinstance(data, dict):
            if "notifications" in data:
                return data.get("notifications", [])
            if "items" in data:
                return data.get("items", [])
            if "data" in data:
                return data.get("data", [])
        return []
    
    # Fall back to RSS
    feed = feedparser.parse(text)
    return [entry for entry in feed.entries]


def parse_feed_entry(
    entry: dict[str, Any], 
    source_url: str, 
    source_name: str, 
    config: GovtFeedConnectorConfig
) -> EventPayload:
    """Parse single feed entry into EventPayload."""
    raw_title = str(entry.get("title") or entry.get("headline") or "")
    summary = str(entry.get("summary") or entry.get("description") or "")
    combined = f"{raw_title}\n{summary}"
    
    event_type = get_event_type(combined)
    severity = normalize_severity(
        entry.get("severity") or entry.get("importance") or combined
    )
    start_time = parse_timestamp(
        entry.get("published") 
        or entry.get("start_time") 
        or entry.get("date") 
        or entry.get("published_at")
    )
    end_time = (
        parse_timestamp(entry.get("end_time")) 
        if entry.get("end_time") 
        else None
    )
    
    affected_city = entry.get("city") or entry.get("affected_city")
    if not affected_city:
        affected_city, affected_zones = extract_locations(combined, config)
    else:
        affected_zones = []
    
    payload_data = {
        "event_type": event_type,
        "affected_city": affected_city,
        "affected_zones": affected_zones,
        "city_extracted": affected_city,
        "severity": int(severity),
        "start_time": start_time,
        "end_time": end_time,
        "source_url": source_url,
        "raw_title": raw_title,
        "source": source_name,
        "relevance_score": 1.0,  # PIB is authoritative
        "timestamp_utc": datetime.now(timezone.utc),
        "is_trigger_condition": event_type in {"curfew", "strike", "bandh"},
    }
    
    return TypeAdapter(EventPayload).validate_python(payload_data)


async def parse_source_entries(
    session: httpx.AsyncClient, 
    url: str, 
    source_name: str, 
    config: GovtFeedConnectorConfig
) -> list[EventPayload]:
    """Parse all entries from a feed source."""
    entries = await fetch_feed(session, url)
    results: list[EventPayload] = []
    
    for entry in entries[:config.max_events_per_feed]:
        try:
            payload = parse_feed_entry(entry, source_url=url, source_name=source_name, config=config)
            results.append(payload)
        except ValidationError as exc:
            logger.warning(
                "govt_event_validation_failed", 
                error=str(exc), 
                source=url,
                title=entry.get("title", "")[:100]
            )
    
    return results


# ==============================================================================
# Main Processing Loop
# ==============================================================================


async def run_govt_feed_cycle(
    producer: AIOKafkaProducer, 
    redis_client: aioredis.Redis, 
    config: GovtFeedConnectorConfig
) -> int:
    """Run single feed ingestion cycle. Returns count of events published."""
    published_count = 0
    
    async with httpx.AsyncClient() as client:
        sources = [
            (str(config.data_gov_feed), "data.gov.in"),
            (str(config.pib_feed), "pib"),
        ] + [
            (str(url), f"state-{idx}") 
            for idx, url in enumerate(config.state_feeds, start=1)
        ]
        
        for url, source_name in sources:
            try:
                logger.info("govt_feed_fetching", source=source_name, url=url)
                events = await parse_source_entries(client, url, source_name, config)
                
                for event in events:
                    key = get_dedup_key(event.source_url, event.raw_title)
                    if await dedupe_event(redis_client, key, config.redis_ttl_seconds):
                        # New event
                        await publish_event(
                            producer, 
                            config.kafka_topic, 
                            event.model_dump()
                        )
                        published_count += 1
                        logger.info(
                            "govt_event_published",
                            source=source_name,
                            event_type=event.event_type,
                            city=event.affected_city,
                            severity=event.severity,
                        )
                    else:
                        # Duplicate
                        logger.debug(
                            "govt_event_duplicate",
                            source=source_name,
                            title=event.raw_title[:50],
                        )
            
            except httpx.HTTPError as exc:
                logger.error(
                    "govt_feed_http_error", 
                    error=str(exc), 
                    source=source_name,
                    url=url
                )
                await publish_dlq(
                    producer, 
                    config, 
                    f"HTTP Error: {str(exc)}", 
                    {"source_url": url, "source_name": source_name}
                )
            except Exception as exc:
                logger.error(
                    "govt_feed_processing_error", 
                    error=str(exc), 
                    source=source_name,
                    url=url
                )
                await publish_dlq(
                    producer, 
                    config, 
                    str(exc), 
                    {"source_url": url, "source_name": source_name}
                )
    
    return published_count


async def main() -> None:
    """Start government feed connector."""
    config = ConfigFactory.load_govt_feed_config()
    producer = await create_kafka_producer(config)
    redis_client = await create_redis_client(config)
    
    logger.info(
        "govt_feed_connector_started",
        kafka_topic=config.kafka_topic,
        poll_interval_seconds=config.poll_interval_seconds,
    )
    
    try:
        while True:
            start = datetime.now(timezone.utc)
            count = await run_govt_feed_cycle(producer, redis_client, config)
            elapsed = (datetime.now(timezone.utc) - start).total_seconds()
            
            logger.info(
                "govt_feed_cycle_complete",
                events_published=count,
                elapsed_seconds=elapsed,
            )
            
            await asyncio.sleep(config.poll_interval_seconds)
    except KeyboardInterrupt:
        logger.info("govt_feed_connector_shutting_down")
    finally:
        await producer.stop()
        await redis_client.close()
        logger.info("govt_feed_connector_stopped")


if __name__ == "__main__":
    asyncio.run(main())
