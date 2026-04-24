import 'package:flutter/material.dart';
import 'package:figgy_app/theme/app_theme.dart';

class ProgressPillWidget extends StatelessWidget {
  const ProgressPillWidget({super.key});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        _pillStep('Claim Received', true),
        _pillLine(true),
        _pillStep('Activity Checked ✓', true),
        _pillLine(false),
        _pillStep('Payout Ready', false),
      ],
    );
  }

  Widget _pillStep(String label, bool active) {
    final bgColor = active ? AppColors.brandPrimary.withOpacity(0.15) : AppColors.surface;
    final textColor = active ? AppColors.brandPrimary : AppColors.textMuted;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: active ? AppColors.brandPrimary : AppColors.border),
      ),
      child: Text(
        label,
        style: AppTypography.small.copyWith(
          color: textColor,
          fontWeight: FontWeight.w800,
          fontSize: 9,
        ),
      ),
    );
  }

  Widget _pillLine(bool active) {
    return Container(
      width: 20,
      height: 2,
      color: active ? AppColors.brandPrimary : AppColors.border,
      margin: const EdgeInsets.symmetric(horizontal: 4),
    );
  }
}
