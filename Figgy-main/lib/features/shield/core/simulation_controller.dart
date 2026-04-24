import 'package:flutter/material.dart';

enum DemoDisruption { none, rain, heat, traffic, strike }

class SimulationController extends ChangeNotifier {
  DemoDisruption _active = DemoDisruption.none;
  int _eventStep = 5; // Starts with initial rides shown

  DemoDisruption get active => _active;
  int get eventStep => _eventStep;

  void toggle(DemoDisruption type, bool on) {
    if (!on) {
      _active = DemoDisruption.none;
      _eventStep = 5;
    } else {
      _active = type;
      _runDemoSequence();
    }
    notifyListeners();
  }

  bool isOn(DemoDisruption type) => _active == type;

  void _runDemoSequence() {
    // Immediately show the final state (all disruption cards and claim trigger)
    _eventStep = 8; 
    notifyListeners();
  }

}
