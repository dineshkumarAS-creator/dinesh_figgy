import pytest
import numpy as np
from ..filters.kalman_imu import IMUKalmanFilter

def test_imu_kalman_update():
    kf = IMUKalmanFilter()
    ax, ay, az, stationary = kf.update(0.1, 0.0, 9.8, 1000.0)
    assert ax == pytest.approx(0.1, abs=0.1)
    assert ay == pytest.approx(0.0, abs=0.1)
    assert az == pytest.approx(9.8, abs=0.1)
    assert not stationary

def test_imu_zupt_detection():
    kf = IMUKalmanFilter(zupt_threshold=0.1, zupt_duration=2.0)
    # Simulate low accel for 2s
    timestamps = [1000.0, 1001.0, 1002.0, 1003.0]
    for t in timestamps:
        ax, ay, az, stationary = kf.update(0.05, 0.05, 9.81, t)
    assert stationary

@pytest.mark.benchmark
def test_imu_kalman_latency(benchmark):
    kf = IMUKalmanFilter()

    def update_func():
        kf.update(0.1, 0.0, 9.8, 1000.0)

    result = benchmark(update_func)
    assert result.stats.mean < 0.01