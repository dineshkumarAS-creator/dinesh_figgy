import 'package:flutter/material.dart';

class AppColors {
  static const Color primary = Color(0xFFF2994A); // Figgy Orange
  static const Color secondary = Color(0xFF2D9CDB); // Blue for alerts
  static const Color background = Color(0xFFFFFFFF);
  static const Color cardBg = Color(0xFFFBFBFB);
  static const Color textPrimary = Color(0xFF1A1A1A);
  static const Color textLight = Color(0xFF757575);
  static const Color success = Color(0xFF27AE60);
  static const Color danger = Color(0xFFEB5757);
  static const Color highlightBg = Color(0xFFFEF5ED); // Light orange for claim cards
  static const Color infoBg = Color(0xFFEFF6FF); // Light blue for rain cards
  static const Color surface = Color(0xFFFFFFFF);
}

class AppTheme {
  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: AppColors.primary,
      ),
      // cardTheme: CardTheme(
      //   elevation: 0,
      //   shape: RoundedRectangleBorder(
      //     borderRadius: BorderRadius.circular(16),
      //     side: BorderSide(color: Colors.grey.shade100),
      //   ),
      //   color: AppColors.cardBg,
      // ),
    );
  }
}
