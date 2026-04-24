"""
Configuration schemas and loaders for data connectors and services.

Provides:
  - Structured configuration classes for each connector/service
  - Validation and schema definitions
  - Factory methods for creating configured instances
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import AnyHttpUrl, Field, HttpUrl, field_validator, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict


# ==============================================================================
# Base Configuration Classes
# ==============================================================================


class BaseConnectorConfig(BaseSettings):
    """Base configuration for all data connectors."""
    
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = ""
    kafka_dlq_topic: str = ""
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# ==============================================================================
# Specific Connector Configurations
# ==============================================================================


class AQIConnectorConfig(BaseConnectorConfig):
    """Configuration for Air Quality Index (AQI) data connector."""
    
    cpcb_api_url: str = "https://api.cpcbccr.com/caaqms/fetch_all_records"
    cpcb_api_key: str = ""
    
    iqair_api_url: HttpUrl = "https://api.airvisual.com/v2/nearest_city"
    iqair_api_key: str = ""
    
    kafka_topic: str = "aqi"
    kafka_dlq_topic: str = "aqi_dlq"
    
    aqi_city: str = "Delhi"
    poll_interval_seconds: int = 300
    
    @field_validator("poll_interval_seconds")
    @classmethod
    def validate_poll_interval(cls, v: int) -> int:
        if v < 10:
            raise ValueError("poll_interval_seconds must be at least 10")
        return v


class WeatherConnectorConfig(BaseConnectorConfig):
    """Configuration for weather data connector."""
    
    openweathermap_api_url: HttpUrl = "https://api.openweathermap.org/data/2.5/weather"
    openweathermap_api_key: str = ""
    
    kafka_topic: str = "weather"
    kafka_dlq_topic: str = "weather_dlq"
    
    weather_cities: List[str] = Field(default_factory=lambda: ["Delhi", "Bengaluru", "Chennai"])
    poll_interval_seconds: int = 300
    
    rainfall_threshold_mm_hr: float = 35.0
    wind_speed_threshold_kmh: float = 40.0
    visibility_threshold_m: int = 1000


class GovtFeedConnectorConfig(BaseConnectorConfig):
    """Configuration for Government feed connector."""
    
    kafka_topic: str = "events"
    kafka_dlq_topic: str = "events_dlq"
    
    # Government data feeds
    data_gov_feed: HttpUrl = "https://data.gov.in/rss"
    pib_feed: HttpUrl = "https://archive.pib.gov.in/rss/press_release.rss"
    state_feeds: List[HttpUrl] = Field(default_factory=list)
    
    # Redis for deduplication
    redis_url: str = "redis://localhost:6379/0"
    redis_ttl_seconds: int = 21600  # 6 hours
    
    # NLP configuration
    spacy_model: str = "en_core_web_sm"
    
    # Keywords for event detection
    keywords: List[str] = Field(
        default_factory=lambda: [
            "curfew",
            "bandh",
            "strike",
            "protest",
            "section 144",
            "shutdown",
        ]
    )
    
    # Feed polling
    poll_interval_seconds: int = 600
    fetch_timeout_seconds: float = 20.0
    
    # Event configuration
    default_severity: int = 3
    max_events_per_feed: int = 50


class NewsConnectorConfig(BaseConnectorConfig):
    """Configuration for news feed connector."""
    
    kafka_topic: str = "events"
    kafka_dlq_topic: str = "events_dlq"
    
    # News APIs
    newsapi_url: HttpUrl = "https://newsapi.org/v2/everything"
    newsapi_key: str = ""
    
    gnews_url: HttpUrl = "https://gnews.io/api/v4/search"
    gnews_key: str = ""
    
    # Redis for deduplication
    redis_url: str = "redis://localhost:6379/0"
    redis_ttl_seconds: int = 21600  # 6 hours
    
    # NLP configuration
    spacy_model: str = "en_core_web_sm"
    
    # Keywords and credibility
    keywords: List[str] = Field(
        default_factory=lambda: [
            "curfew",
            "bandh",
            "strike",
            "protest",
            "section 144",
            "shutdown",
        ]
    )
    source_credibility: Dict[str, float] = Field(
        default_factory=lambda: {
            "newsapi.org": 0.9,
            "gnews.io": 0.85,
        }
    )
    
    # Feed polling
    poll_interval_seconds: int = 300
    fetch_timeout_seconds: float = 20.0
    
    # Event configuration
    default_severity: int = 3
    min_relevance_score: float = 0.6
    max_events_per_source: int = 30


class LegacyAppConfig(BaseSettings):
    """Legacy combined configuration (backward compatibility)."""
    
    kafka_bootstrap_servers: str = "localhost:9092"
    events_topic: str = "events"
    events_dlq_topic: str = "events_dlq"
    redis_url: str = "redis://localhost:6379/0"
    redis_ttl_seconds: int = 21600

    data_gov_feed: HttpUrl = Field(default="https://data.gov.in/rss")
    pib_feed: HttpUrl = Field(default="https://archive.pib.gov.in/rss/press_release.rss")
    state_feeds: List[HttpUrl] = Field(default_factory=list)

    newsapi_url: HttpUrl = Field(default="https://newsapi.org/v2/everything")
    newsapi_key: str = Field(default="")
    gnews_url: HttpUrl = Field(default="https://gnews.io/api/v4/search")
    gnews_key: str = Field(default="")
    keywords: List[str] = Field(
        default_factory=lambda: ["curfew", "bandh", "strike", "protest", "section 144", "shutdown"]
    )
    source_credibility: Dict[str, float] = Field(
        default_factory=lambda: {"newsapi.org": 0.9, "gnews.io": 0.85}
    )

    spacy_model: str = "en_core_web_sm"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @classmethod
    def load(cls, path: str = "config.yaml") -> "LegacyAppConfig":
        """Load configuration from YAML file."""
        content = Path(path).read_text()
        raw = yaml.safe_load(content) or {}
        return cls(**raw)


# ==============================================================================
# Configuration Factory
# ==============================================================================


class ConfigFactory:
    """Factory for loading connector configurations."""
    
    @staticmethod
    def load_aqi_config(path: Optional[str] = None) -> AQIConnectorConfig:
        """Load AQI connector configuration."""
        if path:
            content = Path(path).read_text()
            raw = yaml.safe_load(content).get("aqi", {})
            return AQIConnectorConfig(**raw)
        return AQIConnectorConfig()
    
    @staticmethod
    def load_weather_config(path: Optional[str] = None) -> WeatherConnectorConfig:
        """Load weather connector configuration."""
        if path:
            content = Path(path).read_text()
            raw = yaml.safe_load(content).get("weather", {})
            return WeatherConnectorConfig(**raw)
        return WeatherConnectorConfig()
    
    @staticmethod
    def load_govt_feed_config(path: Optional[str] = None) -> GovtFeedConnectorConfig:
        """Load government feed connector configuration."""
        if path:
            content = Path(path).read_text()
            raw = yaml.safe_load(content).get("govt_feed", {})
            return GovtFeedConnectorConfig(**raw)
        return GovtFeedConnectorConfig()
    
    @staticmethod
    def load_news_config(path: Optional[str] = None) -> NewsConnectorConfig:
        """Load news feed connector configuration."""
        if path:
            content = Path(path).read_text()
            raw = yaml.safe_load(content).get("news", {})
            return NewsConnectorConfig(**raw)
        return NewsConnectorConfig()
    
    @staticmethod
    def load_legacy_config(path: str = "config.yaml") -> LegacyAppConfig:
        """Load legacy combined configuration (backward compatible)."""
        return LegacyAppConfig.load(path)
    
    @staticmethod
    def load_all_configs(path: str = "config.yaml") -> Dict[str, BaseConnectorConfig]:
        """Load all connector configurations from single file."""
        aqi = ConfigFactory.load_aqi_config(path)
        weather = ConfigFactory.load_weather_config(path)
        govt_feed = ConfigFactory.load_govt_feed_config(path)
        news = ConfigFactory.load_news_config(path)
        
        return {
            "aqi": aqi,
            "weather": weather,
            "govt_feed": govt_feed,
            "news": news,
        }
