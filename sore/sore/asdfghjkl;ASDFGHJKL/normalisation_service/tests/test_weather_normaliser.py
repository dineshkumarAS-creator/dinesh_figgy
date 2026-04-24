import pytest
from datetime import datetime, timezone
from normalisation_service.normalisers.weather_normaliser import WeatherNormaliser


class TestWeatherNormaliser:
    @pytest.fixture
    def normaliser(self):
        return WeatherNormaliser("normalisation_config.yaml")

    def test_normalise_basic_weather(self, normaliser):
        raw_event = {
            "location": "Delhi",
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            "temperature_c": 25.0,
            "humidity_pct": 60.0,
            "wind_speed_kmh": 10.0,
            "pressure_hpa": 1013.0,
            "description": "Clear sky",
            "provider": "openweather"
        }

        result = normaliser.normalise(raw_event)

        assert result.location == "Delhi"
        assert result.normalised_temperature_c == 25.0
        assert result.normalised_wind_speed_ms == 10.0 * 0.2778  # kmh to ms
        assert result.normalised_pressure_hpa == 1013.0
        assert result.source_quality_score > 0

    def test_normalise_rainfall_conversion(self, normaliser):
        raw_event = {
            "location": "Delhi",
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            "rainfall": 3.0,
            "source_unit": {"rainfall": "mm_3hr"},
            "provider": "openweather"
        }

        result = normaliser.normalise(raw_event)

        assert result.normalised_rainfall_mm_hr == 3.0 * (1/3)  # mm_3hr to mm_hr

    def test_normalise_temperature_conversion(self, normaliser):
        raw_event = {
            "location": "Delhi",
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            "temperature_k": 298.15,  # 25°C in Kelvin
            "provider": "openweather"
        }

        result = normaliser.normalise(raw_event)

        assert result.normalised_temperature_c == 25.0

    def test_calculate_quality_score(self, normaliser):
        # Fresh data from reliable provider
        raw_event = {
            "location": "Delhi",
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            "temperature_c": 25.0,
            "humidity_pct": 60.0,
            "wind_speed_kmh": 10.0,
            "pressure_hpa": 1013.0,
            "provider": "openweather"
        }

        result = normaliser.normalise(raw_event)
        assert result.source_quality_score >= 0.8  # High score

    def test_quality_score_with_missing_fields(self, normaliser):
        raw_event = {
            "location": "Delhi",
            "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
            "temperature_c": 25.0,
            # Missing other fields
            "provider": "openweather"
        }

        result = normaliser.normalise(raw_event)
        assert result.source_quality_score < 1.0  # Penalty for missing fields