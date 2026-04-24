# FIGGY Layer 1 Event Connector Microservice

## Overview

Production-ready async microservice for detecting parametric insurance triggers from government feeds and news sources. Implements real-time event ingestion, NLP-based extraction, and probabilistic deduplication for the FIGGY platform.

---

## Architecture

### Module 1: Government Feed Connector (`govt_feed_connector.py`)

**Fetch cycle**: Every 2 minutes

**Data sources** (priority order):
1. `data.gov.in` REST/RSS API (Indian government data portal)
2. PIB (Press Information Bureau) RSS feed
3. Configurable state government feeds (list driven from `config.yaml`)

**Event extraction**:
- KeywordMatching for event type classification: `curfew`, `strike`, `bandh`, `protest`, `other`
- SpaCy NER (`en_core_web_sm`, lazily loaded) to extract GPE/LOC entities when structured fields missing
- Fallback parsing for both RSS and JSON REST responses

**Triggering logic**:
- `is_trigger_condition=True` for event_type ∈ {`curfew`, `strike`, `bandh`}

**Publishing**:
- Kafka topic: `events`
- Dead-letter queue: `events_dlq` on persistent failures

**Deduplication** (Redis TTL 6 hours):
- SHA256 hash of `source_url|raw_title` prevents re-publishing duplicates
- Atomic set-with-ttl via Redis ensures at-most-once publishing guarantee

---

### Module 2: News Feed Connector (`news_feed_connector.py`)

**Fetch cycle**: Every 5 minutes

**Data sources**:
- NewsAPI.org (`newsapi.org`)
- GNews API (`gnews.io`)

**Filtering & scoring**:
- Keyword density: Count occurrences of keywords [`curfew`, `bandh`, `strike`, `protest`, `section 144`, `shutdown`]
- Source credibility scoring (config-driven):
  - `newsapi.org`: 0.9
  - `gnews.io`: 0.85
- Composite relevance score: `0.4 * keyword_density + 0.6 * source_credibility`
- **Only publishes if `relevance_score > 0.6`**

**Event prediction**:
- Event type predicted via keyword matching (same as govt connector)
- City extracted via SpaCy NER on headline + source name fallback
- Relevance score attached to payload

**Publishing**:
- Kafka topic: `events` (same topic as govt connector, differentiated by `source` field)
- Dead-letter queue: `events_dlq`

**Deduplication**: Same Redis strategy as govt connector

---

## Shared Components

### Schema: `schemas.py`

**Discriminated Union** (Pydantic v2):
```python
EventPayload = Annotated[
    CurfewEvent | StrikeEvent | BandhEvent | ProtestEvent | OtherEvent,
    Field(discriminator="event_type")
]
```

**Common fields**:
- `event_type: Literal`
- `affected_city, affected_zones, severity (1-5)`
- `start_time, end_time (optional)`
- `source_url, raw_title, source`
- `relevance_score (optional, news-specific)`
- `city_extracted (optional, news-specific)`
- `timestamp_utc, is_trigger_condition`

### Config: `config_loader.py` + `config.yaml`

**Pydantic Settings** with YAML file loading:
- Kafka bootstrap servers & topic names
- Redis URL & TTL
- Feed URLs (govt and state feeds)
- API keys (NewsAPI, GNews)
- Keyword list for news filtering
- Source credibility constants

---

## Deduplication Strategy

### Rationale

Event feeds can be noisy with partial duplicates (same headline from multiple sources, multiple fetches of RSS entries within the same 6-hour window). Simple URL matching fails for syndicated content; simple title matching produces false negatives due to slight rewording.

### Implementation

**Fingerprint**: SHA256 hash of `f"{source_url}|{raw_title}"` (full URL + exact title prevents collision)

**Storage**:
- Redis key: `dedup:{hash}`
- Value: `"1"` (marker only)
- TTL: 6 hours (configurable via `redis_ttl_seconds`)

**Atomicity**:
- `SET key "1" EX 21600 NX` (Redis SET with NX flag = create only if not exists)
- Returns `True` (new event) or `None` (duplicate)

