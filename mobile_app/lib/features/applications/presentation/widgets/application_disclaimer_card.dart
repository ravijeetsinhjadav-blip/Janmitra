import 'package:flutter/material.dart';

/// Informational disclaimer card explaining citizen application tracking boundaries.
/// Clarifies that JanMitra Assist is an intelligence and personal tracking assistant,
/// not an official government portal, and that statuses are citizen-maintained.
class ApplicationDisclaimerCard extends StatelessWidget {
  /// Custom disclaimer text override (e.g. from backend history response)
  final String? customText;

  /// Optional card title
  final String title;

  /// Whether to display in a compact visual style
  final bool isCompact;

  const ApplicationDisclaimerCard({
    super.key,
    this.customText,
    this.title = 'Application Tracking Notice',
    this.isCompact = false,
  });

  static const String defaultDisclaimer =
      'JanMitra Assist is an independent guidance and tracking assistant, not an official government portal. '
      'Formal application submission takes place directly on respective official government department websites. '
      'Status updates and remarks recorded here are maintained by the citizen for personal progress tracking. '
      'JanMitra Assist does not independently verify, approve, or reject official government applications.';

  @override
  Widget build(BuildContext context) {
    final text = customText ?? defaultDisclaimer;

    return Container(
      padding: EdgeInsets.all(isCompact ? 10 : 14),
      decoration: BoxDecoration(
        color: const Color(0xFFFFFBEB), // Amber 50
        borderRadius: BorderRadius.circular(10),
        border:
            Border.all(color: const Color(0xFFFDE68A), width: 1), // Amber 200
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.shield_outlined,
            size: isCompact ? 20 : 24,
            color: const Color(0xFFB45309), // Amber 700
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontSize: isCompact ? 12 : 13,
                    fontWeight: FontWeight.bold,
                    color: const Color(0xFF78350F), // Amber 900
                    letterSpacing: 0.2,
                  ),
                ),
                SizedBox(height: isCompact ? 3 : 5),
                Text(
                  text,
                  style: TextStyle(
                    fontSize: isCompact ? 11 : 12,
                    color: const Color(0xFF92400E), // Amber 800
                    height: 1.35,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
