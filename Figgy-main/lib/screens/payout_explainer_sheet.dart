// lib/screens/payout_explainer_sheet.dart
// ---------------------------------------------------------------------------
// Figgy GigShield — Payout Explainer Bottom Sheet
// Shows the 3-step parametric payout formula in plain English and Hindi.
// ---------------------------------------------------------------------------

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

// ── Design tokens ─────────────────────────────────────────────────────────
class _S {
  static const bg       = Color(0xFF1A1A2E);
  static const surface  = Color(0xFF22263A);
  static const orange   = Color(0xFFD85A30);
  static const green    = Color(0xFF10B981);
  static const blue     = Color(0xFF3B82F6);
  static const txt1     = Color(0xFFF1F5F9);
  static const txt2     = Color(0xFF94A3B8);
  static const txt3     = Color(0xFF475569);
  static const border   = Color(0xFF2D3148);
}

TextStyle _t(double size, FontWeight w, Color c, {double ls = 0, double h = 1.4}) =>
    GoogleFonts.outfit(fontSize: size, fontWeight: w, color: c, letterSpacing: ls, height: h);

/// Show the bilingual explanation sheet for parametric payouts.
void showPayoutExplainerSheet(
  BuildContext context, {
  required String tier,
  required String capStr,
}) {
  showModalBottomSheet(
    context: context,
    backgroundColor: Colors.transparent,
    isScrollControlled: true,
    builder: (_) => Container(
      decoration: BoxDecoration(
        color: _S.bg,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        border: Border.all(color: _S.border),
      ),
      padding: const EdgeInsets.fromLTRB(24, 20, 24, 36),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Handle
          Center(
            child: Container(
              width: 40, height: 4,
              decoration: BoxDecoration(
                  color: _S.border, borderRadius: BorderRadius.circular(2)),
            ),
          ),
          const SizedBox(height: 20),

          // Title
          Text('How is your payout calculated?',
              style: _t(17, FontWeight.w800, _S.txt1)),
          const SizedBox(height: 4),
          Text('$tier Plan · Cap $capStr',
              style: _t(12, FontWeight.w600, _S.orange)),
          const SizedBox(height: 24),

          // 3-step formula
          _formulaStep(
            step: '1', color: _S.orange,
            en: 'Expected income',
            hi: 'जितना आप कमाते — बिना रुकावट के',
            sub: 'Based on your average hourly rate × disruption hours',
          ),
          _formulaArrow(),
          _formulaStep(
            step: '2', color: _S.blue,
            en: 'What you actually earned',
            hi: 'आपने कितना कमाया — रुकावट के दौरान',
            sub: 'Deliveries completed × your per-delivery rate',
          ),
          _formulaArrow(),
          _formulaStep(
            step: '3', color: _S.green,
            en: 'Your income loss',
            hi: 'नुकसान = फ़र्क',
            sub: 'Expected − Earned = Your loss. Figgy pays up to $capStr.',
          ),
          const SizedBox(height: 20),

          // Plain-language summary
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: _S.surface,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: _S.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('In plain words / सरल भाषा में',
                    style: _t(11, FontWeight.w800, _S.txt3, ls: 0.5)),
                const SizedBox(height: 8),
                Text(
                  'Expected income − What you earned = Your loss.\n'
                  'We pay up to $capStr (your plan limit).',
                  style: _t(13, FontWeight.w500, _S.txt2, h: 1.6),
                ),
                const SizedBox(height: 6),
                Text(
                  'अपेक्षित कमाई − असली कमाई = आपका नुकसान।\n'
                  'Figgy आपके प्लान सीमा तक $capStr तक भुगतान करता है।',
                  style: _t(13, FontWeight.w500, _S.txt2, h: 1.6),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Close button
          SizedBox(
            width: double.infinity,
            child: TextButton(
              onPressed: () => Navigator.pop(context),
              style: TextButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                    side: const BorderSide(color: _S.border)),
              ),
              child: Text('Got it', style: _t(14, FontWeight.w700, _S.txt1)),
            ),
          ),
        ],
      ),
    ),
  );
}

Widget _formulaStep({
  required String step,
  required Color color,
  required String en,
  required String hi,
  required String sub,
}) =>
    Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Container(
        width: 26, height: 26,
        decoration: BoxDecoration(
          color: color.withOpacity(0.12),
          shape: BoxShape.circle,
          border: Border.all(color: color.withOpacity(0.5), width: 1.5),
        ),
        child: Center(
          child: Text(step, style: _t(11, FontWeight.w800, color)),
        ),
      ),
      const SizedBox(width: 12),
      Expanded(child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(en, style: _t(14, FontWeight.w700, _S.txt1)),
          Text(hi, style: _t(12, FontWeight.w500, color)),
          const SizedBox(height: 2),
          Text(sub, style: _t(11, FontWeight.w400, _S.txt3, h: 1.5)),
        ],
      )),
    ]);

Widget _formulaArrow() => Padding(
  padding: const EdgeInsets.only(left: 11, top: 4, bottom: 4),
  child: Row(children: [
    Container(width: 4, height: 20, color: _S.border),
    const SizedBox(width: 20),
    const Icon(Icons.arrow_downward_rounded, color: _S.txt3, size: 14),
  ]),
);
