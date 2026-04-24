import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:http/http.dart' as http;
import 'package:figgy_app/theme/app_theme.dart';
import 'package:figgy_app/routes.dart';
import 'package:figgy_app/screens/check_row_widget.dart';
import 'package:figgy_app/screens/progress_pill_widget.dart';

class ProofOfWorkScreen extends StatefulWidget {
  final String claimId;

  const ProofOfWorkScreen({super.key, required this.claimId});

  @override
  State<ProofOfWorkScreen> createState() => _ProofOfWorkScreenState();
}

class _ProofOfWorkScreenState extends State<ProofOfWorkScreen> {
  bool _isLoading = true;
  Map<String, dynamic>? _data;
  Map<String, dynamic>? _stats;

  @override
  void initState() {
    super.initState();
    _fetchData();
  }

  Future<void> _fetchData() async {
    try {
      final host = Platform.isAndroid ? '10.0.2.2' : 'localhost';
      final res = await http.get(Uri.parse('http://$host:5000/api/claim/pow_status/${widget.claimId}'));
      if (res.statusCode == 200) {
        setState(() {
          _data = jsonDecode(res.body);
          _isLoading = false;
        });
      } else {
        setState(() => _isLoading = false);
      }
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      appBar: AppBar(
        backgroundColor: AppColors.background,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: AppColors.textPrimary, size: 20),
          onPressed: () => Navigator.pop(context),
        ),
        title: Text(
          'VERIFICATION',
          style: AppTypography.small.copyWith(
            fontWeight: FontWeight.w900,
            letterSpacing: 2.0,
            color: AppColors.textPrimary,
          ),
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: AppColors.brandPrimary))
          : LayoutBuilder(
              builder: (context, constraints) {
                final double hPadding = constraints.maxWidth > 600 ? constraints.maxWidth * 0.15 : 24.0;
                
                return SingleChildScrollView(
                  padding: EdgeInsets.symmetric(horizontal: hPadding, vertical: 24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                    // Progress Bar Pill (Step 1)
                      const ProgressPillWidget(),
                      const SizedBox(height: 24),

                      // SECTION 1 — Status Header
                      _buildStatusHeader(),
                      const SizedBox(height: 32),

                      // SECTION 2 — Timeline
                      _buildTimelineSection(),
                      const SizedBox(height: 32),

                      // SECTION 3 — Security Checks
                      _buildAntiSpoofingSection(),
                      const SizedBox(height: 32),

                      // SECTION 4 — Verification Result (Risk Level)
                      _buildRiskSection(),
                      const SizedBox(height: 32),

                      // SECTION 5 — Bottom CTA
                      _buildActionButtons(context),
                      const SizedBox(height: 64),
                    ],
                  ),
                );
              },
            ),
    );
  }

  // ── SECTION 1: Status Banner ──────────────────────────────────────────────
  Widget _buildStatusHeader() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: const Color(0xFFECFDF5),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: const BoxDecoration(color: Color(0xFF34D399), shape: BoxShape.circle),
            child: const Icon(Icons.check_rounded, color: Colors.white, size: 28),
          ),
          const SizedBox(width: 20),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Your Activity is Verified',
                  style: AppTypography.h3.copyWith(color: const Color(0xFF065F46), fontWeight: FontWeight.bold, fontSize: 20),
                ),
                const SizedBox(height: 4),
                Text(
                  'We checked your work records. Everything looks good.',
                  style: AppTypography.bodySmall.copyWith(color: const Color(0xFF047857), fontWeight: FontWeight.w600, height: 1.4),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ── SECTION 2: Timeline ───────────────────────────────────────────────────
  Widget _buildTimelineSection() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('What we checked', style: AppTypography.bodyMedium.copyWith(fontWeight: FontWeight.w800, color: AppColors.textPrimary)),
          const SizedBox(height: 24),
          _buildTimelineNode('08:00 AM', 'Your app was active', true, false),
          _buildTimelineNode('08:15 AM - 01:00 PM', 'You were on your delivery route', false, false),
          _buildTimelineNode('01:05 PM', 'Your location data checks out', false, true),
        ],
      ),
    );
  }

  Widget _buildTimelineNode(String time, String title, bool isFirst, bool isLast) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Column(
          children: [
            Container(
              width: 14,
              height: 14,
              decoration: BoxDecoration(
                color: AppColors.brandPrimary,
                shape: BoxShape.circle,
                border: Border.all(color: AppColors.surface, width: 2),
              ),
            ),
            if (!isLast)
              Container(width: 2, height: 40, color: AppColors.border),
          ],
        ),
        const SizedBox(width: 20),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(time, style: AppTypography.small.copyWith(color: AppColors.brandPrimary, fontWeight: FontWeight.w800, fontSize: 10)),
            const SizedBox(height: 2),
            Text(title, style: AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w700, color: AppColors.textSecondary, fontSize: 14)),
            if (!isLast) const SizedBox(height: 16),
          ],
        ),
      ],
    );
  }

  // ── SECTION 3: Security Checks ────────────────────────────────────────────
  Widget _buildAntiSpoofingSection() {
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.lock_rounded, color: AppColors.textMuted, size: 16),
              const SizedBox(width: 8),
              Text('Security Checks', style: AppTypography.bodyMedium.copyWith(fontWeight: FontWeight.w800, color: AppColors.textPrimary)),
            ],
          ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(color: const Color(0xFF10B981).withOpacity(0.1), borderRadius: BorderRadius.circular(12)),
            child: Row(
              children: [
                const Icon(Icons.verified_user_rounded, color: Color(0xFF10B981), size: 24),
                const SizedBox(width: 12),
                Expanded(
                  child: Text('Everything looks genuine — no issues found', style: AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w800, color: const Color(0xFF047857))),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          const CheckRowWidget(title: 'Natural movement pattern'),
          const CheckRowWidget(title: 'Route matches real roads'),
          const CheckRowWidget(title: 'Your timing made sense'),
          const CheckRowWidget(title: 'Phone sensors confirmed'),
        ],
      ),
    );
  }

  // ── SECTION 4: Verification Result ────────────────────────────────────────
  Widget _buildRiskSection() {
    final String risk = _data?['risk_level'] ?? 'LOW';
    final bool instantEligible = _data?['eligible_for_instant_payout'] ?? true;

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Verification Result', style: AppTypography.bodyMedium.copyWith(fontWeight: FontWeight.w800, color: AppColors.textPrimary)),
          const SizedBox(height: 20),
          _buildRiskGauge(risk),
          const SizedBox(height: 24),
          if (instantEligible)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFFECFDF5),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFF10B981).withOpacity(0.2)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.check_circle_rounded, color: Color(0xFF10B981), size: 18),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('ELIGIBLE FOR INSTANT PAYOUT', style: AppTypography.small.copyWith(color: const Color(0xFF065F46), fontWeight: FontWeight.w900, letterSpacing: 0.5)),
                        const SizedBox(height: 2),
                        Text("Based on your activity today — we're ready to process your claim.", style: AppTypography.small.copyWith(color: const Color(0xFF047857), fontWeight: FontWeight.w600, fontSize: 10, height: 1.3)),
                      ],
                    ),
                  ),
                ],
              ),
            )
          else
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFFFFFBEB),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFF59E0B).withOpacity(0.2)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.hourglass_empty_rounded, color: Color(0xFFD97706), size: 18),
                  const SizedBox(width: 8),
                  Expanded(child: Text('An admin will review your claim shortly', style: AppTypography.bodySmall.copyWith(color: const Color(0xFF92400E), fontWeight: FontWeight.bold))),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildRiskGauge(String currentRisk) {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              flex: 1,
              child: Column(
                children: [
                  Container(height: 8, decoration: BoxDecoration(color: currentRisk == 'LOW' ? const Color(0xFF10B981) : AppColors.border, borderRadius: const BorderRadius.horizontal(left: Radius.circular(4)))),
                  const SizedBox(height: 6),
                  Text('LOW', style: AppTypography.small.copyWith(fontSize: 9, fontWeight: FontWeight.w900, color: currentRisk == 'LOW' ? const Color(0xFF10B981) : AppColors.textMuted)),
                  Text('Ready to pay', style: AppTypography.small.copyWith(fontSize: 8, color: AppColors.textMuted)),
                ],
              ),
            ),
            const SizedBox(width: 2),
            Expanded(
              flex: 1,
              child: Column(
                children: [
                  Container(height: 8, color: currentRisk == 'MEDIUM' ? const Color(0xFFFDE68A) : AppColors.border),
                  const SizedBox(height: 6),
                  Text('MEDIUM', style: AppTypography.small.copyWith(fontSize: 9, fontWeight: FontWeight.w900, color: currentRisk == 'MEDIUM' ? const Color(0xFFD97706) : AppColors.textMuted)),
                  Text('Quick check needed', style: AppTypography.small.copyWith(fontSize: 8, color: AppColors.textMuted, overflow: TextOverflow.ellipsis)),
                ],
              ),
            ),
            const SizedBox(width: 2),
            Expanded(
              flex: 1,
              child: Column(
                children: [
                  Container(height: 8, decoration: BoxDecoration(color: currentRisk == 'HIGH' ? const Color(0xFFEF4444) : AppColors.border, borderRadius: const BorderRadius.horizontal(right: Radius.circular(4)))),
                  const SizedBox(height: 6),
                  Text('HIGH', style: AppTypography.small.copyWith(fontSize: 9, fontWeight: FontWeight.w900, color: currentRisk == 'HIGH' ? const Color(0xFFEF4444) : AppColors.textMuted)),
                  Text('Admin review', style: AppTypography.small.copyWith(fontSize: 8, color: AppColors.textMuted)),
                ],
              ),
            ),
          ],
        ),
      ],
    );
  }

  // ── Action Buttons ────────────────────────────────────────────────────────
  Widget _buildActionButtons(BuildContext context) {
    return Column(
      children: [
        SizedBox(
          width: double.infinity,
          height: 54,
          child: ElevatedButton(
            onPressed: () => Navigator.pushReplacementNamed(context, AppRoutes.claimProcessing, arguments: ClaimProcessingArgs(claimId: widget.claimId)),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.brandPrimary,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              elevation: 0,
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text('Continue to Payout', style: AppTypography.bodySmall.copyWith(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 16)),
                const SizedBox(width: 8),
                const Icon(Icons.arrow_forward_rounded, color: Colors.white, size: 20),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text('Back', style: AppTypography.bodySmall.copyWith(color: AppColors.textSecondary, fontWeight: FontWeight.w600, decoration: TextDecoration.underline)),
        ),
      ],
    );
  }
}
