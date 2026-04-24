import 'package:flutter/material.dart';
import '../core/theme.dart';
import '../core/simulation_controller.dart';
import '../screens/file_claim_screen.dart';

class SummaryCard extends StatelessWidget {
  final DemoDisruption mode;

  const SummaryCard({super.key, required this.mode});

  @override
  Widget build(BuildContext context) {
    final bool normal = mode == DemoDisruption.none;
    
    // Screenshot values: Rides 300, Protected 198, Total 498
    final String ridesLine = normal ? '₹570' : '₹300';
    final String protectedLine = normal ? '—' : '+₹198';
    final String totalLine = normal ? '₹570' : '₹498';

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.grey.withAlpha(25), width: 1),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.01),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        children: [
          _buildRow('Rides earned today', ridesLine),
          const SizedBox(height: 12),
          Divider(height: 1, thickness: 1, color: Colors.grey.withAlpha(15)),
          const SizedBox(height: 12),
          _buildRow('Protected income', protectedLine, valueColor: normal ? Colors.black54 : Colors.black),
          const SizedBox(height: 12),
          Divider(height: 1, thickness: 1, color: Colors.grey.withAlpha(15)),
          const SizedBox(height: 12),
          _buildRow('Effective total', totalLine, isBold: true, fontSize: 15),
        ],
      ),
    );
  }

  Widget _buildRow(String label, String value, {bool isBold = false, Color? valueColor, double fontSize = 13}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: TextStyle(
            color: isBold ? Colors.black : Colors.black87,
            fontSize: fontSize,
            fontWeight: isBold ? FontWeight.bold : FontWeight.normal,
          ),
        ),
        Text(
          value,
          style: TextStyle(
            color: valueColor ?? Colors.black,
            fontSize: fontSize + 1,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }
}

class ManualFileButton extends StatelessWidget {
  const ManualFileButton({super.key});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        Navigator.push(
          context,
          MaterialPageRoute(builder: (context) => const FileClaimScreen()),
        );
      },
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.grey.withAlpha(25), width: 1),
        ),
        child: Row(
          children: [
            const Icon(Icons.add, size: 16, color: Colors.black45),
            const SizedBox(width: 12),
            const Expanded(
              child: Text(
                'Disruption not auto-detected? File manually',
                style: TextStyle(
                  color: Colors.black,
                  fontSize: 13,
                  fontWeight: FontWeight.bold,
                  letterSpacing: -0.2,
                ),
              ),
            ),
            const Icon(Icons.arrow_forward, size: 16, color: Colors.black54),
          ],
        ),
      ),
    );
  }
}
