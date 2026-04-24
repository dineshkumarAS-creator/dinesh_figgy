import pytest
import respx
import httpx
from datetime import datetime, timezone
from dataclasses import replace

import weather_connector
from weather_connector import parse_weather_payload, fetch_weather_payload, ingest_weather_cycle
from schemas import WeatherPayload


class DummyProducer:
    def __init__(self) -> None:
        self.sent_topic = None
        self.sent_payload = None

    async def send_and_wait(self, topic: str, payload: bytes) -> None:
        self.sent_topic = topic
        self.sent_payload = payload


def test_parse_weather_payload_openweather_trigger() -> None:
    sample = {
        "rain": {"1h": 45.0},
        "wind": {"speed": 4.5},
        "visibility": 8000,
        "weather": [{"id": 502}],
        "dt": 1710000000,
        "coord": {"lat": 12.97, "lon": 77.59},
        "main": {"temp": 26.7},
        "name": "Bengaluru",
    }

    payload = parse_weather_payload(sample, source="openweather", city="Bengaluru")

    assert isinstance(payload, WeatherPayload)
    assert payload.rainfall_mm_per_hr == 45.0
    assert payload.wind_speed_kmh == pytest.approx(16.2)
    assert payload.is_trigger_condition is True
    assert payload.city == "Bengaluru"
    assert payload.timestamp_utc.tzinfo == timezone.utc


@respx.mock
@pytest.mark.asyncio
async def test_fetch_weather_payload_falls_back_to_imd(monkeypatch: pytest.MonkeyPatch) -> None:
    config = replace(
        weather_connector.get_weather_config(),
        api_key="fake",
        imd_api_url="https://imd.test/weather",
        imd_api_key="fake",
        city="Mumbai",
    )

    async def fake_openweather(session: httpx.AsyncClient, config_value: weather_connector.WeatherConnectorConfig) -> dict:
        raise weather_connector.RetryError("openweather failed")

    monkeypatch.setattr(weather_connector, "fetch_openweather", fake_openweather)
    respx.get("https://imd.test/weather").respond(200, json={
        "rainfall_mm_per_hr": 0.0,
        "wind_speed_kmh": 12.0,
        "visibility_m": 9000,
        "weather_condition_code": 800,
        "timestamp_utc": "2026-04-13T08:05:00Z",
        "city": "Mumbai",
        "lat": 19.0760,
        "lon": 72.8777,
        "temperature_c": 28.0,
    })

    payload = await fetch_weather_payload(config)
    assert payload.city == "Mumbai"
    assert payload.is_trigger_condition is False


@pytest.mark.asyncio
async def test_ingest_weather_cycle_publishes(monkeypatch: pytest.MonkeyPatch) -> None:
    config = replace(weather_connector.get_weather_config(), kafka_topic="weather_test", city="TestCity")
    payload = WeatherPayload(
        rainfall_mm_per_hr=0.0,
        temperature_c=25.0,
        wind_speed_kmh=10.0,
        visibility_m=10000,
        weather_condition_code=800,
        timestamp_utc=datetime.now(timezone.utc),
        city="TestCity",
        lat=0.0,
        lon=0.0,
        is_trigger_condition=False,
    )

    async def fake_fetch_weather_payload(config_value: weather_connector.WeatherConnectorConfig) -> WeatherPayload:
        return payload

    monkeypatch.setattr(weather_connector, "fetch_weather_payload", fake_fetch_weather_payload)
    producer = DummyProducer()

    await ingest_weather_cycle(producer, config)

    assert producer.sent_topic == "weather_test"
    assert b'"city": "TestCity"' in producer.sent_payload
