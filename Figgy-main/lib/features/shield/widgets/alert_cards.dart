import 'package:flutter/material.dart';
import '../../../core/navigation/main_tab_scope.dart';
import '../core/theme.dart';
import '../screens/file_claim_screen.dart';
import '../core/notifications.dart';

class DisruptionAlertCard extends StatelessWidget {
  final Color accent;
  final String areaLabel;
  final String body;
  final String duration;

  const DisruptionAlertCard({
    super.key,
    required this.accent,
    required this.areaLabel,
    required this.body,
    required this.duration,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 32, left: 12, right: 16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFFF0F9FF),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFBAE6FD).withOpacity(0.8), width: 1),
        boxShadow: [
          BoxShadow(color: const Color(0xFF0284C7).withOpacity(0.04), blurRadius: 4, offset: const Offset(0, 2)),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Area', style: TextStyle(color: Color(0xFF6B7280), fontSize: 11, fontWeight: FontWeight.w500)),
              Text(areaLabel, style: const TextStyle(color: Color(0xFF1A1A1A), fontSize: 11, fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 12),
          Text(body, style: const TextStyle(color: Color(0xFF0369A1), fontSize: 13, fontWeight: FontWeight.w500, height: 1.4)),
          const SizedBox(height: 16),
          _metaRow('Duration', duration),
          const SizedBox(height: 8),
          _metaRow('Protection', 'Active', labelColor: const Color(0xFF6B7280), valueColor: const Color(0xFF059669)),
        ],
      ),
    );
  }

  Widget _metaRow(String label, String value, {Color? labelColor, Color? valueColor}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: TextStyle(color: labelColor ?? const Color(0xFF6B7280), fontSize: 11, fontWeight: FontWeight.w500)),
        Text(value, style: TextStyle(color: valueColor ?? const Color(0xFF1A1A1A), fontSize: 11, fontWeight: FontWeight.bold)),
      ],
    );
  }
}

class ClaimAlertCard extends StatelessWidget {
  const ClaimAlertCard({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 32, left: 12, right: 16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF7ED),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: const Color(0xFFFDBA74).withOpacity(0.6), width: 1),
        boxShadow: [
          BoxShadow(color: const Color(0xFFEA580C).withOpacity(0.04), blurRadius: 4, offset: const Offset(0, 2)),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Your income protection', style: TextStyle(color: Color(0xFF6B7280), fontSize: 11, fontWeight: FontWeight.w500)),
          const SizedBox(height: 6),
          const Text(
            '₹198 coming to you',
            style: TextStyle(color: Color(0xFF1A1A1A), fontSize: 22, fontWeight: FontWeight.w800, letterSpacing: -0.5),
          ),
          const SizedBox(height: 6),
          const Text(
            '66% of ₹300 income loss · Smart plan cap applied',
            style: TextStyle(color: Color(0xFF6B7280), fontSize: 10, fontWeight: FontWeight.w500, height: 1.4),
          ),
          const SizedBox(height: 20),
          InkWell(
            onTap: () {
              context.goToMainTab(2);
            },
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 12),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFE96A10).withOpacity(0.15), width: 1),
              ),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    'Track my claim',
                    style: TextStyle(color: Color(0xFFE96A10), fontSize: 13, fontWeight: FontWeight.bold),
                  ),
                  SizedBox(width: 8),
                  Icon(Icons.arrow_forward, size: 14, color: Color(0xFFE96A10)),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          InkWell(
            onTap: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (context) => const FileClaimScreen()),
              );
            },
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 12),
              decoration: BoxDecoration(
                color: Colors.transparent,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFE96A10).withOpacity(0.15), width: 1),
              ),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    'Manual claim',
                    style: TextStyle(color: Color(0xFFE96A10), fontSize: 13, fontWeight: FontWeight.bold),
                  ),
                  SizedBox(width: 8),
                  Icon(Icons.arrow_forward, size: 14, color: Color(0xFFE96A10)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
