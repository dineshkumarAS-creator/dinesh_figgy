import numpy as np
from filterpy.kalman import KalmanFilter
from typing import Dict, Tuple
import time

class IMUKalmanFilter:
    def __init__(self, process_noise_q: float = 1e-4, measurement_noise_r: float = 0.1, zupt_threshold: float = 0.1, zupt_duration: float = 2.0):
        self.axes = ['x', 'y', 'z']
        self.filters: Dict[str, KalmanFilter] = {}
        for axis in self.axes:
            kf = KalmanFilter(dim_x=1, dim_z=1)
            kf.x = np.array([0.0])  # Initial accel
            kf.P = np.array([[1.0]])  # Initial covariance
            kf.F = np.array([[1.0]])  # No change
            kf.H = np.array([[1.0]])
            kf.Q = np.array([[process_noise_q]])
            kf.R = np.array([[measurement_noise_r]])
            self.filters[axis] = kf
        self.zupt_threshold = zupt_threshold
        self.zupt_duration = zupt_duration
        self.low_accel_start = None
        self.is_stationary = False

    def update(self, accel_x: float, accel_y: float, accel_z: float, timestamp: float) -> Tuple[float, float, float, bool]:
        # Update each axis filter
        smoothed = {}
        for axis, value in zip(self.axes, [accel_x, accel_y, accel_z]):
            kf = self.filters[axis]
            kf.predict()
            z = np.array([value])
            kf.update(z)
            smoothed[axis] = kf.x[0]

        # ZUPT: check overall accel magnitude
        accel_magnitude = np.sqrt(accel_x**2 + accel_y**2 + accel_z**2)
        if accel_magnitude < self.zupt_threshold:
            if self.low_accel_start is None:
                self.low_accel_start = timestamp
            elif timestamp - self.low_accel_start >= self.zupt_duration:
                self.is_stationary = True
                # Optionally, reset velocity if we had it, but since we don't, just flag
        else:
            self.low_accel_start = None
            self.is_stationary = False

        return smoothed['x'], smoothed['y'], smoothed['z'], self.is_stationary

    def to_dict(self) -> dict:
        data = {
            'filters': {axis: {
                'x': kf.x.tolist(),
                'P': kf.P.tolist(),
                'F': kf.F.tolist(),
                'H': kf.H.tolist(),
                'Q': kf.Q.tolist(),
                'R': kf.R.tolist()
            } for axis, kf in self.filters.items()},
            'zupt_threshold': self.zupt_threshold,
            'zupt_duration': self.zupt_duration,
            'low_accel_start': self.low_accel_start,
            'is_stationary': self.is_stationary
        }
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'IMUKalmanFilter':
        imu_kf = cls(zupt_threshold=data['zupt_threshold'], zupt_duration=data['zupt_duration'])
        for axis, kf_data in data['filters'].items():
            kf = imu_kf.filters[axis]
            kf.x = np.array(kf_data['x'])
            kf.P = np.array(kf_data['P'])
            kf.F = np.array(kf_data['F'])
            kf.H = np.array(kf_data['H'])
            kf.Q = np.array(kf_data['Q'])
            kf.R = np.array(kf_data['R'])
        imu_kf.low_accel_start = data['low_accel_start']
        imu_kf.is_stationary = data['is_stationary']
        return imu_kf