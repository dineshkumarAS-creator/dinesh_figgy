import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppColors {
  // Brand Colors - Reverted to OG Figgy Orange
  static const Color brandPrimary = Color(0xFFFF6A2A); // Figgy Orange
  static const Color brandDeepBlue = Color(0xFF111827); // Premium Fintech Blue
  static const Color brandAccent = Color(0xFFFF7A00);
  static const Color brandGradientStart = Color(0xFF8A0F3C);
  static const Color brandGradientEnd = Color(0xFFFF6A2A);
  
  // Semantic Colors
  static const Color success = Color(0xFF10B981); // Emerald Green
  static const Color dangerSoft = Color(0xFFFEF2F2); // Red background
  static const Color dangerText = Color(0xFFDC2626); // Refined Red text (slightly more premium)
  static const Color bgPremium = Color(0xFFF8F9FB); // Soft Fintech Background
  static const Color warning = Color(0xFFF59E0B);
  static const Color warningLight = Color(0xFFFFFBEB); // Light background for high-trust warnings
  static const Color error = Color(0xFFEF4444);
  static const Color info = Color(0xFF3B82F6);
  static const Color brandOrange = Color(0xFFFF6A2A); // Warning/Safety Orange
  static const Color brandOrangeSoft = Color(0xFFFFF7ED); // Light background for warnings

  // Neutral Text Colors
  static const Color textPrimary = Color(0xFF111827);
  static const Color textSecondary = Color(0xFF6B7280);
  static const Color textMuted = Color(0xFF9CA3AF);
  static const Color textLink = Color(0xFF2563EB);

  // Background Colors
  static const Color background = Color(0xFFF9FAFB);
  static const Color surface = Colors.white;
  static const Color border = Color(0xFFE5E7EB);
}

class AppSpacing {
  static const double micro = 6.0;    
  static const double small = 12.0;   
  static const double standard = 16.0; 
  static const double section = 24.0; 
}

class AppTypography {
  // Scaled down font sizes to prevent the UI from being too big
  static TextStyle get h1 => GoogleFonts.inter(
        fontSize: 22,
        fontWeight: FontWeight.w700,
        color: AppColors.textPrimary,
        letterSpacing: -0.3,
      );

  static TextStyle get h2 => GoogleFonts.inter(
        fontSize: 18,
        fontWeight: FontWeight.w700,
        color: AppColors.textPrimary,
        letterSpacing: -0.2,
      );

  static TextStyle get h3 => GoogleFonts.inter(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        color: AppColors.textPrimary,
      );

  static TextStyle get bodyLarge => GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w500,
        color: AppColors.textPrimary,
      );

  static TextStyle get bodyMedium => GoogleFonts.inter(
        fontSize: 13,
        fontWeight: FontWeight.w400,
        color: AppColors.textSecondary,
      );

  static TextStyle get bodySmall => GoogleFonts.inter(
        fontSize: 12,
        fontWeight: FontWeight.w400,
        color: AppColors.textSecondary,
      );

  static TextStyle get small => GoogleFonts.inter(
        fontSize: 11,
        fontWeight: FontWeight.w600,
        color: AppColors.textMuted,
        letterSpacing: 0.2,
      );
}

class AppStyles {
  static const double gridUnit = 8.0;
  static const double borderRadius = 10.0; 
  static const double cardRadius = 14.0;   
  static const double cardPadding = 16.0;  

  static List<BoxShadow> get softShadow => [
        BoxShadow(
          color: Colors.black.withOpacity(0.04),
          blurRadius: 10,
          offset: const Offset(0, 3),
        ),
      ];

  static List<BoxShadow> get premiumShadow => [
        BoxShadow(
          color: AppColors.brandPrimary.withOpacity(0.12),
          blurRadius: 16,
          offset: const Offset(0, 6),
        ),
      ];
}
