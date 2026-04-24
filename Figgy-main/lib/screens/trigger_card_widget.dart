// lib/screens/trigger_card_widget.dart
// ---------------------------------------------------------------------------
// Reusable Trigger Card Widget — Figgy GigShield Parametric Screen
//
// Usage:
//   TriggerCardWidget(
//     triggerKey : 'RAIN',
//     label      : 'Rainfall',
//     icon       : Icons.water_drop_rounded,
//     unit       : 'mm',
//     thresholdData: weatherData['thresholds']['RAIN'],   // Map from API
//     hasLiveData: true,
//   )
//
// API field expected (from GET /api/weather/zone/<zone>):
//   thresholds.RAIN / AQI / CURFEW = {
//     triggered        : bool,
//     label            : str,
//     detected_value   : num | bool,
//     threshold_value  : num | bool,
//     operator         : str,
//     unit             : str,
//     limit            : num | null,
//   }
// ---------------------------------------------------------------------------

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

// ── Design tokens (dark theme, matches parametric_screen.dart) ─────────────
class TriggerCardColors {
  static const bg      = Color(0xFF1A1D27);
  static const card    = Color(0xFF22263A);
  static const orange  = Color(0xFFD85A30);
  static const blue    = Color(0xFF3B82F6);
  static const border  = Color(0xFF2D3148);
  static const txt1    = Color(0xFFF1F5F9);
  static const txt2    = Color(0xFF94A3B8);
  static const txt3    = Color(0xFF475569);
}

// ── Status pill state ─────────────────────────────────────────────────────
enum TriggerStatus { triggered, ok, monitoring }

class TriggerCardWidget extends StatelessWidget {
  /// Key into TRIGGER_THRESHOLDS: "RAIN", "AQI", or "CURFEW"
  final String triggerKey;

  /// Display name shown in the card body
  final String label;

  /// Leading icon (rain drop, smoke cloud, warning flag, etc.)
  final IconData icon;

  /// Unit suffix appended to detected/limit values: "mm", "AQI", ""
  final String unit;

  /// Raw threshold map from `weatherData['thresholds'][triggerKey]`
  /// Can be null while loading or offline.
  final Map<String, dynamic>? thresholdData;

  /// Whether live API data has been received at all.
  /// Controls whether pill shows OK vs MONITORING.
  final bool hasLiveData;

  const TriggerCardWidget({
    super.key,
    required this.triggerKey,
    required this.label,
    required this.icon,
    required this.unit,
    this.thresholdData,
    this.hasLiveData = false,
  });

  // ── Derived state ──────────────────────────────────────────────────────
  bool get _triggered => (thresholdData?['triggered'] as bool?) ?? false;

  TriggerStatus get _status {
    if (_triggered) return TriggerStatus.triggered;
    if (hasLiveData) return TriggerStatus.ok;
    return TriggerStatus.monitoring;
  }

  String get _subLabel {
    final detected = thresholdData?['detected_value'];
    final limit    = thresholdData?['threshold_value'];
    if (detected == null || limit == null) return '';

    if (triggerKey == 'CURFEW') {
      return 'Status: ${detected == true ? 'Active' : 'Inactive'} · Triggers when: Active';
    }
    final dStr = detected is double
        ? (detected % 1 == 0 ? '${detected.toInt()}' : detected.toStringAsFixed(1))
        : '$detected';
    final lStr = limit is double
        ? (limit % 1 == 0 ? '${limit.toInt()}' : limit.toStringAsFixed(1))
        : '$limit';
    return 'Detected $dStr$unit · Limit $lStr$unit';
  }

  // ── Pill appearance ────────────────────────────────────────────────────
  String get _pillLabel {
    switch (_status) {
      case TriggerStatus.triggered:  return 'TRIGGERED';
      case TriggerStatus.ok:         return 'OK';
      case TriggerStatus.monitoring: return 'MONITORING';
    }
  }

  Color get _pillBg {
    switch (_status) {
      case TriggerStatus.triggered:  return TriggerCardColors.orange;
      case TriggerStatus.ok:         return TriggerCardColors.border;
      case TriggerStatus.monitoring: return TriggerCardColors.blue.withOpacity(0.15);
    }
  }

  Color get _pillFg {
    switch (_status) {
      case TriggerStatus.triggered:  return Colors.white;
      case TriggerStatus.ok:         return TriggerCardColors.txt2;
      case TriggerStatus.monitoring: return TriggerCardColors.blue;
    }
  }

  Color get _iconBg =>
      _triggered ? TriggerCardColors.orange.withOpacity(0.12) : TriggerCardColors.card;

  Color get _iconColor =>
      _triggered ? TriggerCardColors.orange : TriggerCardColors.txt2;

  // ── Build ──────────────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    final sub = _subLabel;

    return Container(
      decoration: BoxDecoration(
        color: TriggerCardColors.bg,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: _triggered
              ? TriggerCardColors.orange.withOpacity(0.45)
              : TriggerCardColors.border,
        ),
      ),
      child: IntrinsicHeight(
        child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [

          // ── Orange left-border accent (triggered only) ────────────────
          if (_triggered)
            Container(
              width: 4,
              decoration: const BoxDecoration(
                color: TriggerCardColors.orange,
                borderRadius: BorderRadius.only(
                  topLeft:    Radius.circular(16),
                  bottomLeft: Radius.circular(16),
                ),
              ),
            ),

          // ── Card body ─────────────────────────────────────────────────
          Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              child: Row(children: [

                // Large icon box
                Container(
                  width: 50, height: 50,
                  decoration: BoxDecoration(
                    color: _iconBg,
                    borderRadius: BorderRadius.circular(13),
                  ),
                  child: Icon(icon, color: _iconColor, size: 24),
                ),
                const SizedBox(width: 14),

                // Label + sub-label
                Expanded(child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment:  MainAxisAlignment.center,
                  children: [
                    Text(label, style: GoogleFonts.outfit(
                      fontSize: 15, fontWeight: FontWeight.w700,
                      color: TriggerCardColors.txt1,
                    )),
                    if (sub.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Text(sub, style: GoogleFonts.outfit(
                        fontSize: 11, fontWeight: FontWeight.w500,
                        color: TriggerCardColors.txt3,
                      )),
                    ],
                  ],
                )),

                const SizedBox(width: 10),

                // Status pill
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(
                    color: _pillBg,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(_pillLabel, style: GoogleFonts.outfit(
                    fontSize: 10, fontWeight: FontWeight.w800,
                    color: _pillFg, letterSpacing: 0.5,
                  )),
                ),

              ]),
            ),
          ),
        ]),
      ),
    );
  }
}
