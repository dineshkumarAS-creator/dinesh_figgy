"""
News Feed Connector

Fetches events from public news APIs (NewsAPI, GNews) and publishes to Kafka.
Features:
  - Multi-source news aggregation
  - Event type detection and relevance scoring
  - Location extraction with NLP
  - Deduplication via Redis
  - Source credibility weighting
  - Dead-letter queue for failures
"""

import asyncio
import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Optional

import redis.asyncio as aioredis
import httpx
import structlog
from aiokafka import AIOKafkaProducer
from dotenv import load_dotenv
from pydantic import TypeAdapter, ValidationError

from config_schemas import NewsConnectorConfig, ConfigFactory
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


def extract_locations(text: str, config: NewsConnectorConfig) -> tuple[Optional[str], list[str]]:
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
    match = re.search(r"(\d)", text)
    if match:
        value = int(match.group(1))
        return min(max(value, 1), 5)
    return DEFAULT_SEVERITY


def compute_relevance_score(
    text: str, 
    keywords: list[str],
) -> float:
    """Compute relevance score based on keyword presence."""
    normalized = text.lower()
    match_count = sum(1 for kw in keywords if kw.lower() in normalized)
    return min(match_count / max(len(keywords), 1), 1.0)


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


def get_source_name(url: str) -> str:
    """Extract source name from URL."""
    if "newsapi.org" in url:
        return "newsapi.org"
    elif "gnews.io" in url:
        return "gnews.io"
    else:
        return "unknown"


def _serialize(payload: Any) -> bytes:
    """Serialize payload to JSON bytes."""
    return json.dumps(payload, default=str).encode("utf-8")


# ==============================================================================
# Kafka and Redis Operations
# ==============================================================================


async def create_kafka_producer(config: NewsConnectorConfig) -> AIOKafkaProducer:
    """Create Kafka producer."""
    producer = AIOKafkaProducer(
        bootstrap_servers=config.kafka_bootstrap_servers.split(",")
    )
    await producer.start()
    return producer


