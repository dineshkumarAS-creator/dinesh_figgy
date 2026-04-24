import pytest
from ..filters.weather_smoother import WeatherSmoother

def test_weather_smoother_update():
    smoother = WeatherSmoother(window_minutes=1)  # 1 min for test
    smoothed = smoother.update('Delhi', 10.0, 1000.0)
    assert smoothed == 10.0

    smoothed = smoother.update('Delhi', 20.0, 1001.0)
    assert smoothed == 15.0

    # Add old data
    smoothed = smoother.update('Delhi', 30.0, 1061.0)  # >60s, should remove first
    assert len(smoother.data['Delhi']) == 2
    assert smoothed == 25.0