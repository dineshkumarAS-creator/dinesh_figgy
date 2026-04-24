import pytest
import numpy as np
from ..filters.kalman_gps import GPSKalmanFilter

def test_gps_kalman_initialization():
    kf = GPSKalmanFilter()
    assert not kf.initialized
    smoothed_lat, smoothed_lon, speed, uncertainty = kf.update(10.0, 20.0, 5.0, 1000.0)
    assert kf.initialized
    assert smoothed_lat == 10.0
    assert smoothed_lon == 20.0
    assert speed == 0.0
    assert uncertainty == 5.0

def test_gps_kalman_convergence():
    kf = GPSKalmanFilter(process_noise_q=1e-6)
    # Simulate noisy GPS data around true position
    true_lat, true_lon = 10.0, 20.0
    timestamps = np.linspace(0, 10, 100)
    noisy_lat = true_lat + np.random.normal(0, 0.01, 100)
    noisy_lon = true_lon + np.random.normal(0, 0.01, 100)
    accuracies = np.full(100, 0.01)

    errors = []
    for i, (lat, lon, acc, t) in enumerate(zip(noisy_lat, noisy_lon, accuracies, timestamps)):
        smoothed_lat, smoothed_lon, _, _ = kf.update(lat, lon, acc, t)
        error = np.sqrt((smoothed_lat - true_lat)**2 + (smoothed_lon - true_lon)**2)
        errors.append(error)

    # Check that error decreases over time (convergence)
    initial_error = np.mean(errors[:10])
    final_error = np.mean(errors[-10:])
    assert final_error < initial_error

@pytest.mark.benchmark
def test_gps_kalman_latency(benchmark):
    kf = GPSKalmanFilter()
    kf.update(10.0, 20.0, 5.0, 1000.0)  # Initialize

    def update_func():
        kf.update(10.01, 20.01, 5.0, 1001.0)

    result = benchmark(update_func)
    assert result.stats.mean < 0.01  # <10ms