"""
conftest.py - Shared pytest configuration and fixtures
"""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def mock_zone_config_global(monkeypatch):
    """Mock zone config globally for all tests."""
    config = MagicMock()
    config.zones = {
        "DL-CENTRAL-01": {
            "centroid_lat": 28.6139,
            "centroid_lon": 77.2090,
            "lat_range": {"min": 28.60, "max": 28.65},
            "lon_range": {"min": 77.20, "max": 77.25},
            "location_tolerance_km": 2.0,
        }
    }
    config.get_zone_centroid = lambda zone_id: (
        config.zones[zone_id]["centroid_lat"],
        config.zones[zone_id]["centroid_lon"],
    )
    
    # Patch get_zone_config in soft_verify package
    monkeypatch.setattr(
        "soft_verify.evaluator.get_zone_config", 
        lambda: config
    )
    monkeypatch.setattr(
        "soft_verify.challenge.get_zone_config",
        lambda: config
    )
    
    return config
