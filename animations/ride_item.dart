import 'package:flutter/material.dart';

enum RidePhase {
  hidden,
  inProgress,
  completedMonitor,
  queued,
  disruptionWarning,
  blocked,
  claimTriggered,
}

class RideItem {
  final String id;
  final String fromZone;
  final String toZone;
  final String timeLabel;
  final double earnedAmount;
  final int staggerIndex;

  RidePhase phase;
  double progressPct;

  // Monitor panel
  String? riskScore;
  String? ordersStatus;
  String? gpsStatus;

  // Disruption
  String? disruptionType;
  String? disruptionArea;
  String? deliveriesImpact;
  String? disruptionDuration;
  String? protectionStatus;

  // Blocked
  double? lossAmount;

  // Claim
  double? payoutAmount;
  String? claimTime;

  RideItem({
    required this.id,
    required this.fromZone,
    required this.toZone,
    required this.timeLabel,
    required this.earnedAmount,
    this.staggerIndex = 0,
    this.phase = RidePhase.hidden,
    this.progressPct = 0.0,
    this.riskScore,
    this.ordersStatus,
    this.gpsStatus,
    this.disruptionType,
    this.disruptionArea,
    this.deliveriesImpact,
    this.disruptionDuration,
    this.protectionStatus,
    this.lossAmount,
    this.payoutAmount,
    this.claimTime,
  });

  bool get showProgressBar    => phase == RidePhase.inProgress;
  bool get showMonitorPanel   => phase == RidePhase.completedMonitor;
  bool get showDisruptionCard => phase == RidePhase.disruptionWarning;
  bool get showBlockedCard    => phase == RidePhase.blocked || phase == RidePhase.claimTriggered;
  bool get showClaimCard      => phase == RidePhase.claimTriggered;
  bool get isAmberPulsing     => phase == RidePhase.disruptionWarning;
  bool get isNegativeAmount   => phase == RidePhase.blocked || phase == RidePhase.claimTriggered;

  Color circleColor() {
    switch (phase) {
      case RidePhase.inProgress:
        return const Color(0xFF1d4ed8);
      case RidePhase.completedMonitor:
      case RidePhase.queued:
      case RidePhase.claimTriggered:
        return const Color(0xFF16a34a);
      case RidePhase.disruptionWarning:
        return const Color(0xFFd97706);
      case RidePhase.blocked:
        return const Color(0xFFdc2626);
      default:
        return const Color(0xFF374151);
    }
  }

  Color circleTextColor() {
    switch (phase) {
      case RidePhase.inProgress:
        return const Color(0xFF93c5fd);
      case RidePhase.completedMonitor:
      case RidePhase.queued:
      case RidePhase.claimTriggered:
        return const Color(0xFF4ade80);
      case RidePhase.disruptionWarning:
        return const Color(0xFFfbbf24);
      case RidePhase.blocked:
        return const Color(0xFFf87171);
      default:
        return const Color(0xFF9ca3af);
    }
  }

  Color lineColor() {
    switch (phase) {
      case RidePhase.completedMonitor:
      case RidePhase.queued:
      case RidePhase.claimTriggered:
        return const Color(0xFF16a34a);
      case RidePhase.disruptionWarning:
        return const Color(0xFFd97706);
      case RidePhase.blocked:
        return const Color(0xFFdc2626);
      default:
        return const Color(0xFF374151);
    }
  }

  double get displayAmount {
    if (isNegativeAmount) return -(lossAmount ?? earnedAmount);
    return earnedAmount;
  }
}
