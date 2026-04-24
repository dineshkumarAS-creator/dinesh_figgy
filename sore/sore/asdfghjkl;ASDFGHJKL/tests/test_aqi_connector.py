import pytest
import respx
import httpx
from datetime import datetime, timezone
from dataclasses import replace

import aqi_connector
from aqi_connector import parse_aqi_payload, normalize_aqi, fetch_aqi_payload, ingest_aqi_cycle
from schemas import AQIPayload


class DummyProducer:
    def __init__(self) -> None:
        self.sent_topic = None
        self.sent_payload = None

    async def send_and_wait(self, topic: str, payload: bytes) -> None:
        self.sent_topic = topic
        self.sent_payload = payload


def test_parse_aqi_payload_cpcb_trigger() -> None:
    sample = {
        "aqi_index_current": 410,
        "pm25": 145.0,
        "pm10": 250.0,
        "no2": 90.0,
        "station_id": "CPCB-DELHI-01",
        "city": "Delhi",
        "lat": 28.7041,
        "lon": 77.1025,
        "timestamp_utc": "2026-04-13T08:10:00Z",
    }

    payload = parse_aqi_payload(sample, source="cpcb", city="Delhi")

    assert isinstance(payload, AQIPayload)
    assert payload.aqi_index_standardized == 410
    assert payload.is_trigger_condition is True
    assert payload.city == "Delhi"
    assert payload.timestamp_utc.tzinfo == timezone.utc


def test_normalize_aqi_clamps_values() -> None:
    assert normalize_aqi(520) == 500
    assert normalize_aqi(-20) == 0
    assert normalize_aqi(250.3) == 250


@respx.mock
@pytest.mark.asyncio
async def test_fetch_aqi_payload_falls_back_to_iqair(monkeypatch: pytest.MonkeyPatch) -> None:
    config = replace(
        aqi_connector.get_aqi_config(),
        cpcb_api_url="https://cpcb.test/aqi",
        cpcb_api_key="fake",
        iqair_api_url="https://api.airvisual.com/v2/nearest_city",
        iqair_api_key="fake",
        city="Delhi",
    )

    async def fake_fetch_cpcb(session: httpx.AsyncClient, config_value: aqi_connector.AQIConnectorConfig) -> dict:
        raise aqi_connector.RetryError("cpcb failed")

    monkeypatch.setattr(aqi_connector, "fetch_cpcb", fake_fetch_cpcb)
    respx.get("https://api.airvisual.com/v2/nearest_city").respond(200, json={
        "data": {
            "city": {"name": "Delhi"},
            "location": {"coordinates": [77.1025, 28.7041]},
            "current": {"pollution": {"aqius": 220, "p2": 110, "p1": 210, "n2": 70, "ts": "2026-04-13T08:15:00Z"}},
        }
    })

    payload = await fetch_aqi_payload(config)

    assert payload.city == "Delhi"
    assert payload.aqi_index_standardized == 220
    assert payload.is_trigger_condition is False


@pytest.mark.asyncio
async def test_ingest_aqi_cycle_publishes(monkeypatch: pytest.MonkeyPatch) -> None:
    config = replace(aqi_connector.get_aqi_config(), kafka_topic="aqi_test", city="TestCity")
    payload = AQIPayload(
        aqi_index_current=120.0,
        aqi_index_standardized=120,
        pm25=60.0,
        pm10=110.0,
        no2=30.0,
        station_id="TEST-01",
        city="TestCity",
        lat=0.0,
        lon=0.0,
        timestamp_utc=datetime.now(timezone.utc),
        is_trigger_condition=False,
    )

    async def fake_fetch_aqi_payload(config_value: aqi_connector.AQIConnectorConfig) -> AQIPayload:
        return payload

    monkeypatch.setattr(aqi_connector, "fetch_aqi_payload", fake_fetch_aqi_payload)
    producer = DummyProducer()

    await ingest_aqi_cycle(producer, config)

    assert producer.sent_topic == "aqi_test"
    assert b'"station_id": "TEST-01"' in producer.sent_payload
