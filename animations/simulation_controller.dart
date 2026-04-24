import 'dart:async';
import 'package:flutter/material.dart';
import '../models/ride_item.dart';
import '../core/animation_constants.dart';

enum DisruptionMode { rain, heat, strike, flood, none }

class SimulationController extends ChangeNotifier {

  // ── Core state ─────────────────────────────────────────────────────────────
  int eventStep = 0;
  DisruptionMode? active;

  // ── Live backend ───────────────────────────────────────────────────────────
  bool useLiveBackend = false;
  String? currentClaimId;
  String claimStatus = 'idle'; // 'idle' | 'verifying' | 'paid' | 'failed'

  // ── Navigator key (set once from MaterialApp) ──────────────────────────────
  static final GlobalKey<NavigatorState> navigatorKey =
      GlobalKey<NavigatorState>();

  // ── Rides ──────────────────────────────────────────────────────────────────
  List<RideItem> rides = [];

  // ── Timers ─────────────────────────────────────────────────────────────────
  final List<Timer> _demoTimers = [];
  Timer? _weatherPollTimer;

  // ── Constructor ────────────────────────────────────────────────────────────
  SimulationController() {
    _initRides();
  }

  void _initRides() {
    rides = [
      RideItem(id: 'R1', fromZone: 'Anna Nagar', toZone: 'Vadapalani',
          timeLabel: '9:10 AM', earnedAmount: 80, staggerIndex: 0),
      RideItem(id: 'R2', fromZone: 'Koyambedu', toZone: 'T Nagar',
          timeLabel: '10:05 AM', earnedAmount: 120, staggerIndex: 1),
      RideItem(id: 'R3', fromZone: 'T Nagar', toZone: 'Mylapore',
          timeLabel: '10:58 AM', earnedAmount: 100, staggerIndex: 2),
      RideItem(id: 'R4', fromZone: 'Mylapore', toZone: '—',
          timeLabel: '11:30 AM', earnedAmount: 150, staggerIndex: 3),
      RideItem(id: 'R5', fromZone: 'Velachery', toZone: '—',
          timeLabel: '1:40 PM', earnedAmount: 0, staggerIndex: 4),
    ];
  }

  // ── Demo sequence ──────────────────────────────────────────────────────────

  void startDemoSequence() {
    _cancelDemoTimers();
    useLiveBackend = false;
    eventStep = 0;
    _initRides();
    notifyListeners();

    // Each tuple: (delay from previous step, step function)
    final steps = <(Duration, VoidCallback)>[
      (ShieldAnimations.step1To2Delay, _step1),
      (ShieldAnimations.step2To3Delay, _step2),
      (ShieldAnimations.step3To4Delay, _step3),
      (ShieldAnimations.step4To5Delay, _step4),
      (ShieldAnimations.step5To6Delay, _step5),
      (ShieldAnimations.step6To7Delay, _step6),
      (ShieldAnimations.step7To8Delay, _step7),
    ];

    Duration elapsed = Duration.zero;
    for (final s in steps) {
      elapsed += s.$1;
      final fn = s.$2;
      _demoTimers.add(Timer(elapsed, () {
        if (!useLiveBackend) fn();
      }));
    }
  }

  /// Call this to restore demo mode from live mode.
  void runDemoMode() {
    _weatherPollTimer?.cancel();
    _weatherPollTimer = null;
    useLiveBackend = false;
    claimStatus = 'idle';
    currentClaimId = null;
    startDemoSequence();
  }

  // ── Demo step functions ────────────────────────────────────────────────────

  void _step1() {
    eventStep = 1;
    rides[0].phase = RidePhase.inProgress;
    notifyListeners();
  }

  void _step2() {
    eventStep = 2;
    rides[0].phase = RidePhase.completedMonitor;
    rides[0].riskScore = 'LOW · clear';
    rides[0].ordersStatus = 'Normal rate';
    rides[0].gpsStatus = 'Consistent';
    rides[1].phase = RidePhase.queued;
    rides[2].phase = RidePhase.queued;
    notifyListeners();
  }

