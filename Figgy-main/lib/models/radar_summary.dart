import 'package:flutter/foundation.dart';

@immutable
class RadarAlert {
  final String severity; // "None" | "Moderate" | "High"
  final String message;

  const RadarAlert({
    required this.severity,
    required this.message,
  });

  factory RadarAlert.fromJson(Map<String, dynamic> json) {
    return RadarAlert(
      severity: json['severity'] as String? ?? 'None',
      message: json['message'] as String? ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
    'severity': severity,
    'message': message,
  };

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is RadarAlert &&
          runtimeType == other.runtimeType &&
          severity == other.severity &&
          message == other.message;

  @override
  int get hashCode => severity.hashCode ^ message.hashCode;

  @override
  String toString() => 'RadarAlert(severity: $severity, message: $message)';
}

@immutable
class ZoneData {
  final String zoneId;
  final String zoneName;
  final String zoneLetter;
  final String riskLabel;
  final String alertText;
  final String primarySignal;
  final double distanceKm;
  final double riskScore;
  final double opportunityIndex;
  final int etaMin;
  final int orderCount;
  final int boostInr;
  final bool recommended;

  const ZoneData({
    required this.zoneId,
    required this.zoneName,
    required this.zoneLetter,
    required this.riskLabel,
    required this.alertText,
    required this.primarySignal,
    required this.distanceKm,
    required this.riskScore,
    required this.opportunityIndex,
    required this.etaMin,
    required this.orderCount,
    required this.boostInr,
    required this.recommended,
  });

