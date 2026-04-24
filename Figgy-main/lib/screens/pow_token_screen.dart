import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart';
import 'package:figgy_app/theme/app_theme.dart';
import 'package:figgy_app/routes.dart';

class PowTokenScreen extends StatefulWidget {
  final String workerId;
  final String? claimId;

  const PowTokenScreen({super.key, required this.workerId, this.claimId});

  @override
  State<PowTokenScreen> createState() => _PowTokenScreenState();
}

class _PowTokenScreenState extends State<PowTokenScreen> {
  bool _isLoading = true;
  Map<String, dynamic>? _stats;

  @override
  void initState() {
    super.initState();
    _fetchData();
  }

  Future<void> _fetchData() async {
    try {
      final host = Platform.isAndroid ? '10.0.2.2' : 'localhost';
      final telemetryRes = await http.get(Uri.parse('http://$host:5000/api/worker/telemetry_summary/${widget.workerId}'));
      
      if (telemetryRes.statusCode == 200) {
        setState(() {
          _stats = jsonDecode(telemetryRes.body);
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
          'YOUR CLAIM DATA',
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
                      // Status Banner
                      _buildHeaderBanner(),
                      const SizedBox(height: 32),

                      // MAP SECTION
                      _buildTrackingMap(),
                      const SizedBox(height: 16),

                      // STATS GRID
                      _buildMetricsGrid(),
                      const SizedBox(height: 32),

                      // POW TOKEN SECTION
                      _buildTokenCard(),
                      const SizedBox(height: 32),

                      // BOTTOM CTA
                      _buildActionButtons(context),
                      const SizedBox(height: 64),
                    ],
                  ),
                );
              },
            ),
    );
  }

  Widget _buildHeaderBanner() {
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
            child: const Icon(Icons.bolt_rounded, color: Colors.white, size: 28),
          ),
          const SizedBox(width: 20),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'ELIGIBLE FOR INSTANT PAYOUT',
                  style: AppTypography.h3.copyWith(color: const Color(0xFF065F46), fontWeight: FontWeight.bold, fontSize: 16),
                ),
                const SizedBox(height: 6),
                Text(
                  "Based on your activity today — we're ready to process your claim.",
                  style: AppTypography.bodySmall.copyWith(color: const Color(0xFF047857), fontWeight: FontWeight.w600, height: 1.4, fontSize: 12),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTrackingMap() {
    final List<LatLng> routePoints = [
      const LatLng(13.0418, 80.2341), // Start
      const LatLng(13.0450, 80.2380),
      const LatLng(13.0480, 80.2350),
      const LatLng(13.0520, 80.2420),
      const LatLng(13.0550, 80.2450), // End
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          height: 200,
          width: double.infinity,
          decoration: BoxDecoration(
            color: AppColors.surface,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: AppColors.border),
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(19),
            child: Stack(
              children: [
                FlutterMap(
                  options: MapOptions(
                    initialCenter: const LatLng(13.0480, 80.2400),
                    initialZoom: 14.0,
                    interactionOptions: const InteractionOptions(flags: InteractiveFlag.all),
                  ),
                  children: [
                    TileLayer(
                      urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                      userAgentPackageName: 'com.figgy.app',
                    ),
                    PolylineLayer<Object>(
                      polylines: [
                        Polyline(
                          points: routePoints,
                          color: AppColors.brandPrimary,
                          strokeWidth: 4,
                        ),
                      ],
                    ),
                  ],
                ),
                Positioned(
                  left: 12,
                  top: 12,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(20),
                      boxShadow: AppStyles.softShadow,
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.circle, color: Color(0xFF10B981), size: 10),
                        const SizedBox(width: 6),
                        Text('LIVE TRACKING', style: AppTypography.small.copyWith(fontWeight: FontWeight.w900, color: Colors.black, fontSize: 10)),
                      ],
                    ),
                  ),
                ),
                Positioned(
                  bottom: 12,
                  right: 12,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppColors.surface.withOpacity(0.9),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: AppColors.border),
                    ),
                    child: Text('Your route today — 12.4 km', style: AppTypography.small.copyWith(fontWeight: FontWeight.w800, fontSize: 10)),
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        // Legend
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.circle, color: Color(0xFF10B981), size: 10),
            const SizedBox(width: 6),
            Text('Normal route', style: AppTypography.small.copyWith(color: AppColors.textSecondary, fontSize: 11)),
            const SizedBox(width: 16),
            const Icon(Icons.circle, color: Color(0xFFEF4444), size: 10),
            const SizedBox(width: 6),
            Text('Disruption zone', style: AppTypography.small.copyWith(color: AppColors.textSecondary, fontSize: 11)),
          ],
        ),
      ],
    );
  }

  Widget _buildMetricsGrid() {
    final active = _stats?['active_hours'] ?? 0;
    final normal = _stats?['normal_deliveries'] ?? 0;
    final rain = _stats?['rainday_deliveries'] ?? 0;
    final earnings = _stats?['disruption_earnings'] ?? 0;

    return Row(
      children: [
        Expanded(
          child: Column(
            children: [
              _buildMetricItem('$active', 'hrs online today'),
              const SizedBox(height: 12),
              _buildMetricItem('$rain', 'deliveries during rain', isWarning: true),
            ],
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            children: [
              _buildMetricItem('$normal', 'deliveries (normal day)'),
              const SizedBox(height: 12),
              _buildMetricItem('₹$earnings', 'earned', highlight: true),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildMetricItem(String value, String label, {bool isWarning = false, bool highlight = false}) {
    Color valColor = AppColors.brandPrimary;
    if (isWarning) valColor = const Color(0xFFF59E0B);
    if (highlight) valColor = const Color(0xFF10B981);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 8),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        children: [
          Text(value, style: AppTypography.h1.copyWith(color: valColor, fontWeight: FontWeight.w800, fontSize: 22)),
          const SizedBox(height: 4),
          Text(
            label,
            textAlign: TextAlign.center,
            style: AppTypography.small.copyWith(fontSize: 10, fontWeight: FontWeight.w600, color: AppColors.textSecondary, height: 1.2),
          ),
        ],
      ),
    );
  }

  Widget _buildTokenCard() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Your Claim Reference', style: AppTypography.bodyMedium.copyWith(fontWeight: FontWeight.w800, color: AppColors.textPrimary)),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: AppColors.brandPrimary,
            borderRadius: BorderRadius.circular(20),
            boxShadow: [BoxShadow(color: AppColors.brandPrimary.withOpacity(0.3), blurRadius: 15, offset: const Offset(0, 8))],
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Text('CLAIM ID', style: AppTypography.small.copyWith(color: Colors.white.withOpacity(0.8), fontWeight: FontWeight.w900, letterSpacing: 1.5)),
              const SizedBox(height: 12),
              Text(
                widget.claimId ?? 'PENDING...',
                style: AppTypography.h1.copyWith(color: Colors.white, fontSize: 36, letterSpacing: 2.5, fontWeight: FontWeight.w900),
              ),
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(color: Colors.black.withOpacity(0.15), borderRadius: BorderRadius.circular(20)),
                child: Text('Generated at 9:05 AM · Valid for 24 hours', style: AppTypography.small.copyWith(color: Colors.white.withOpacity(0.9), fontSize: 10, fontWeight: FontWeight.w600)),
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                height: 48,
                child: OutlinedButton(
                  onPressed: () {},
                  style: OutlinedButton.styleFrom(
                    padding: EdgeInsets.zero,
                    side: const BorderSide(color: Colors.white),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.ios_share_rounded, color: Colors.white, size: 16),
                      const SizedBox(width: 8),
                      Text('Share with Support', style: AppTypography.small.copyWith(color: Colors.white, fontWeight: FontWeight.w800, fontStyle: FontStyle.italic)),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        Center(
          child: Text(
            'This ID links all your activity data to your claim. Keep it safe.',
            textAlign: TextAlign.center,
            style: AppTypography.small.copyWith(color: AppColors.textMuted, fontSize: 10, fontStyle: FontStyle.italic),
          ),
        ),
      ],
    );
  }

  bool _isSubmitting = false;

  Future<void> _submitClaim() async {
    setState(() => _isSubmitting = true);
    try {
      String finalClaimId = widget.claimId ?? '';
      
      if (finalClaimId.isEmpty) {
        final host = Platform.isAndroid ? '10.0.2.2' : 'localhost';
        final response = await http.post(
          Uri.parse('http://$host:5000/api/claim/manual'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({"worker_id": widget.workerId}),
        );
        if (response.statusCode == 201 || response.statusCode == 200) {
          final data = jsonDecode(response.body);
          finalClaimId = data['claim_id'];
        } else {
          setState(() => _isSubmitting = false);
          return;
        }
      }
      
      if (mounted) {
        Navigator.pushReplacementNamed(
          context,
          AppRoutes.powVerify,
          arguments: PowVerifyArgs(claimId: finalClaimId),
        );
      }
    } catch (e) {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  Widget _buildActionButtons(BuildContext context) {
    return Column(
      children: [
        SizedBox(
          width: double.infinity,
          height: 54,
          child: ElevatedButton(
            onPressed: _isSubmitting ? null : _submitClaim,
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.brandPrimary,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              elevation: 0,
            ),
            child: _isSubmitting
                ? const SizedBox(width: 24, height: 24, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                : Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text('Continue to Claim Processing', style: AppTypography.bodySmall.copyWith(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 16)),
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
