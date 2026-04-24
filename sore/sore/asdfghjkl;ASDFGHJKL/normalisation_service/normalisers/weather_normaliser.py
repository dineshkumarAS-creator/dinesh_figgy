from datetime import datetime, timezone
from typing import Dict, Any, Optional
import yaml
from pydantic import BaseModel

from normalisation_service.schemas.normalised_schemas import NormalisedWeatherData


class WeatherNormaliser:
    def __init__(self, config_path: str = "normalisation_config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)["weather"]

    def normalise(self, raw_event: Dict[str, Any]) -> NormalisedWeatherData:
        """Normalise weather data to SI units and add quality metrics."""
        # Extract raw fields
        location = raw_event["location"]
        timestamp = raw_event["timestamp"]
        temperature_c = raw_event.get("temperature_c")
        humidity_pct = raw_event.get("humidity_pct")
        wind_speed_kmh = raw_event.get("wind_speed_kmh")
        pressure_hpa = raw_event.get("pressure_hpa")
        description = raw_event.get("description")
        source_unit = raw_event.get("source_unit", {})  # e.g., {"rainfall": "mm_3hr"}

        # Normalise rainfall
        normalised_rainfall = None
        if "rainfall" in raw_event:
            rainfall = raw_event["rainfall"]
            unit = source_unit.get("rainfall", "mm_hr")
            if unit == "mm_3hr":
                normalised_rainfall = rainfall * self.config["rainfall_conversions"]["mm_3hr_to_mm_hr"]
            elif unit == "mm_day":
                normalised_rainfall = rainfall * self.config["rainfall_conversions"]["mm_day_to_mm_hr"]
            else:
                normalised_rainfall = rainfall

        # Normalise temperature
        normalised_temperature = temperature_c
        if temperature_c is None and "temperature_k" in raw_event:
            normalised_temperature = raw_event["temperature_k"] + self.config["temperature_conversions"]["kelvin_to_celsius"]
        elif temperature_c is None and "temperature_f" in raw_event:
            f = raw_event["temperature_f"]
            normalised_temperature = (f - 32) * 5/9

        # Normalise wind speed
        normalised_wind_speed = None
        if wind_speed_kmh is not None:
            normalised_wind_speed = wind_speed_kmh * self.config["wind_speed_conversions"]["kmh_to_ms"]
        elif "wind_speed_knots" in raw_event:
            normalised_wind_speed = raw_event["wind_speed_knots"] * self.config["wind_speed_conversions"]["knots_to_ms"]

        # Normalise pressure (assume already hPa, but could add conversions if needed)
        normalised_pressure = pressure_hpa

        # Calculate source quality score
        quality_score = self._calculate_quality_score(raw_event)

        return NormalisedWeatherData(
            location=location,
            timestamp=timestamp,
            temperature_c=temperature_c,
            humidity_pct=humidity_pct,
            wind_speed_kmh=wind_speed_kmh,
            pressure_hpa=pressure_hpa,
            description=description,
            normalised_rainfall_mm_hr=normalised_rainfall,
            normalised_temperature_c=normalised_temperature,
            normalised_wind_speed_ms=normalised_wind_speed,
            normalised_pressure_hpa=normalised_pressure,
            normalised_at=datetime.now(timezone.utc),
            source_quality_score=quality_score,
        )

    def _calculate_quality_score(self, raw_event: Dict[str, Any]) -> float:
        """Calculate quality score based on freshness, provider, missing fields."""
        score = 1.0

        # Freshness penalty
        if "timestamp" in raw_event:
            age_hours = (datetime.now(timezone.utc).timestamp() - raw_event["timestamp"] / 1000) / 3600
            score -= age_hours * self.config["source_quality"]["freshness_penalty_per_hour"]

        # Provider reliability
        provider = raw_event.get("provider", "default")
        score *= self.config["source_quality"]["provider_reliability"].get(provider, 0.7)

        # Missing field penalty
        required_fields = ["temperature_c", "humidity_pct", "wind_speed_kmh", "pressure_hpa"]
        missing_count = sum(1 for field in required_fields if raw_event.get(field) is None)
        score -= missing_count * self.config["source_quality"]["missing_field_penalty"]

        return max(0.0, min(1.0, score))