  void _step3() {
    eventStep = 3;
    rides[1].phase = RidePhase.completedMonitor;
    rides[2].phase = RidePhase.completedMonitor;
    notifyListeners();
  }

  void _step4() {
    eventStep = 4;
    rides[3].phase = RidePhase.queued;
    notifyListeners();
  }

  void _step5() {
    // Disruption detected
    eventStep = 5;
    active = DisruptionMode.rain;
    rides[3].phase = RidePhase.disruptionWarning;
    rides[3].disruptionType = 'Heavy rain detected · 11:30 AM';
    rides[3].disruptionArea = 'T Nagar';
    rides[3].deliveriesImpact = 'Slowing — orders dropped 80%';
    rides[3].disruptionDuration = '2 hrs 15 min';
    rides[3].protectionStatus = 'Active';
    notifyListeners();
  }

  void _step6() {
    // Ride blocked
    eventStep = 6;
    rides[4].phase = RidePhase.blocked;
    rides[4].lossAmount = 300;
    notifyListeners();
  }

  void _step7() {
    // Claim auto-triggered
    eventStep = 7;
    rides[4].phase = RidePhase.claimTriggered;
    rides[4].payoutAmount = 198;
    rides[4].claimTime = '1:45 PM';
    claimStatus = 'verifying';
    notifyListeners();
  }

  // ── Live backend polling ───────────────────────────────────────────────────

  Future<void> startLivePolling(String workerId, String zone) async {
    useLiveBackend = true;
    _cancelDemoTimers();
    _weatherPollTimer?.cancel();
    _weatherPollTimer = Timer.periodic(
      const Duration(seconds: 30),
      (_) => _pollWeather(workerId, zone),
    );
  }

  Future<void> _pollWeather(String workerId, String zone) async {
    try {
      // ── Replace this stub with real API call ──────────────────────────────
      // final weather = await ApiService().getZoneWeather(zone);
      final weather = <String, dynamic>{
        'disruption_active': false,
        'disruption_type': 'rain',
      };
      // ─────────────────────────────────────────────────────────────────────

      if (weather['disruption_active'] == true && claimStatus == 'idle') {
        active = _mapDisruptionType(weather['disruption_type'] as String);
        eventStep = 6;
        notifyListeners();
        await triggerParametricClaim(workerId);
      } else {
        notifyListeners();
      }
    } catch (_) {
      // swallow poll errors silently — no crash on network issues
    }
  }

  Future<void> triggerParametricClaim(String workerId) async {
    try {
      // ── Replace this stub with real API call ──────────────────────────────
      // final res = await ApiService().triggerAutoClaim(workerId);
      final res = <String, dynamic>{
        'claim_id': 'demo_${DateTime.now().millisecondsSinceEpoch}',
      };
      // ─────────────────────────────────────────────────────────────────────

      currentClaimId = res['claim_id'] as String;
      claimStatus = 'verifying';
      eventStep = 8;

      rides[4].phase = RidePhase.claimTriggered;
      rides[4].payoutAmount = 198;
      rides[4].claimTime = '1:45 PM';

      notifyListeners();

      navigatorKey.currentState?.pushNamed(
        '/claim-processing',
        arguments: {'claim_id': currentClaimId, 'mode': 'auto'},
      );
    } catch (_) {
      claimStatus = 'idle';
      notifyListeners();
    }
  }

  // ── Helpers ────────────────────────────────────────────────────────────────

  DisruptionMode _mapDisruptionType(String type) {
    switch (type) {
      case 'rain':      return DisruptionMode.rain;
      case 'pollution': return DisruptionMode.heat;
      case 'strike':    return DisruptionMode.strike;
      case 'flood':     return DisruptionMode.flood;
      default:          return DisruptionMode.rain;
    }
  }

  void _cancelDemoTimers() {
    for (final t in _demoTimers) {
      t.cancel();
    }
    _demoTimers.clear();
  }

  @override
  void dispose() {
    _cancelDemoTimers();
    _weatherPollTimer?.cancel();
    super.dispose();
  }
}
