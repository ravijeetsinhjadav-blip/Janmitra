import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../../core/theme/app_theme.dart';
import '../../profile/presentation/screens/profile_setup_screen.dart';
import '../models/scheme_models.dart';

class EligibilityResultScreen extends StatelessWidget {
  final AssessmentResultModel assessment;

  const EligibilityResultScreen({
    super.key,
    required this.assessment,
  });

  Color _getStatusColor() {
    switch (assessment.overallStatus) {
      case 'Potentially Eligible':
        return AppTheme.accentGreen;
      case 'Not Eligible Based on Available Information':
        return Colors.red.shade700;
      case 'Insufficient Information':
      default:
        return Colors.orange.shade800;
    }
  }

  IconData _getStatusIcon() {
    switch (assessment.overallStatus) {
      case 'Potentially Eligible':
        return Icons.check_circle_outline;
      case 'Not Eligible Based on Available Information':
        return Icons.highlight_off;
      case 'Insufficient Information':
      default:
        return Icons.help_outline;
    }
  }

  @override
  Widget build(BuildContext context) {
    final statusColor = _getStatusColor();
    final statusIcon = _getStatusIcon();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Advisory Eligibility Result'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Prominent Advisory Disclaimer Notice
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.amber.shade50,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.amber.shade400),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.info_outline, color: Colors.amber.shade900, size: 22),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      assessment.advisoryDisclaimer,
                      style: TextStyle(
                        fontSize: 12,
                        height: 1.4,
                        color: Colors.amber.shade900,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Scheme Header & Category
            Text(
              assessment.schemeName,
              style: const TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: AppTheme.primaryDark,
              ),
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: AppTheme.primaryBlue.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    assessment.category,
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: AppTheme.primaryBlue,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Main Status Banner Card
            Card(
              elevation: 2,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
                side: BorderSide(color: statusColor.withValues(alpha: 0.4), width: 1.5),
              ),
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  children: [
                    Icon(statusIcon, color: statusColor, size: 54),
                    const SizedBox(height: 10),
                    Text(
                      assessment.overallStatus,
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: statusColor,
                      ),
                    ),
                    const SizedBox(height: 16),
                    // Criteria Match Percentage Gauge (Not approval probability)
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'Criteria Match Percentage:',
                          style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                        ),
                        Text(
                          '${assessment.criteriaMatchPercentage.toInt()}%',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: statusColor,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(6),
                      child: LinearProgressIndicator(
                        value: (assessment.criteriaMatchPercentage / 100).clamp(0.0, 1.0),
                        minHeight: 8,
                        backgroundColor: Colors.grey.shade200,
                        valueColor: AlwaysStoppedAnimation<Color>(statusColor),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Colors.grey.shade100,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        assessment.scoreInterpretation,
                        style: const TextStyle(fontSize: 11, color: Colors.black87, height: 1.3),
                      ),
                    ),
                    const SizedBox(height: 16),
                    // Satisfied / Failed / Unknown counts
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        _buildCountBadge('Satisfied', assessment.satisfiedCount, AppTheme.accentGreen),
                        _buildCountBadge('Not Satisfied', assessment.notSatisfiedCount, Colors.red.shade700),
                        _buildCountBadge('Unknown', assessment.unknownCount, Colors.orange.shade800),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Missing Fields Notice (if any)
            if (assessment.missingFields.isNotEmpty) ...[
              Card(
                color: Colors.orange.shade50,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10),
                  side: BorderSide(color: Colors.orange.shade300),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(14.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(Icons.edit_note, color: Colors.orange.shade900),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              'Missing Profile Information (${assessment.missingFields.length})',
                              style: TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.bold,
                                color: Colors.orange.shade900,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Provide these profile fields for an accurate assessment: ${assessment.missingFields.join(", ")}.',
                        style: const TextStyle(fontSize: 12, color: Colors.black87),
                      ),
                      const SizedBox(height: 10),
                      OutlinedButton.icon(
                        icon: const Icon(Icons.person, size: 16),
                        label: const Text('Update Profile Now'),
                        onPressed: () {
                          Navigator.of(context).push(
                            MaterialPageRoute(builder: (_) => const ProfileSetupScreen()),
                          );
                        },
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],

            // Criteria Breakdown List
            const Text(
              'Detailed Condition Analysis',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            ...assessment.conditionsBreakdown.map((cond) => _buildConditionCard(cond)),

            const SizedBox(height: 16),

            // Official Application Access
            Card(
              elevation: 1,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
                side: BorderSide(color: AppTheme.primaryBlue.withValues(alpha: 0.3)),
              ),
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.open_in_new, color: AppTheme.primaryBlue),
                        SizedBox(width: 8),
                        Text(
                          'Official Government Portal',
                          style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Applications must be formally filed through the verified nodal portal below:',
                      style: TextStyle(fontSize: 12, color: Colors.black54),
                    ),
                    const SizedBox(height: 10),
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: Colors.grey.shade100,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: SelectableText(
                        assessment.officialApplicationUrl,
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppTheme.primaryBlue,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    ElevatedButton.icon(
                      icon: const Icon(Icons.copy, size: 16),
                      label: const Text('Copy Official Portal URL'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.primaryBlue,
                        foregroundColor: Colors.white,
                      ),
                      onPressed: () {
                        Clipboard.setData(ClipboardData(text: assessment.officialApplicationUrl));
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Official URL copied to clipboard!')),
                        );
                      },
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),

            ElevatedButton(
              onPressed: () => Navigator.of(context).pop(),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
              child: const Text('Back to Schemes'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCountBadge(String label, int count, Color color) {
    return Column(
      children: [
        Text(
          count.toString(),
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        Text(
          label,
          style: TextStyle(fontSize: 11, color: Colors.grey.shade700),
        ),
      ],
    );
  }

  Widget _buildConditionCard(ConditionEvaluationModel cond) {
    Color cardColor;
    IconData icon;
    String statusLabel;

    switch (cond.status) {
      case 'satisfied':
        cardColor = AppTheme.accentGreen;
        icon = Icons.check_circle;
        statusLabel = 'Satisfied';
        break;
      case 'not_satisfied':
        cardColor = Colors.red.shade700;
        icon = Icons.cancel;
        statusLabel = 'Not Satisfied';
        break;
      case 'unknown':
      default:
        cardColor = Colors.orange.shade800;
        icon = Icons.help_outline;
        statusLabel = 'Incomplete Info';
        break;
    }

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      elevation: 0.5,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: BorderSide(color: cardColor.withValues(alpha: 0.3)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: cardColor, size: 20),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    cond.conditionName,
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      color: Colors.black87,
                    ),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: cardColor.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    statusLabel,
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      color: cardColor,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              cond.explanation,
              style: const TextStyle(fontSize: 12, color: Colors.black87),
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                Text(
                  'Expected: ${cond.expectedValue}',
                  style: const TextStyle(fontSize: 11, color: Colors.black54),
                ),
                const SizedBox(width: 12),
                Text(
                  'Your profile: ${cond.actualValue ?? "Not Provided"}',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: cond.actualValue != null ? Colors.black87 : Colors.orange.shade800,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