  factory ZoneData.fromJson(Map<String, dynamic> json) {
    return ZoneData(
      zoneId: json['zone_id'] as String? ?? '',
      zoneName: json['zone_name'] as String? ?? '',
      zoneLetter: json['zone_letter'] as String? ?? '',
      riskLabel: json['risk_label'] as String? ?? 'Safe',
      alertText: json['alert_text'] as String? ?? '',
      primarySignal: json['primary_signal'] as String? ?? 'none',
      distanceKm: (json['distance_km'] as num?)?.toDouble() ?? 0.0,
      riskScore: (json['risk_score'] as num?)?.toDouble() ?? 0.0,
      opportunityIndex: (json['opportunity_index'] as num?)?.toDouble() ?? 0.0,
      etaMin: json['eta_min'] as int? ?? 0,
      orderCount: json['order_count'] as int? ?? 0,
      boostInr: json['boost_inr'] as int? ?? 0,
      recommended: json['recommended'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() => {
    'zone_id': zoneId,
    'zone_name': zoneName,
    'zone_letter': zoneLetter,
    'risk_label': riskLabel,
    'alert_text': alertText,
    'primary_signal': primarySignal,
    'distance_km': distanceKm,
    'risk_score': riskScore,
    'opportunity_index': opportunityIndex,
    'eta_min': etaMin,
    'order_count': orderCount,
    'boost_inr': boostInr,
    'recommended': recommended,
  };

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ZoneData &&
          runtimeType == other.runtimeType &&
          zoneId == other.zoneId &&
          zoneName == other.zoneName &&
          zoneLetter == other.zoneLetter &&
          riskLabel == other.riskLabel &&
          alertText == other.alertText &&
          primarySignal == other.primarySignal &&
          distanceKm == other.distanceKm &&
          riskScore == other.riskScore &&
          opportunityIndex == other.opportunityIndex &&
          etaMin == other.etaMin &&
          orderCount == other.orderCount &&
          boostInr == other.boostInr &&
          recommended == other.recommended;

  @override
  int get hashCode =>
      zoneId.hashCode ^
      zoneName.hashCode ^
      zoneLetter.hashCode ^
      riskLabel.hashCode ^
      alertText.hashCode ^
      primarySignal.hashCode ^
      distanceKm.hashCode ^
      riskScore.hashCode ^
      opportunityIndex.hashCode ^
      etaMin.hashCode ^
      orderCount.hashCode ^
      boostInr.hashCode ^
      recommended.hashCode;

  @override
  String toString() =>
      'ZoneData(zoneId: $zoneId, zoneName: $zoneName, riskScore: $riskScore, opportunityIndex: $opportunityIndex, recommended: $recommended)';
}

@immutable
class ClaimPending {
  final double amountInr;
  final String reason;
  final String claimId;
  final String status;

  const ClaimPending({
    required this.amountInr,
    required this.reason,
    required this.claimId,
    required this.status,
  });

  factory ClaimPending.fromJson(Map<String, dynamic> json) {
    return ClaimPending(
      amountInr: (json['amount_inr'] as num?)?.toDouble() ?? 0.0,
      reason: json['reason'] as String? ?? '',
      claimId: json['claim_id'] as String? ?? '',
      status: json['status'] as String? ?? 'pending',
    );
  }

  Map<String, dynamic> toJson() => {
    'amount_inr': amountInr,
    'reason': reason,
    'claim_id': claimId,
    'status': status,
  };

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ClaimPending &&
          runtimeType == other.runtimeType &&
          amountInr == other.amountInr &&
          reason == other.reason &&
          claimId == other.claimId &&
          status == other.status;

  @override
  int get hashCode => amountInr.hashCode ^ reason.hashCode ^ claimId.hashCode ^ status.hashCode;

  @override
  String toString() =>
      'ClaimPending(amountInr: $amountInr, reason: $reason, claimId: $claimId, status: $status)';
}

@immutable
class EarningsToday {
  final double earnedInr;
  final double protectedInr;
  final int ridesDone;
  final ClaimPending? claimPending;

  const EarningsToday({
    required this.earnedInr,
    required this.protectedInr,
    required this.ridesDone,
    this.claimPending,
  });

  factory EarningsToday.fromJson(Map<String, dynamic> json) {
    return EarningsToday(
      earnedInr: (json['earned_inr'] as num?)?.toDouble() ?? 0.0,
      protectedInr: (json['protected_inr'] as num?)?.toDouble() ?? 0.0,
      ridesDone: json['rides_done'] as int? ?? 0,
      claimPending: json['claim_pending'] != null
          ? ClaimPending.fromJson(json['claim_pending'] as Map<String, dynamic>)
          : null,
    );
  }

  Map<String, dynamic> toJson() => {
    'earned_inr': earnedInr,
    'protected_inr': protectedInr,
    'rides_done': ridesDone,
    'claim_pending': claimPending?.toJson(),
  };

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is EarningsToday &&
          runtimeType == other.runtimeType &&
          earnedInr == other.earnedInr &&
          protectedInr == other.protectedInr &&
          ridesDone == other.ridesDone &&
          claimPending == other.claimPending;

  @override
  int get hashCode =>
      earnedInr.hashCode ^
      protectedInr.hashCode ^
      ridesDone.hashCode ^
      claimPending.hashCode;

  @override
  String toString() =>
      'EarningsToday(earnedInr: $earnedInr, protectedInr: $protectedInr, ridesDone: $ridesDone, claimPending: $claimPending)';
}

@immutable
class RiderRisk {
  final bool inRiskZone;
  final bool protectionAutoOn;
  final String zoneId;
  final String riskLabel;

  const RiderRisk({
    required this.inRiskZone,
    required this.protectionAutoOn,
    required this.zoneId,
    required this.riskLabel,
  });

  factory RiderRisk.fromJson(Map<String, dynamic> json) {
    return RiderRisk(
      inRiskZone: json['in_risk_zone'] as bool? ?? false,
      protectionAutoOn: json['protection_auto_on'] as bool? ?? false,
      zoneId: json['zone_id'] as String? ?? '',
      riskLabel: json['risk_label'] as String? ?? 'Safe',
    );
  }

  Map<String, dynamic> toJson() => {
    'in_risk_zone': inRiskZone,
    'protection_auto_on': protectionAutoOn,
    'zone_id': zoneId,
    'risk_label': riskLabel,
  };

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is RiderRisk &&
          runtimeType == other.runtimeType &&
          inRiskZone == other.inRiskZone &&
          protectionAutoOn == other.protectionAutoOn &&
          zoneId == other.zoneId &&
          riskLabel == other.riskLabel;

  @override
  int get hashCode =>
      inRiskZone.hashCode ^
      protectionAutoOn.hashCode ^
      zoneId.hashCode ^
      riskLabel.hashCode;

  @override
  String toString() =>
      'RiderRisk(inRiskZone: $inRiskZone, protectionAutoOn: $protectionAutoOn, zoneId: $zoneId, riskLabel: $riskLabel)';
}

@immutable
class RadarSummary {
  final RadarAlert alert;
  final List<ZoneData> zones;
  final EarningsToday earningsToday;
  final RiderRisk riderRisk;

  const RadarSummary({
    required this.alert,
    required this.zones,
    required this.earningsToday,
    required this.riderRisk,
  });

  factory RadarSummary.fromJson(Map<String, dynamic> json) {
    return RadarSummary(
      alert: RadarAlert.fromJson(json['alert'] as Map<String, dynamic>? ?? {}),
      zones: (json['zones'] as List<dynamic>? ?? [])
          .cast<Map<String, dynamic>>()
          .map((z) => ZoneData.fromJson(z))
          .toList(),
      earningsToday: EarningsToday.fromJson(
          json['earnings_today'] as Map<String, dynamic>? ?? {}),
      riderRisk: RiderRisk.fromJson(json['rider_risk'] as Map<String, dynamic>? ?? {}),
    );
  }

  Map<String, dynamic> toJson() => {
    'alert': alert.toJson(),
    'zones': zones.map((z) => z.toJson()).toList(),
    'earnings_today': earningsToday.toJson(),
    'rider_risk': riderRisk.toJson(),
  };

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is RadarSummary &&
          runtimeType == other.runtimeType &&
          alert == other.alert &&
          zones == other.zones &&
          earningsToday == other.earningsToday &&
          riderRisk == other.riderRisk;

  @override
  int get hashCode =>
      alert.hashCode ^
      zones.hashCode ^
      earningsToday.hashCode ^
      riderRisk.hashCode;

  @override
  String toString() =>
      'RadarSummary(alert: $alert, zones: ${zones.length} zones, earningsToday: $earningsToday, riderRisk: $riderRisk)';
}
