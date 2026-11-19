import 'package:flutter/material.dart';

class AppTheme {
  // Primary brand colors
  static const Color primaryBlue = Color(0xFF1565C0); // Professional civic blue
  static const Color secondaryBlue = Color(0xFF0D47A1); // Deep accent blue
  static const Color primaryDark =
      Color(0xFF0F172A); // Deep navy for typography
  static const Color primaryNavy = Color(0xFF1E3A8A); // Deep navy blue
  static const Color accentGreen = Color(0xFF2E7D32); // Civic green
  static const Color successGreen = Color(0xFF15803D); // Success green
  static const Color accentGold = Color(0xFFD97706); // Accent gold
  static const Color textPrimary = Color(0xFF1E293B); // Dark slate text
  static const Color textSecondary = Color(0xFF64748B); // Muted slate text
  static const Color surfaceBg =
      Color(0xFFF8FAFC); // Clean neutral light background
  static const Color cardBg = Colors.white;

  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: primaryBlue,
        primary: primaryBlue,
        secondary: secondaryBlue,
        surface: surfaceBg,
      ),
      scaffoldBackgroundColor: surfaceBg,
      appBarTheme: const AppBarTheme(
        backgroundColor: primaryBlue,
        foregroundColor: Colors.white,
        elevation: 0,
        centerTitle: true,
        titleTextStyle: TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.bold,
          color: Colors.white,
          letterSpacing: 0.5,
        ),
      ),
      cardTheme: CardThemeData(
        color: cardBg,
        elevation: 2,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        margin: const EdgeInsets.symmetric(vertical: 8),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primaryBlue,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
          textStyle: const TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }
}
