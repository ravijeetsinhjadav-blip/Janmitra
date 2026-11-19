import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';
import '../../models/application_models.dart';
import 'application_status_badge.dart';

/// Reusable card component displaying an individual citizen-tracked application.
/// Shows scheme identity, citizen-reported status badge, reference number,
/// submission date (with fallback), remarks snippet, and tap interaction.
class ApplicationCard extends StatelessWidget {
  final ApplicationModel application;
  final VoidCallback? onTap;

  const ApplicationCard({
    super.key,
    required this.application,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final hasCategory =
        application.category != null && application.category!.trim().isNotEmpty;
    final hasDepartment = application.department != null &&
        application.department!.trim().isNotEmpty;

    return Card(
      elevation: 1,
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: Colors.grey.shade200),
      ),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Top Row: Category (if available) & Status Badge
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (hasCategory) ...[
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: AppTheme.primaryBlue.withAlpha(20),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              application.category!.trim(),
                              style: const TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                                color: AppTheme.primaryBlue,
                              ),
                            ),
                          ),
                          const SizedBox(height: 6),
                        ],
                        Text(
                          application.schemeName,
                          style: const TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.bold,
                            color: Colors.black87,
                            height: 1.25,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  ApplicationStatusBadge(
                    status: application.status,
                    isCompact: true,
                  ),
                ],
              ),

              const SizedBox(height: 12),
              const Divider(height: 1, thickness: 0.5),
              const SizedBox(height: 10),

              // Reference Number & Submission Date Meta Row
              Row(
                children: [
                  // Reference Number Pill / Info
                  Expanded(
                    child: Row(
                      children: [
                        Icon(
                          Icons.tag_rounded,
                          size: 15,
                          color: application.hasReferenceNumber
                              ? Colors.grey.shade700
                              : Colors.amber.shade800,
                        ),
                        const SizedBox(width: 4),
                        Flexible(
                          child: Text(
                            application.hasReferenceNumber
                                ? application.applicationReferenceNumber!.trim()
                                : 'Ref: Not Issued',
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: application.hasReferenceNumber
                                  ? FontWeight.w600
                                  : FontWeight.normal,
                              color: application.hasReferenceNumber
                                  ? Colors.black87
                                  : Colors.brown.shade700,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  ),

                  // Submission Date
                  Row(
                    children: [
                      Icon(Icons.calendar_today_outlined,
                          size: 13, color: Colors.grey.shade600),
                      const SizedBox(width: 4),
                      Text(
                        application.submissionDate != null
                            ? _formatDate(application.submissionDate!)
                            : 'Date: Not Recorded',
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.grey.shade700,
                        ),
                      ),
                    ],
                  ),
                ],
              ),

              // Optional Department Info
              if (hasDepartment) ...[
                const SizedBox(height: 8),
                Row(
                  children: [
                    Icon(
                      Icons.account_balance_outlined,
                      size: 13,
                      color: Colors.grey.shade600,
                    ),
                    const SizedBox(width: 4),
                    Expanded(
                      child: Text(
                        application.department!.trim(),
                        style: TextStyle(
                          fontSize: 11,
                          color: Colors.grey.shade600,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ],

              const SizedBox(height: 8),

              // Bottom subtle action row with chevron
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  Text(
                    'View Details & History',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: AppTheme.primaryBlue.withAlpha(220),
                    ),
                  ),
                  const SizedBox(width: 2),
                  const Icon(
                    Icons.chevron_right_rounded,
                    size: 16,
                    color: AppTheme.primaryBlue,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _formatDate(DateTime dt) {
    const months = [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec'
    ];
    final day = dt.day.toString().padLeft(2, '0');
    final month = months[dt.month - 1];
    final year = dt.year.toString();
    return '$day $month $year';
  }
}
