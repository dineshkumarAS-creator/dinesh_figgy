import pytest
from datetime import datetime, timezone
from normalisation_service.normalisers.aqi_normaliser import AQINormaliser


class TestAQINormaliser:
    @pytest.fixture
    def normaliser(self):
        return AQINormaliser("normalisation_config.yaml")

    def test_normalise_iqair_aqi(self, normaliser):
        raw_event = {
            "location": "Delhi",
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            "aqi_value": 150,
            "pm25": 35.0,
            "provider": "iqair"
        }

        result = normaliser.normalise(raw_event)

        assert result.location == "Delhi"
        assert result.normalised_aqi_us == 150  # Pass through for IQAir
        assert result.normalised_pm25_ug_m3 == 35.0
        assert not result.is_hazardous

    def test_normalise_cpcb_naqi(self, normaliser):
        raw_event = {
            "location": "Delhi",
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            "aqi_value": 250,  # NAQI
            "provider": "cpcb"
        }

        result = normaliser.normalise(raw_event)

        # Should convert to US AQI equivalent
        assert result.normalised_aqi_us > 150  # Higher range
        assert result.is_hazardous  # >300? Wait, 250 NAQI might map to lower

    def test_normalise_hazardous_aqi(self, normaliser):
        raw_event = {
            "location": "Delhi",
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            "aqi_value": 400,
            "provider": "iqair"
        }

        result = normaliser.normalise(raw_event)

        assert result.is_hazardous

    def test_normalise_pollutants(self, normaliser):
        raw_event = {
            "location": "Delhi",
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            "aqi_value": 100,
            "pm25": 25.0,
            "pm10": 50.0,
            "no2": 20.0,  # ppb
            "provider": "iqair"
        }

        result = normaliser.normalise(raw_event)

        assert result.normalised_pm25_ug_m3 == 25.0
        assert result.normalised_pm10_ug_m3 == 50.0
        assert result.normalised_no2_ug_m3 == 20.0 * 1.88  # ppb to µg/m³