import 'package:flutter/material.dart';

/// Reusable status badge representing application tracking lifecycle states.
/// Formatted with high-contrast text and background tints.
/// Explicitly identifies 'Approved' and 'Rejected' as citizen-reported records
/// to avoid misrepresenting manual tracking as official government decisions.
class ApplicationStatusBadge extends StatelessWidget {
  /// Raw backend status string (e.g. 'Submitted', 'Under Review', 'Approved')
  final String status;

  /// Whether to display in a compact form (e.g. within tight list headers)
  final bool isCompact;

  /// Whether to append citizen-reported tags. Note: For 'Approved' and 'Rejected',
  /// the citizen-reported qualification is mandatory and cannot be suppressed.
  final bool showCitizenReportedTag;

  const ApplicationStatusBadge({
    super.key,
    required this.status,
    this.isCompact = false,
    this.showCitizenReportedTag = true,
  });

  @override
  Widget build(BuildContext context) {
    final config = _getStatusConfig(status.trim());

    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: isCompact ? 8 : 10,
        vertical: isCompact ? 3 : 5,
      ),
      decoration: BoxDecoration(
        color: config.backgroundColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: config.borderColor, width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            config.icon,
            size: isCompact ? 13 : 15,
            color: config.foregroundColor,
          ),
          const SizedBox(width: 5),
          Flexible(
            child: Text(
              _getDisplayLabel(config.baseLabel),
              style: TextStyle(
                fontSize: isCompact ? 11 : 12,
                fontWeight: FontWeight.w600,
                color: config.foregroundColor,
                letterSpacing: 0.2,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }

  String _getDisplayLabel(String baseLabel) {
    // Approved and Rejected must ALWAYS be qualified to avoid misrepresenting
    // manual tracking as government determinations.
    // showCitizenReportedTag: false must NOT suppress these qualifications.
    if (baseLabel == 'Approved' || baseLabel == 'Rejected') {
      return isCompact
          ? '$baseLabel (Self-Reported)'
          : '$baseLabel (Citizen Reported)';
    }
    if (!showCitizenReportedTag) return baseLabel;
    return baseLabel;
  }

  _StatusStyleConfig _getStatusConfig(String normalizedStatus) {
    switch (normalizedStatus) {
      case 'Submitted':
        return _StatusStyleConfig(
          baseLabel: 'Submitted',
          icon: Icons.send_rounded,
          backgroundColor: const Color(0xFFEFF6FF), // Blue 50
          borderColor: const Color(0xFFBFDBFE), // Blue 200
          foregroundColor: const Color(0xFF1D4ED8), // Blue 700
        );
      case 'Under Review':
        return _StatusStyleConfig(
          baseLabel: 'Under Review',
          icon: Icons.hourglass_top_rounded,
          backgroundColor: const Color(0xFFFEF3C7), // Amber 100
          borderColor: const Color(0xFFFDE68A), // Amber 200
          foregroundColor: const Color(0xFFB45309), // Amber 700
        );
      case 'Pending':
        return _StatusStyleConfig(
          baseLabel: 'Pending',
          icon: Icons.pending_actions_rounded,
          backgroundColor: const Color(0xFFFFF7ED), // Orange 50
          borderColor: const Color(0xFFFED7AA), // Orange 200
          foregroundColor: const Color(0xFFC2410C), // Orange 700
        );
      case 'Document Verification':
        return _StatusStyleConfig(
          baseLabel: 'Document Verification',
          icon: Icons.fact_check_rounded,
          backgroundColor: const Color(0xFFFAF5FF), // Purple 50
          borderColor: const Color(0xFFE9D5FF), // Purple 200
          foregroundColor: const Color(0xFF7E22CE), // Purple 700
        );
      case 'Approved':
        return _StatusStyleConfig(
          baseLabel: 'Approved',
          icon: Icons.check_circle_rounded,
          backgroundColor: const Color(0xFFF0FDF4), // Green 50
          borderColor: const Color(0xFFBBF7D0), // Green 200
          foregroundColor: const Color(0xFF15803D), // Green 700
        );
      case 'Rejected':
        return _StatusStyleConfig(
          baseLabel: 'Rejected',
          icon: Icons.cancel_rounded,
          backgroundColor: const Color(0xFFFEF2F2), // Red 50
          borderColor: const Color(0xFFFECACA), // Red 200
          foregroundColor: const Color(0xFFB91C1C), // Red 700
        );
      case 'Completed':
        return _StatusStyleConfig(
          baseLabel: 'Completed',
          icon: Icons.task_alt_rounded,
          backgroundColor: const Color(0xFFF0FDFA), // Teal 50
          borderColor: const Color(0xFF99F6E4), // Teal 200
          foregroundColor: const Color(0xFF0F766E), // Teal 700
        );
      default:
        return _StatusStyleConfig(
          baseLabel: normalizedStatus.isEmpty ? 'Unknown' : normalizedStatus,
          icon: Icons.info_outline_rounded,
          backgroundColor: const Color(0xFFF1F5F9), // Slate 100
          borderColor: const Color(0xFFCBD5E1), // Slate 300
          foregroundColor: const Color(0xFF475569), // Slate 600
        );
    }
  }
}

class _StatusStyleConfig {
  final String baseLabel;
  final IconData icon;
  final Color backgroundColor;
  final Color borderColor;
  final Color foregroundColor;

  _StatusStyleConfig({
    required this.baseLabel,
    required this.icon,
    required this.backgroundColor,
    required this.borderColor,
    required this.foregroundColor,
  });
}

/// Helper chip for history timeline audit entries
class ApplicationHistoryEventChip extends StatelessWidget {
  final String eventType;
  final String? source;

  const ApplicationHistoryEventChip({
    super.key,
    required this.eventType,
    this.source,
  });

  @override
  Widget build(BuildContext context) {
    final label = _formatEventType(eventType);
    final isUserReported = source == 'USER_REPORTED';

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          decoration: BoxDecoration(
            color: const Color(0xFFF1F5F9),
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: const Color(0xFFCBD5E1)),
          ),
          child: Text(
            label,
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: Color(0xFF334155),
            ),
          ),
        ),
        if (source != null) ...[
          const SizedBox(width: 6),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: isUserReported
                  ? const Color(0xFFEFF6FF)
                  : const Color(0xFFF8FAFC),
              borderRadius: BorderRadius.circular(4),
              border: Border.all(
                color: isUserReported
                    ? const Color(0xFF93C5FD)
                    : const Color(0xFFE2E8F0),
              ),
            ),
            child: Text(
              isUserReported ? 'Citizen Reported' : 'System',
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w500,
                color: isUserReported
                    ? const Color(0xFF1D4ED8)
                    : const Color(0xFF64748B),
              ),
            ),
          ),
        ],
      ],
    );
  }

  String _formatEventType(String type) {
    switch (type) {
      case 'INITIAL_REGISTRATION':
        return 'Initial Registration';
      case 'STATUS_UPDATE':
        return 'Status Update';
      case 'REMARK_ADDED':
        return 'Remark Added';
      case 'APPLICATION_DETAILS_UPDATED':
        return 'Details Updated';
      default:
        return type.replaceAll('_', ' ');
    }
  }
}
