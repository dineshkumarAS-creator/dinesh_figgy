import 'package:flutter/material.dart';
import 'package:figgy_app/theme/app_theme.dart';

class CheckRowWidget extends StatelessWidget {
  final String title;

  const CheckRowWidget({super.key, required this.title});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(title, style: AppTypography.bodySmall.copyWith(fontWeight: FontWeight.w600, color: AppColors.textSecondary)),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(color: const Color(0xFF10B981).withOpacity(0.15), borderRadius: BorderRadius.circular(4)),
            child: Text('VERIFIED', style: AppTypography.small.copyWith(color: const Color(0xFF10B981), fontWeight: FontWeight.w900, fontSize: 9, letterSpacing: 0.5)),
          ),
        ],
      ),
    );
  }
}
