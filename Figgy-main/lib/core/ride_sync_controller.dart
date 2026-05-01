import 'package:flutter/material.dart';

class RideSyncController extends ChangeNotifier {
  static final RideSyncController instance = RideSyncController._();
  RideSyncController._();

  int _currentRideIndex = 1;
  double _rideProgress = 0.0;
  bool _isRiskDetected = false;
  bool _isRideBlocked = false;

  int get currentRideIndex => _currentRideIndex;
  double get rideProgress => _rideProgress;
  bool get isRiskDetected => _isRiskDetected;
  bool get isRideBlocked => _isRideBlocked;

  void updateProgress(double progress) {
    if (progress.isNaN || progress.isInfinite) {
      _rideProgress = 0.0;
    } else {
      _rideProgress = progress.clamp(0.0, 1.0);
    }
    notifyListeners();
  }

  void setRideIndex(int index) {
    _currentRideIndex = index;
    _rideProgress = 0.0;
    
    _isRiskDetected = (index == 4);
    _isRideBlocked = (index >= 5);
    
    notifyListeners();
  }

  void nextRide() {
    if (_currentRideIndex < 6) {
      setRideIndex(_currentRideIndex + 1);
    }
  }

  void reset() {
    _currentRideIndex = 1;
    _rideProgress = 0.0;
    _isRiskDetected = false;
    _isRideBlocked = false;
    notifyListeners();
  }
}
