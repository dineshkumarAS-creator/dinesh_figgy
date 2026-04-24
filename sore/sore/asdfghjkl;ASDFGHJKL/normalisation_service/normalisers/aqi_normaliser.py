from datetime import datetime, timezone
from typing import Dict, Any, Optional
import yaml
from pydantic import BaseModel

from normalisation_service.schemas.normalised_schemas import NormalisedAQIData


class AQINormaliser:
    def __init__(self, config_path: str = "normalisation_config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)["aqi"]

    def normalise(self, raw_event: Dict[str, Any]) -> NormalisedAQIData:
        """Normalise AQI data to US AQI scale and standard units."""
        location = raw_event["location"]
        timestamp = raw_event["timestamp"]
        aqi_value = raw_event["aqi_value"]
        pm25 = raw_event.get("pm25")
        pm10 = raw_event.get("pm10")
        o3 = raw_event.get("o3")
        no2 = raw_event.get("no2")
        so2 = raw_event.get("so2")
        co = raw_event.get("co")
        provider = raw_event.get("provider", "unknown")

        # Normalise AQI to US scale
        normalised_aqi = self._normalise_aqi_to_us(aqi_value, provider)

        # Normalise pollutants to µg/m³
        normalised_pm25 = pm25  # Assume already µg/m³
        normalised_pm10 = pm10
        normalised_no2 = no2 * self.config["pollutant_units"]["no2"]["ppb_to_ug_m3"] if no2 else None
        # Similar for others, but keeping simple

        is_hazardous = normalised_aqi > 300

        return NormalisedAQIData(
            location=location,
            timestamp=timestamp,
            aqi_value=aqi_value,
            pm25=pm25,
            pm10=pm10,
            o3=o3,
            no2=no2,
            so2=so2,
            co=co,
            normalised_aqi_us=normalised_aqi,
            normalised_pm25_ug_m3=normalised_pm25,
            normalised_pm10_ug_m3=normalised_pm10,
            normalised_no2_ug_m3=normalised_no2,
            normalised_at=datetime.now(timezone.utc),
            is_hazardous=is_hazardous,
        )

    def _normalise_aqi_to_us(self, aqi: int, provider: str) -> int:
        """Convert NAQI to US AQI if needed."""
        if provider.lower() == "iqair":
            return aqi  # Already US AQI

        # For CPCB NAQI, use lookup table
        naqi_ranges = self.config["naqi_to_us_aqi"]
        for range_str, us_range in naqi_ranges.items():
            min_naqi, max_naqi = map(int, range_str.split("-"))
            if min_naqi <= aqi <= max_naqi:
                min_us, max_us = map(int, us_range.split("-"))
                # Linear interpolation
                ratio = (aqi - min_naqi) / (max_naqi - min_naqi)
                return int(min_us + ratio * (max_us - min_us))

        return aqi  # Fallback