async def create_redis_client(config: NewsConnectorConfig) -> aioredis.Redis:
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
    config: NewsConnectorConfig,
    error: str, 
    raw_event: dict[str, Any]
) -> None:
    """Publish failed event to DLQ."""
    dlq_payload = DLQEvent(
        original_event=raw_event,
        failure_reason=error,
        failed_service="news_feed_connector",
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
# News API Fetching
# ==============================================================================


async def fetch_newsapi(
    session: httpx.AsyncClient, 
    config: NewsConnectorConfig
) -> list[dict[str, Any]]:
    """Fetch from NewsAPI."""
    for keyword in config.keywords:
        try:
            params = {
                "q": keyword,
                "apiKey": config.newsapi_key,
                "sortBy": "publishedAt",
                "pageSize": config.max_events_per_source,
                "language": "en",
            }
            response = await session.get(str(config.newsapi_url), params=params, timeout=20.0)
            response.raise_for_status()
            data = response.json()
            
            logger.info(
                "newsapi_fetch_success",
                keyword=keyword,
                articles=len(data.get("articles", [])),
            )
            
            for article in data.get("articles", []):
                article["_source_url"] = str(config.newsapi_url)
                article["_keyword"] = keyword
            
            return data.get("articles", [])
        except httpx.HTTPError as exc:
            logger.warning(
                "newsapi_fetch_error",
                keyword=keyword,
                error=str(exc),
            )
    
    return []


async def fetch_gnews(
    session: httpx.AsyncClient, 
    config: NewsConnectorConfig
) -> list[dict[str, Any]]:
    """Fetch from GNews."""
    for keyword in config.keywords:
        try:
            params = {
                "q": keyword,
                "token": config.gnews_key,
                "max": config.max_events_per_source,
                "lang": "en",
                "sortby": "publishedAt",
            }
            response = await session.get(str(config.gnews_url), params=params, timeout=20.0)
            response.raise_for_status()
            data = response.json()
            
            logger.info(
                "gnews_fetch_success",
                keyword=keyword,
                articles=len(data.get("articles", [])),
            )
            
            for article in data.get("articles", []):
                article["_source_url"] = str(config.gnews_url)
                article["_keyword"] = keyword
            
            return data.get("articles", [])
        except httpx.HTTPError as exc:
            logger.warning(
                "gnews_fetch_error",
                keyword=keyword,
                error=str(exc),
            )
    
    return []


def parse_news_article(
    article: dict[str, Any], 
    source_url: str,
    config: NewsConnectorConfig
) -> Optional[EventPayload]:
    """Parse news article into EventPayload."""
    raw_title = str(article.get("title") or article.get("headline") or "")
    if not raw_title:
        return None
    
    description = str(article.get("description") or article.get("content") or "")
    combined = f"{raw_title}\n{description}"
    
    event_type = get_event_type(combined)
    
    # Filter by relevance
    relevance_score = compute_relevance_score(combined, config.keywords)
    if relevance_score < config.min_relevance_score:
        return None
    
    severity = normalize_severity(combined)
    publish_time = article.get("publishedAt") or article.get("published_at")
    start_time = parse_timestamp(publish_time)
    
    affected_city, affected_zones = extract_locations(combined, config)
    
    # Get source credibility
    source_name = get_source_name(source_url)
    credibility = config.source_credibility.get(source_name, 0.5)
    
    # Adjust relevance by credibility
    final_relevance = relevance_score * credibility
    
    url = str(article.get("url") or article.get("link") or source_url)
    
    payload_data = {
        "event_type": event_type,
        "affected_city": affected_city,
        "affected_zones": affected_zones,
        "city_extracted": affected_city,
        "severity": int(severity),
        "start_time": start_time,
        "end_time": None,
        "source_url": url,
        "raw_title": raw_title,
        "source": source_name,
        "relevance_score": final_relevance,
        "timestamp_utc": datetime.now(timezone.utc),
        "is_trigger_condition": event_type in {"curfew", "strike", "bandh"},
    }
    
    try:
        return TypeAdapter(EventPayload).validate_python(payload_data)
    except ValidationError as exc:
        logger.warning(
            "news_event_validation_failed",
            error=str(exc),
            source=source_name,
            title=raw_title[:100],
        )
        return None


# ==============================================================================
# Main Processing Loop
# ==============================================================================


async def run_news_feed_cycle(
    producer: AIOKafkaProducer, 
    redis_client: aioredis.Redis, 
    config: NewsConnectorConfig
) -> int:
    """Run single news feed ingestion cycle. Returns count of events published."""
    published_count = 0
    
    async with httpx.AsyncClient() as client:
        sources = []
        
        # Add NewsAPI if configured
        if config.newsapi_key:
            articles_newsapi = await fetch_newsapi(client, config)
            for article in articles_newsapi:
                article["_source"] = "newsapi.org"
            sources.extend(articles_newsapi)
        
        # Add GNews if configured
        if config.gnews_key:
            articles_gnews = await fetch_gnews(client, config)
            for article in articles_gnews:
                article["_source"] = "gnews.io"
            sources.extend(articles_gnews)
        
        logger.info("news_feed_fetched", total_articles=len(sources))
        
        for article in sources:
            source_url = article.get("_source_url", "")
            
            try:
                event = parse_news_article(article, source_url, config)
                
                if event is None:
                    # Filtered by relevance
                    continue
                
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
                        "news_event_published",
                        source=event.source,
                        event_type=event.event_type,
                        city=event.affected_city,
                        relevance_score=event.relevance_score,
                    )
                else:
                    # Duplicate
                    logger.debug(
                        "news_event_duplicate",
                        source=event.source,
                        title=event.raw_title[:50],
                    )
            
            except Exception as exc:
                logger.error(
                    "news_article_processing_error",
                    error=str(exc),
                    title=article.get("title", "")[:100],
                )
                await publish_dlq(
                    producer, 
                    config, 
                    str(exc), 
                    {
                        "article_title": article.get("title", ""),
                        "source_url": source_url,
                    }
                )
    
    return published_count


async def main() -> None:
    """Start news feed connector."""
    config = ConfigFactory.load_news_config()
    
    if not (config.newsapi_key or config.gnews_key):
        logger.error(
            "news_feed_connector_no_credentials",
            message="No API keys configured for NewsAPI or GNews"
        )
        return
    
    producer = await create_kafka_producer(config)
    redis_client = await create_redis_client(config)
    
    logger.info(
        "news_feed_connector_started",
        kafka_topic=config.kafka_topic,
        poll_interval_seconds=config.poll_interval_seconds,
        keywords=config.keywords,
    )
    
    try:
        while True:
            start = datetime.now(timezone.utc)
            count = await run_news_feed_cycle(producer, redis_client, config)
            elapsed = (datetime.now(timezone.utc) - start).total_seconds()
            
            logger.info(
                "news_feed_cycle_complete",
                events_published=count,
                elapsed_seconds=elapsed,
            )
            
            await asyncio.sleep(config.poll_interval_seconds)
    except KeyboardInterrupt:
        logger.info("news_feed_connector_shutting_down")
    finally:
        await producer.stop()
        await redis_client.close()
        logger.info("news_feed_connector_stopped")


if __name__ == "__main__":
    asyncio.run(main())
