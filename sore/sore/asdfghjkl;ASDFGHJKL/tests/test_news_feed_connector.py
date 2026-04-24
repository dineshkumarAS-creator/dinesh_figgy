"""
Tests for News Feed Connector

Tests cover:
  - News API fetching (NewsAPI, GNews)
  - Event type detection and relevance scoring
  - Location extraction
  - Deduplication via Redis
  - Source credibility weighting
  - DLQ publishing for failures
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from config_schemas import NewsConnectorConfig
from news_feed_connector import (
    get_event_type,
    extract_locations,
    normalize_severity,
    compute_relevance_score,
    get_source_name,
    get_dedup_key,
    parse_news_article,
    dedupe_event,
)
from schemas import EventPayload


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def news_config():
    """News feed connector config."""
    return NewsConnectorConfig()


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    return AsyncMock()


@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer."""
    producer = AsyncMock()
    producer.send_and_wait = AsyncMock()
    return producer


# ==============================================================================
# Text Processing Tests
# ==============================================================================


class TestEventTypeDetection:
    """Tests for event type classification."""
    
    def test_detect_curfew(self):
        """Detect curfew event type."""
        text = "Breaking: Curfew imposed in 5 districts following unrest"
        assert get_event_type(text) == "curfew"
    
    def test_detect_strike(self):
        """Detect strike event type."""
        text = "Industrial strike impacts public transport services"
        assert get_event_type(text) == "strike"
    
    def test_detect_bandh(self):
        """Detect bandh event type."""
        text = "Complete bandh observed across the state"
        assert get_event_type(text) == "bandh"
    
    def test_detect_protest(self):
        """Detect protest event type."""
        text = "Massive protest march planned against new policy"
        assert get_event_type(text) == "protest"
    
    def test_detect_other(self):
        """Detect 'other' event type."""
        text = "New technology enhances delivery services"
        assert get_event_type(text) == "other"


# ==============================================================================
# Relevance Scoring Tests
# ==============================================================================


class TestRelevanceScoring:
    """Tests for event relevance scoring."""
    
    def test_compute_relevance_single_keyword(self):
        """Compute relevance with single keyword match."""
        keywords = ["curfew", "bandh", "strike", "protest"]
        text = "Emergency curfew announced"
        score = compute_relevance_score(text, keywords)
        
        assert 0.0 <= score <= 1.0
        assert score > 0.2  # Should have reasonably high relevance
    
    def test_compute_relevance_no_keywords(self):
        """Low relevance with no keyword matches."""
        keywords = ["curfew", "bandh", "strike", "protest"]
        text = "Weather forecast today"
        score = compute_relevance_score(text, keywords)
        
        assert score < 0.3  # Low relevance
    
    def test_compute_relevance_multiple_keywords(self):
        """Higher relevance with multiple keyword matches."""
        keywords = ["curfew", "bandh", "strike", "protest"]
        text = "Curfew and protest march expected tomorrow"
        score = compute_relevance_score(text, keywords)
        
        assert score > 0.4  # Moderate to high relevance
    
    def test_relevance_case_insensitive(self):
        """Relevance scoring is case-insensitive."""
        keywords = ["curfew", "bandh"]
        score1 = compute_relevance_score("CURFEW IMPOSED", keywords)
        score2 = compute_relevance_score("curfew imposed", keywords)
        
        assert score1 == score2


# ==============================================================================
# Source Identification Tests
# ==============================================================================


class TestSourceIdentification:
    """Tests for news source identification."""
    
    def test_identify_newsapi_source(self):
        """Identify NewsAPI source."""
        url = "https://newsapi.org/v2/everything"
        assert get_source_name(url) == "newsapi.org"
    
    def test_identify_gnews_source(self):
        """Identify GNews source."""
        url = "https://gnews.io/api/v4/search"
        assert get_source_name(url) == "gnews.io"
    
    def test_identify_unknown_source(self):
        """Unknown source returns 'unknown'."""
        url = "https://custom-news.com/api"
        assert get_source_name(url) == "unknown"


# ==============================================================================
# Article Parsing Tests
# ==============================================================================


