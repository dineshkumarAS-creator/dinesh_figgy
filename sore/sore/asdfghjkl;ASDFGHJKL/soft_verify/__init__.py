"""
Soft Verification Service - Shared Utilities

Zone configuration and helper functions.
"""

import yaml
import os
from typing import Optional


class ZoneConfig:
    """Zone coordinate configuration."""

    def __init__(self, config_path: Optional[str] = None):
        """Load zone configuration."""
        if config_path is None:
            # Try relative to this module first
            module_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(module_dir, "zone_config.yaml")
        
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)
        self.zones = self.config.get("zones", {})

    def get_zone_centroid(self, zone_id: str) -> tuple[float, float]:
        """Get (lat, lon) for zone centroid."""
        zone = self.zones.get(zone_id)
        if not zone:
            raise ValueError(f"Zone {zone_id} not found")
        return (zone["centroid_lat"], zone["centroid_lon"])

    def get_zone_bounds(
        self, zone_id: str
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        """Get lat_range, lon_range for zone."""
        zone = self.zones.get(zone_id)
        if not zone:
            raise ValueError(f"Zone {zone_id} not found")
        
        lat_range_dict = zone.get("lat_range", {})
        lon_range_dict = zone.get("lon_range", {})
        
        lat_range = (lat_range_dict.get("min", 0), lat_range_dict.get("max", 0))
        lon_range = (lon_range_dict.get("min", 0), lon_range_dict.get("max", 0))
        return lat_range, lon_range


# Singleton instance
_zone_config: Optional[ZoneConfig] = None


def get_zone_config() -> ZoneConfig:
    """Get singleton zone config."""
    global _zone_config
    if not _zone_config:
        _zone_config = ZoneConfig()
    return _zone_config
