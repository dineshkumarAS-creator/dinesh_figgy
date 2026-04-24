from __future__ import annotations
from pathlib import Path
from typing import Dict, List

import yaml
from pydantic import AnyHttpUrl, Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
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
    keywords: List[str] = Field(default_factory=lambda: ["curfew", "bandh", "strike", "protest", "section 144", "shutdown"])
    source_credibility: Dict[str, float] = Field(default_factory=lambda: {"newsapi.org": 0.9, "gnews.io": 0.85})

    spacy_model: str = "en_core_web_sm"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @classmethod
    def load(cls, path: str = "config.yaml") -> "AppConfig":
        content = Path(path).read_text()
        raw = yaml.safe_load(content) or {}
        return cls(**raw)