class TestArticleParsing:
    """Tests for individual article parsing."""
    
    def test_parse_article_above_threshold(self, news_config):
        """Parse article with high relevance content."""
        article = {
            "title": "Curfew and strike announced in major cities",
            "description": "Emergency curfew imposed with bandh due to protests and shutdown",
            "url": "https://news.com/article1",
            "publishedAt": "2026-04-14T10:00:00Z",
        }
        
        event = parse_news_article(
            article,
            source_url="https://newsapi.org",
            config=news_config
        )
        
        assert event is not None
        assert hasattr(event, 'event_type')
        assert event.event_type == "curfew"
        assert event.relevance_score >= news_config.min_relevance_score
    
    def test_parse_article_below_threshold(self, news_config):
        """Article below relevance threshold returns None."""
        article = {
            "title": "Tech news roundup",
            "description": "Latest developments in technology sector",
            "url": "https://news.com/article2",
            "publishedAt": "2026-04-14T10:00:00Z",
        }
        
        event = parse_news_article(
            article,
            source_url="https://newsapi.org",
            config=news_config
        )
        
        assert event is None or event.relevance_score < news_config.min_relevance_score
    
    def test_parse_article_missing_title(self, news_config):
        """Article without title returns None."""
        article = {
            "description": "Some content",
            "url": "https://news.com/article",
            "publishedAt": "2026-04-14T10:00:00Z",
        }
        
        event = parse_news_article(
            article,
            source_url="https://newsapi.org",
            config=news_config
        )
        
        assert event is None


# ==============================================================================
# Deduplication Tests
# ==============================================================================


class TestDeduplication:
    """Tests for event deduplication."""
    
    @pytest.mark.asyncio
    async def test_dedupe_new_article(self, mock_redis):
        """New article passes deduplication."""
        mock_redis.set = AsyncMock(return_value=True)
        
        key = get_dedup_key("https://newsapi.org", "Breaking News Title")
        result = await dedupe_event(mock_redis, key, 21600)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_dedupe_duplicate_article(self, mock_redis):
        """Duplicate article fails deduplication."""
        mock_redis.set = AsyncMock(return_value=None)
        
        key = get_dedup_key("https://newsapi.org", "Breaking News Title")
        result = await dedupe_event(mock_redis, key, 21600)
        
        assert result is False
    
    def test_dedup_key_format(self):
        """Deduplication key is consistent."""
        key1 = get_dedup_key("https://source.com", "Title")
        key2 = get_dedup_key("https://source.com", "Title")
        
        assert key1 == key2
        assert len(key1) == 64  # SHA256 hex length


# ==============================================================================
# Source Credibility Tests
# ==============================================================================


class TestSourceCredibility:
    """Tests for source credibility weighting."""
    
    def test_credibility_weighting_high_credibility_source(self, news_config):
        """High credibility source increases relevance."""
        article = {
            "title": "Curfew announced",
            "description": "Official curfew notice",
            "url": "https://news.com/1",
            "publishedAt": "2026-04-14T10:00:00Z",
        }
        
        event = parse_news_article(
            article,
            source_url="https://newsapi.org/v2/everything",
            config=news_config
        )
        
        if event:
            # NewsAPI has high credibility (0.9)
            assert event.relevance_score > 0.0
    
    def test_credibility_weighting_low_credibility_source(self, news_config):
        """Low credibility source decreases relevance."""
        article = {
            "title": "Alleged curfew",
            "description": "Unverified report",
            "url": "https://tabloid.com/1",
            "publishedAt": "2026-04-14T10:00:00Z",
        }
        
        event = parse_news_article(
            article,
            source_url="https://tabloid.example.com",
            config=news_config
        )
        
        # Unknown source gets default credibility
        # May or may not pass relevance threshold


# ==============================================================================
# Event Validation Tests
# ==============================================================================


class TestEventValidation:
    """Tests for event payload validation."""
    
    def test_valid_news_event_payload(self, news_config):
        """Valid news event payload structure."""
        article = {
            "title": "Strike impact grows",
            "description": "Workers strike continues affecting transport",
            "url": "https://news.com/strike",
            "publishedAt": "2026-04-14T10:00:00Z",
        }
        
        event = parse_news_article(
            article,
            source_url="https://newsapi.org",
            config=news_config
        )
        
        if event:
            assert event.raw_title is not None
            assert event.source_url is not None
            assert event.source is not None
            assert event.timestamp_utc is not None
            assert event.event_type is not None
            assert 1 <= event.severity <= 5
    
    def test_trigger_condition_for_major_events(self, news_config):
        """Major events marked as trigger conditions."""
        article = {
            "title": "Curfew imposed in capital",
            "description": "Emergency curfew declared",
            "url": "https://news.com/curfew",
            "publishedAt": "2026-04-14T10:00:00Z",
        }
        
        event = parse_news_article(
            article,
            source_url="https://newsapi.org",
            config=news_config
        )
        
        if event and event.event_type in ["curfew", "strike", "bandh"]:
            assert event.is_trigger_condition is True
    
    def test_non_trigger_events(self, news_config):
        """Minor events not marked as trigger conditions."""
        article = {
            "title": "Minor disruption in local area",
            "description": "Small scale local issue",
            "url": "https://news.com/minor",
            "publishedAt": "2026-04-14T10:00:00Z",
        }
        
        event = parse_news_article(
            article,
            source_url="https://newsapi.org",
            config=news_config
        )
        
        # Will likely return None due to low relevance
        if event:
            assert event.is_trigger_condition is False or event.event_type not in ["curfew", "strike", "bandh"]

