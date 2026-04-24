// lib/screens/earnings_gap_widget.dart
// ---------------------------------------------------------------------------
// Reusable Earnings Gap Card Widget — Figgy GigShield Parametric Screen
//
// Displays a worker-friendly visual summary of today's earnings vs target,
// with a colour-coded progress bar and an annotated gap label.
//
// Usage:
//   EarningsGapWidget(
//     currentEarnings  : 42.0,
//     expectedEarnings : 180.0,
//     tier             : 'Smart',
//     isDisruptionActive: true,    // appends "— rain detected" to gap label
//   )
//
// Colour rules (matches product spec):
//   gap > 30% of expected → orange bar  (falling behind)
//   gap ≤ 30%             → green bar   (on track)
// ---------------------------------------------------------------------------

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

// ── Design tokens (dark theme, matches parametric_screen.dart) ─────────────
class EarningsGapColors {
  static const surface = Color(0xFF1A1D27);
  static const card    = Color(0xFF22263A);
  static const orange  = Color(0xFFD85A30);
  static const green   = Color(0xFF10B981);
  static const border  = Color(0xFF2D3148);
  static const txt1    = Color(0xFFF1F5F9);
  static const txt2    = Color(0xFF94A3B8);
  static const txt3    = Color(0xFF475569);
}

class EarningsGapWidget extends StatelessWidget {
  /// Worker's actual earnings so far today (₹)
  final double currentEarnings;

  /// Worker's expected earnings for a full shift today (₹)
  final double expectedEarnings;

  /// Subscription tier shown as a small pill: "Lite", "Smart", "Elite"
  final String tier;

  /// When true appends "— rain detected" (or similar) to the gap label
  final bool isDisruptionActive;

  /// Optional override for the disruption suffix text
  final String disruptionSuffix;

  const EarningsGapWidget({
    super.key,
    required this.currentEarnings,
    required this.expectedEarnings,
    this.tier                = 'Smart',
    this.isDisruptionActive  = false,
    this.disruptionSuffix    = 'rain detected',
  });

  // ── Derived values ─────────────────────────────────────────────────────
  double get _gap      => (expectedEarnings - currentEarnings).clamp(0, expectedEarnings);
  double get _gapRatio => expectedEarnings > 0 ? _gap / expectedEarnings : 0;
  double get _pct      => expectedEarnings > 0
      ? (currentEarnings / expectedEarnings).clamp(0.0, 1.0) : 0;
  bool   get _isLow    => _gapRatio > 0.30;
  Color  get _barColor => _isLow ? EarningsGapColors.orange : EarningsGapColors.green;

  String get _gapLabel {
    if (!_isLow) return 'On track — great shift!';
    final suffix = isDisruptionActive ? ' — $disruptionSuffix' : '';
    return '₹${_gap.toInt()} gap$suffix';
  }

  String get _pctLabel => '${(_pct * 100).toInt()}% of target';

  // ── Build ──────────────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    final bc = _barColor;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: EarningsGapColors.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: EarningsGapColors.border),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [

        // ── Header row ──────────────────────────────────────────────────
        Row(children: [
          const Icon(
            Icons.account_balance_wallet_rounded,
            color: EarningsGapColors.orange,
            size: 18,
          ),
          const SizedBox(width: 8),
          Text(
            'YOUR EARNINGS TODAY',
            style: GoogleFonts.outfit(
              fontSize: 10, fontWeight: FontWeight.w800,
              color: EarningsGapColors.txt2, letterSpacing: 1.2,
            ),
          ),
          const Spacer(),
          // Tier pill
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: bc.withOpacity(0.12),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Text(
              tier,
              style: GoogleFonts.outfit(
                fontSize: 10, fontWeight: FontWeight.w800, color: bc,
              ),
            ),
          ),
        ]),
        const SizedBox(height: 16),

        // ── Earnings statement ──────────────────────────────────────────
        RichText(text: TextSpan(
          style: GoogleFonts.outfit(
            fontSize: 15, fontWeight: FontWeight.w400,
            color: EarningsGapColors.txt2, height: 1.5,
          ),
          children: [
            const TextSpan(text: "You've earned "),
            TextSpan(
              text: '₹${currentEarnings.toInt()}',
              style: GoogleFonts.outfit(
                fontSize: 24, fontWeight: FontWeight.w900,
                color: EarningsGapColors.txt1,
              ),
            ),
            const TextSpan(text: ' of '),
            TextSpan(
              text: '₹${expectedEarnings.toInt()}',
              style: GoogleFonts.outfit(
                fontSize: 16, fontWeight: FontWeight.w700,
                color: EarningsGapColors.txt2,
              ),
            ),
            const TextSpan(text: ' expected today'),
          ],
        )),
        const SizedBox(height: 16),

        // ── Progress bar ────────────────────────────────────────────────
        Stack(children: [
          // Track
          Container(
            height: 10,
            decoration: BoxDecoration(
              color: EarningsGapColors.card,
              borderRadius: BorderRadius.circular(6),
            ),
          ),
          // Fill
          FractionallySizedBox(
            widthFactor: _pct,
            child: Container(
              height: 10,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [bc.withOpacity(0.55), bc],
                ),
                borderRadius: BorderRadius.circular(6),
                boxShadow: [
                  BoxShadow(color: bc.withOpacity(0.35), blurRadius: 8),
                ],
              ),
            ),
          ),
        ]),
        const SizedBox(height: 10),

        // ── Gap label row ───────────────────────────────────────────────
        Row(children: [
          // Coloured dot
          Container(
            width: 8, height: 8,
            decoration: BoxDecoration(color: bc, shape: BoxShape.circle),
          ),
          const SizedBox(width: 6),
          // Gap label
          Expanded(child: Text(
            _gapLabel,
            style: GoogleFonts.outfit(
              fontSize: 12, fontWeight: FontWeight.w700, color: bc,
            ),
            overflow: TextOverflow.ellipsis,
          )),
          // Percentage
          Text(
            _pctLabel,
            style: GoogleFonts.outfit(
              fontSize: 11, fontWeight: FontWeight.w500,
              color: EarningsGapColors.txt3,
            ),
          ),
        ]),

      ]),
    );
  }
}
