from collections import deque
import json
from typing import Dict, List, Tuple
import time

class WeatherSmoother:
    def __init__(self, window_minutes: int = 5):
        self.window_seconds = window_minutes * 60
        self.data: Dict[str, deque] = {}  # city -> deque of (timestamp, rainfall)

    def update(self, city: str, rainfall_mm_per_hr: float, timestamp: float) -> float:
        if city not in self.data:
            self.data[city] = deque()

        # Add new reading
        self.data[city].append((timestamp, rainfall_mm_per_hr))

        # Remove old readings
        while self.data[city] and self.data[city][0][0] < timestamp - self.window_seconds:
            self.data[city].popleft()

        # Compute average
        if self.data[city]:
            total = sum(r for t, r in self.data[city])
            smoothed = total / len(self.data[city])
        else:
            smoothed = rainfall_mm_per_hr  # If no data, use current

        return smoothed

    def to_dict(self) -> dict:
        return {
            'window_seconds': self.window_seconds,
            'data': {city: list(deq) for city, deq in self.data.items()}
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'WeatherSmoother':
        smoother = cls(window_minutes=data['window_seconds'] / 60)
        smoother.data = {city: deque(lst) for city, lst in data['data'].items()}
        return smoother