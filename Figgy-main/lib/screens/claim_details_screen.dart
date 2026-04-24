import 'dart:convert';
import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:share_plus/share_plus.dart';
import 'package:figgy_app/models/claim_model.dart';
import 'package:figgy_app/config/api_base_url.dart';
import 'package:figgy_app/theme/app_theme.dart';
import 'package:figgy_app/widgets/receipt_row_widget.dart';

// In case it's missing in other files, define the args object here to prevent compilation errors
class ClaimDetailsArgs {
  final String? claimId;
  final ClaimModel? initialClaim;
  const ClaimDetailsArgs({this.claimId, this.initialClaim});
}

class ClaimDetailsScreen extends StatefulWidget {
  final String? claimId;
  final ClaimModel? initialClaim;

  const ClaimDetailsScreen({super.key, this.claimId, this.initialClaim});

  @override
  State<ClaimDetailsScreen> createState() => _ClaimDetailsScreenState();
}

class _ClaimDetailsScreenState extends State<ClaimDetailsScreen> with SingleTickerProviderStateMixin {
  late AnimationController _checkController;
  late Animation<double> _checkAnimation;
  
  bool _isLoading = false;
  String? _error;
  Map<String, dynamic> _apiData = {};

  @override
  void initState() {
    super.initState();
    _checkController = AnimationController(vsync: this, duration: const Duration(milliseconds: 600));
    _checkAnimation = Tween<double>(begin: 0.5, end: 1.0).animate(
      CurvedAnimation(parent: _checkController, curve: Curves.easeOutBack)
    );
    
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() { _isLoading = true; });
    try {
      final id = widget.claimId ?? widget.initialClaim?.claimId;
      if (id == null) throw Exception("No claim ID provided");

      final res = await http.get(Uri.parse('${figgyApiBaseUrl}/api/claim/status/$id')).timeout(const Duration(seconds: 10));
      
      if (res.statusCode == 200) {
        setState(() {
          _apiData = jsonDecode(res.body);
          _isLoading = false;
        });
        _checkController.forward();
      } else {
        throw Exception("API Failed");
      }
    } catch (e) {
      setState(() {
        _error = 'Unable to load claim details. Please try again.';
        _isLoading = false;
      });
    }
  }

  @override
  void dispose() {
    _checkController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        backgroundColor: Color(0xFF0F0F13),
        body: Center(child: CircularProgressIndicator(color: Colors.green)),
      );
    }

    if (_error != null) {
      return Scaffold(
        backgroundColor: const Color(0xFF0F0F13),
        body: SafeArea(
          child: Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.error_outline_rounded, color: Colors.orange, size: 64),
                  const SizedBox(height: 16),
                  Text(_error!, textAlign: TextAlign.center, style: const TextStyle(color: Colors.white, fontSize: 16)),
                  const SizedBox(height: 20),
                  ElevatedButton(
                    onPressed: _loadData,
                    child: const Text('Retry'),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor: const Color(0xFF0F0F13),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              _buildHeroSection(),
              const SizedBox(height: 48),
              _buildBreakdownCard(),
              const SizedBox(height: 24),
              _buildTriggerDetails(),
              const SizedBox(height: 48),
              _buildBottomActions(),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // SECTION 1: PAID HERO
  // ─────────────────────────────────────────────────────────────────────────────
  Widget _buildHeroSection() {
    final amount = _apiData['payout_amount'] ?? 0;
    final upi = _apiData['upi_id'] ?? 'primary account';
    final rrn = _apiData['rrn'] ?? 'N/A';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        ScaleTransition(
          scale: _checkAnimation,
          child: const Icon(Icons.check_circle_rounded, color: Colors.green, size: 80),
        ),
        const SizedBox(height: 16),
        const Text(
          "PAID", 
          style: TextStyle(
            color: Colors.green, 
            fontSize: 48, 
            fontWeight: FontWeight.bold, 
            letterSpacing: 2
          )
        ),
        const SizedBox(height: 8),
        Text("₹$amount credited to $upi", style: const TextStyle(color: Colors.white, fontSize: 16)),
        const SizedBox(height: 8),
        Text("Transaction ref: $rrn", style: const TextStyle(color: Colors.white38, fontSize: 12)),
      ],
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // SECTION 2: BREAKDOWN CARD
  // ─────────────────────────────────────────────────────────────────────────────
  Widget _buildBreakdownCard() {
    final b = _apiData['breakdown'] ?? {};
    final surge = (b['surge_bonus'] as num?) ?? 0;

    return CustomPaint(
      painter: DashedRectPainter(color: Colors.white24, strokeWidth: 1.5, gap: 6),
      child: Container(
        padding: const EdgeInsets.all(24),
        width: double.infinity,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              "How your payout was calculated",
              style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 24),
            ReceiptRowWidget(label: "Hours disrupted", value: "${b['hours_disrupted'] ?? 0} hrs", valueColor: Colors.white),
            const SizedBox(height: 14),
            ReceiptRowWidget(label: "Expected earnings", value: "₹${b['expected_earnings'] ?? 0}", valueColor: Colors.white54),
            const SizedBox(height: 14),
            ReceiptRowWidget(label: "Actual earnings", value: "₹${b['actual_earnings'] ?? 0}", valueColor: Colors.white54),
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 20),
              child: Divider(color: Colors.white12, height: 1),
            ),
            ReceiptRowWidget(label: "Income loss", value: "₹${b['income_loss'] ?? 0}", valueColor: Colors.white),
            const SizedBox(height: 14),
            ReceiptRowWidget(label: "Your plan cap (Smart)", value: "₹${b['plan_cap'] ?? 0}", valueColor: Colors.white54),
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 20),
              child: Divider(color: Colors.white38, thickness: 2, height: 2),
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text("You receive", style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
                Text("₹${b['final_payout'] ?? _apiData['payout_amount'] ?? 0}", 
                  style: const TextStyle(color: Colors.orange, fontSize: 28, fontWeight: FontWeight.w900)),
              ],
            ),
            if (surge > 0) ...[
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text("+ Elite surge bonus (+10%)", style: TextStyle(color: Colors.greenAccent, fontSize: 14)),
                  Text("+₹$surge", style: const TextStyle(color: Colors.greenAccent, fontSize: 14, fontWeight: FontWeight.bold)),
                ],
              ),
            ]
          ],
        ),
      ),
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // SECTION 3: TRIGGER DETAILS
  // ─────────────────────────────────────────────────────────────────────────────
  Widget _buildTriggerDetails() {
    final t = _apiData['trigger_details'] ?? {};
    final cause = t['cause'] ?? 'Disruption';
    final intensity = t['intensity'] ?? 'Detected';
    final location = t['location'] ?? 'Unknown Location';
    final period = t['period'] ?? 'Unknown Time';

    IconData causeIcon = Icons.cloud_outlined;
    if (cause.toLowerCase().contains("rain")) causeIcon = Icons.water_drop_outlined;
    else if (cause.toLowerCase().contains("strike") || cause.toLowerCase().contains("unrest")) causeIcon = Icons.group_off_outlined;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text("What caused this payout", style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold)),
          const SizedBox(height: 20),
          _buildTriggerRow(causeIcon, cause, "$intensity detected"),
          const SizedBox(height: 16),
          _buildTriggerRow(Icons.location_on_outlined, location, "Zone 3"),
          const SizedBox(height: 16),
          _buildTriggerRow(Icons.access_time_rounded, "Time period", period),
        ],
      ),
    );
  }

  Widget _buildTriggerRow(IconData icon, String title, String subtitle) {
    return Row(
      children: [
        Icon(icon, color: Colors.blueAccent, size: 20),
        const SizedBox(width: 16),
        Expanded(child: Text(title, style: const TextStyle(color: Colors.white, fontSize: 14))),
        Text(subtitle, style: const TextStyle(color: Colors.white54, fontSize: 13)),
      ],
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // SECTION 4: BOTTOM ACTIONS
  // ─────────────────────────────────────────────────────────────────────────────
  Widget _buildBottomActions() {
    return Column(
      children: [
        SizedBox(
          width: double.infinity,
          height: 52,
          child: ElevatedButton(
            onPressed: () {
              Navigator.of(context).popUntil((route) => route.isFirst);
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.white,
              foregroundColor: Colors.black,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(26)),
            ),
            child: const Text("Back to Home", style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
          ),
        ),
        const SizedBox(height: 16),
        SizedBox(
          width: double.infinity,
          height: 52,
          child: OutlinedButton.icon(
            onPressed: () {
              final amount = _apiData['payout_amount'] ?? 0;
              final rrn = _apiData['rrn'] ?? '';
              Share.share('Figgy GigShield\nPayout Receipt: ₹$amount credited successfully. (Ref: $rrn)');
            },
            icon: const Icon(Icons.share_rounded, color: Colors.white, size: 20),
            label: const Text("Share Receipt", style: TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w700)),
            style: OutlinedButton.styleFrom(
              side: const BorderSide(color: Colors.white24, width: 1.5),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(26)),
            ),
          ),
        ),
        const SizedBox(height: 32),
        GestureDetector(
          onTap: () {},
          child: const Text("Questions? Contact support →", style: TextStyle(color: Colors.blueAccent, fontSize: 13, fontWeight: FontWeight.w600)),
        ),
      ],
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Custom Dashed Border Painter
// ─────────────────────────────────────────────────────────────────────────────
class DashedRectPainter extends CustomPainter {
  final Color color;
  final double strokeWidth;
  final double gap;

  DashedRectPainter({required this.color, this.strokeWidth = 1.0, this.gap = 5.0});

  @override
  void paint(Canvas canvas, Size size) {
    final Paint paint = Paint()
      ..color = color
      ..strokeWidth = strokeWidth
      ..style = PaintingStyle.stroke;

    final Path path = Path()
      ..addRRect(RRect.fromRectAndRadius(
        Rect.fromLTWH(0, 0, size.width, size.height), 
        const Radius.circular(16)
      ));

    for (PathMetric measurePath in path.computeMetrics()) {
      double distance = 0.0;
      while (distance < measurePath.length) {
        final length = gap * 1.5; // Dash length
        canvas.drawPath(
          measurePath.extractPath(distance, distance + length),
          paint,
        );
        distance += length + gap; // Move distance forward by dash + gap
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
