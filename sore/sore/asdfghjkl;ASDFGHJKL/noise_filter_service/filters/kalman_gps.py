import numpy as np
from filterpy.kalman import KalmanFilter
from typing import Optional, Tuple
import json

class GPSKalmanFilter:
    def __init__(self, process_noise_q: float = 1e-6):
        self.kf = KalmanFilter(dim_x=4, dim_z=2)
        self.process_noise_q = process_noise_q
        self.initialized = False

    def initialize(self, lat: float, lon: float, accuracy_m: float):
        # Initial state: [lat, lon, vel_lat, vel_lon]
        self.kf.x = np.array([lat, lon, 0.0, 0.0])
        # Initial covariance: high uncertainty
        self.kf.P = np.eye(4) * 100.0
        # State transition matrix (constant velocity model)
        self.kf.F = np.eye(4)
        # Measurement matrix: measure lat, lon
        self.kf.H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]])
        # Process noise
        self.kf.Q = np.eye(4) * self.process_noise_q
        # Measurement noise: based on accuracy
        self.kf.R = np.eye(2) * (accuracy_m ** 2)
        self.initialized = True
        self.last_time = None  # Will set on first update

    def update(self, lat: float, lon: float, accuracy_m: float, timestamp: float) -> Tuple[float, float, float, float]:
        if not self.initialized:
            self.initialize(lat, lon, accuracy_m)
            self.last_time = timestamp
            return lat, lon, 0.0, accuracy_m  # Initial, no smoothing yet

        # Calculate dt
        dt = timestamp - self.last_time
        if dt <= 0:
            dt = 0.1  # Minimum dt to avoid division by zero

        # Update F with dt
        self.kf.F[0, 2] = dt
        self.kf.F[1, 3] = dt

        # Update Q (process noise scales with dt)
        self.kf.Q = np.eye(4) * self.process_noise_q * dt

        # Update R
        self.kf.R = np.eye(2) * (accuracy_m ** 2)

        # Predict
        self.kf.predict()

        # Update with measurement
        z = np.array([lat, lon])
        self.kf.update(z)

        # Extract smoothed values
        smoothed_lat = self.kf.x[0]
        smoothed_lon = self.kf.x[1]
        vel_lat = self.kf.x[2]
        vel_lon = self.kf.x[3]
        estimated_speed_ms = np.sqrt(vel_lat**2 + vel_lon**2)
        position_uncertainty_m = np.sqrt(self.kf.P[0, 0] + self.kf.P[1, 1])  # Approximate

        self.last_time = timestamp
        return smoothed_lat, smoothed_lon, estimated_speed_ms, position_uncertainty_m

    def to_dict(self) -> dict:
        return {
            'x': self.kf.x.tolist(),
            'P': self.kf.P.tolist(),
            'F': self.kf.F.tolist(),
            'H': self.kf.H.tolist(),
            'Q': self.kf.Q.tolist(),
            'R': self.kf.R.tolist(),
            'initialized': self.initialized,
            'last_time': self.last_time,
            'process_noise_q': self.process_noise_q
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'GPSKalmanFilter':
        kf = cls(process_noise_q=data['process_noise_q'])
        kf.kf.x = np.array(data['x'])
        kf.kf.P = np.array(data['P'])
        kf.kf.F = np.array(data['F'])
        kf.kf.H = np.array(data['H'])
        kf.kf.Q = np.array(data['Q'])
        kf.kf.R = np.array(data['R'])
        kf.initialized = data['initialized']
        kf.last_time = data['last_time']
        return kf