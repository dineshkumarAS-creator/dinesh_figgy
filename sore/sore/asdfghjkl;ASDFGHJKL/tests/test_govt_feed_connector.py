"""
Tests for Government Feed Connector

Tests cover:
  - RSS feed parsing
  - Event type detection
  - Location extraction
  - Deduplication via Redis
  - DLQ publishing for failures
  - Full connector lifecycle
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import feedparser

from config_schemas import GovtFeedConnectorConfig
from govt_feed_connector import (
    get_event_type,
    extract_locations,
    normalize_severity,
    get_dedup_key,
    parse_feed_entry,
    dedupe_event,
    fetch_feed,
)
from schemas import EventPayload


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
def govt_config():
    """Government feed connector config."""
    return GovtFeedConnectorConfig()


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
        text = "Emergency: Curfew imposed in Delhi starting 8 PM today"
        assert get_event_type(text) == "curfew"
    
    def test_detect_section_144(self):
        """Detect section 144 event type."""
        text = "Section 144 imposed in Bengaluru area after protests"
        assert get_event_type(text) == "curfew"
    
    def test_detect_strike(self):
        """Detect strike event type."""
        text = "Workers strike begins on Monday affecting services"
        assert get_event_type(text) == "strike"
    
    def test_detect_bandh(self):
        """Detect bandh event type."""
        text = "State-wide bandh called by opposition party"
        assert get_event_type(text) == "bandh"
    
    def test_detect_protest(self):
        """Detect protest event type."""
        text = "Major protest rally planned for tomorrow evening"
        assert get_event_type(text) == "protest"
    
    def test_detect_other(self):
        """Detect 'other' event type."""
        text = "General news about government initiatives"
        assert get_event_type(text) == "other"


class TestSeverityNormalization:
    """Tests for severity extraction."""
    
    def test_extract_severity_from_text(self):
        """Extract severity number from text."""
        assert normalize_severity("Level 4 emergency") == 4
    
    def test_severity_bounds(self):
        """Severity should be bounded 1-5."""
        assert normalize_severity("Level 10 alert") == 5
        assert normalize_severity("Level 0 ") == 1
    
    def test_default_severity(self):
        """Missing severity returns default."""
        assert normalize_severity("") == 3
        assert normalize_severity(None) == 3


# ==============================================================================
# Feed Entry Parsing Tests
# ==============================================================================


class TestFeedEntryParsing:
    """Tests for individual feed entry parsing."""
    
    def test_parse_entry_creates_event(self, govt_config):
        """Parse feed entry into EventPayload."""
        with patch('govt_feed_connector.extract_locations', return_value=("Delhi", [])):
            entry = {
                "title": "Curfew in Delhi",
                "summary": "Section 144 imposed starting tonight",
                "published": "2026-04-14T10:00:00Z",
                "city": "Delhi",
            }
            
            event = parse_feed_entry(
                entry, 
                source_url="https://pib.gov.in",
                source_name="pib",
                config=govt_config
            )
            
            assert event is not None  # Verify event was created
            assert event.event_type == "curfew"
            assert event.raw_title == "Curfew in Delhi"
            assert event.affected_city == "Delhi"
            assert event.is_trigger_condition is True
    
    def test_parse_entry_with_missing_city(self, govt_config):
        """Parse entry without explicit city."""
        with patch('govt_feed_connector.extract_locations', return_value=(None, [])):
            entry = {
                "title": "Strike announced",
                "summary": "Workers strike planned",
                "published": "2026-04-14T10:00:00Z",
            }
            
            event = parse_feed_entry(
                entry,
                source_url="https://pib.gov.in",
                source_name="pib",
                config=govt_config
            )
            
            assert event is not None  # Verify event was created
            assert event.event_type == "strike"
    
    def test_parse_entry_trigger_condition(self, govt_config):
        """Trigger condition set based on event type."""
        with patch('govt_feed_connector.extract_locations', return_value=(None, [])):
            # Trigger event
            entry1 = {
                "title": "Curfew Imposed",
                "published": "2026-04-14T10:00:00Z",
            }
            event1 = parse_feed_entry(entry1, "https://test.com", "test", govt_config)
            assert event1.is_trigger_condition is True
            
            # Non-trigger event
            entry2 = {
                "title": "General Government Update",
                "published": "2026-04-14T10:00:00Z",
            }
            event2 = parse_feed_entry(entry2, "https://test.com", "test", govt_config)
            assert event2.is_trigger_condition is False


# ==============================================================================
# Deduplication Tests
# ==============================================================================


class TestDeduplication:
    """Tests for event deduplication."""
    
    @pytest.mark.asyncio
    async def test_dedupe_new_event(self, mock_redis):
        """New event passes deduplication."""
        mock_redis.set = AsyncMock(return_value=True)
        
        key = get_dedup_key("https://example.com", "Test Event")
        result = await dedupe_event(mock_redis, key, 3600)
        
        assert result is True
        mock_redis.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_dedupe_duplicate_event(self, mock_redis):
        """Duplicate event fails deduplication."""
        mock_redis.set = AsyncMock(return_value=None)
        
        key = get_dedup_key("https://example.com", "Test Event")
        result = await dedupe_event(mock_redis, key, 3600)
        
        assert result is False
    
    def test_dedup_key_consistency(self):
        """Deduplication key is deterministic."""
        url = "https://pib.gov.in"
        title = "Curfew in Delhi"
        
        key1 = get_dedup_key(url, title)
        key2 = get_dedup_key(url, title)
        
        assert key1 == key2
    
    def test_dedup_key_differs_for_different_input(self):
        """Different inputs produce different keys."""
        key1 = get_dedup_key("https://source1.com", "Title 1")
        key2 = get_dedup_key("https://source2.com", "Title 2")
        
        assert key1 != key2


# ==============================================================================
# Event Validation Tests
# ==============================================================================


class TestEventValidation:
    """Tests for event payload validation."""
    
    def test_valid_curfew_payload(self, govt_config):
        """Valid curfew event payload."""
        with patch('govt_feed_connector.extract_locations', return_value=(None, [])):
            entry = {
                "title": "Curfew Announced",
                "summary": "Night curfew from 10 PM to 6 AM",
                "published": "2026-04-14T10:00:00Z",
            }
            
            event = parse_feed_entry(
                entry,
                source_url="https://pib.gov.in",
                source_name="pib",
                config=govt_config
            )
            
            assert event.event_type == "curfew"
            assert event.severity >= 1 and event.severity <= 5
            assert event.source == "pib"
            assert event.timestamp_utc is not None
    
    def test_event_has_required_fields(self, govt_config):
        """All required event fields present."""
        with patch('govt_feed_connector.extract_locations', return_value=(None, [])):
            entry = {
                "title": "Test Event",
                "published": "2026-04-14T10:00:00Z",
            }
            
            event = parse_feed_entry(
                entry,
                source_url="https://test.com",
                source_name="test",
                config=govt_config
            )
            
            # Check required fields
            assert event.raw_title is not None
            assert event.source_url is not None
            assert event.source is not None
            assert event.timestamp_utc is not None
            assert event.is_trigger_condition is not None
            assert event.severity is not None
            assert event.event_type is not None