**Trade-offs**:
- **Pros**: Deterministic, low latency (~1ms per check), survives connector restarts
- **Cons**: Slight false-positive risk if source_url is normalized differently; requires shared Redis
- **Alternative considered**: In-memory cache (simpler, but loses state on restart; won't scale across replicas)

---

## NER Approach (SpaCy)

### Lazy Loading

Model loaded once on first use (not on startup) to avoid blocking initialization:
```python
_nlp = None
def get_spacy_model(model_name: str):
    global _nlp
    if _nlp is not None:
        return _nlp
    _nlp = spacy.load(model_name)
    return _nlp
```

### Extraction Strategy

1. **Government connector**: Parse raw feed entries (title + summary concatenated)
   - Extract GPE/LOC entities → candidate cities
   - Extract zone names via regex pattern: `"Zone\s+[A-Z][a-z]+"` or similar
2. **News connector**: Parse headline only
   - First GPE/LOC entity returned as city

### Fallback

If NER fails (model not available or parse error), city defaults to `None` and zones default to empty list. Processing continues—NER is enhancement, not blocker.

---

## Testing

### Test Suite: `tests/`

1. **`test_govt_feed_connector.py`** (7 tests):
   - Keyword-based event type classification
   - Feed entry parsing (RSS + JSON)
   - Deduplication logic (mocked Redis)

2. **`test_news_feed_connector.py`** (7 tests):
   - Relevance score computation
   - News API mocking (respx)
   - Event payload building
   - Cycle simulation with fake producer/Redis

**All tests use**:
- `respx` for HTTP mocking
- `pytest-asyncio` for async fixtures
- Spacy disabled via monkeypatch to avoid model download in CI

**Coverage**: 14 tests, all passing ✓

---

## Runtime Dependencies

### Core
- `pydantic>=2.0` — schema validation
- `pydantic-settings>=2.0` — YAML config loading
- `aiokafka>=0.8.0` — Kafka producer
- `redis>=4.7.0` — async Redis client (supports Python 3.14)
- `httpx[http2]>=0.24.0` — async HTTP (with H2 support)

### Data Processing
- `feedparser>=6.0.0` — RSS parsing
- `spacy>=3.0.0` — NER (lazy-loaded model)
- `PyYAML>=6.0.0` — config file parsing

### Observability
- `structlog>=24.0.0` — JSON structured logging
- `tenacity>=8.2.0` — retry decorator (not used in final connectors, available for HTTP client upgrades)

### Testing
- `pytest>=8.0`, `pytest-asyncio>=0.21.0`, `respx>=0.23.0`

**Spacy model download** (in Dockerfile):
```bash
RUN python -m spacy download en_core_web_sm
```

---

## Deployment

### Docker

```bash
docker build -t figgy-event-connector:latest .

# Run govt connector
docker run -e CONNECTOR=govt_feed_connector.py figgy-event-connector:latest

# Run news connector
docker run -e CONNECTOR=news_feed_connector.py figgy-event-connector:latest
```

### Environment

Copy `.env.example` → `.env` and populate:
```env
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
REDIS_URL=redis://redis:6379/0
NEWSAPI_KEY=<your-key>
GNEWS_KEY=<your-key>
```

Or configure via `config.yaml` using Pydantic Settings file loading.

---

## Key Design Decisions

1. **Async throughout**: All I/O uses `httpx.AsyncClient`, `redis.asyncio`, `aiokafka` for efficient resource usage under high concurrency.

2. **Discriminated Union schemas**: Pydantic v2 `Annotated[Union[...], Field(discriminator=...)]` enables single "events" Kafka topic with type-safe deserialization.

3. **Lazy NER loading**: SpaCy model not loaded until first event requires location extraction. Faster cold start, negligible latency on runtime (model cached in memory).

4. **Redis deduplication over DB**: ~1ms set operations vs. persistent DB queries; 6-hour expiry avoids unbounded memory growth; atomic NX semantics guarantee consistency.

5. **Structured logging (structlog)**: JSON output with timestamps, source, event metadata — essential for correlating events in observability pipeline.

6. **TypeAdapter for union validation**: Pydantic's `TypeAdapter` handles discriminated union validation; `isinstance()` checks avoided (not supported on generic aliases).

---

## Future Enhancements

- **Configurable fetch intervals**: Move 2min/5min to config
- **Metrics export**: Prometheus counters for published/duplicate/failed events
- **Dead-letter processing**: Separate consumer to retry DLQ events
- **Search history**: Track last-fetch cursor per feed (RSS Etag, API timestamp) for incremental updates
- **ML-based relevance**: Trained classifier instead of keyword density
- **Fault tolerance**: Circuit breaker for unreliable feeds
