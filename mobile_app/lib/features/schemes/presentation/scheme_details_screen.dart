import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../../core/theme/app_theme.dart';
import '../models/scheme_models.dart';
import '../services/scheme_service.dart';
import 'eligibility_result_screen.dart';
import '../../documents/presentation/widgets/scheme_document_checklist_widget.dart';



class SchemeDetailsScreen extends StatefulWidget {
  final SchemeModel scheme;

  const SchemeDetailsScreen({
    super.key,
    required this.scheme,
  });

  @override
  State<SchemeDetailsScreen> createState() => _SchemeDetailsScreenState();
}

class _SchemeDetailsScreenState extends State<SchemeDetailsScreen> {
  final SchemeService _schemeService = SchemeService();
  bool _isAssessing = false;

  Future<void> _handleCheckEligibility() async {
    setState(() => _isAssessing = true);
    try {
      final result = await _schemeService.runAssessment(widget.scheme.id);
      if (!mounted) return;
      Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => EligibilityResultScreen(assessment: result),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString().replaceAll('Exception: ', '')),
          backgroundColor: Colors.red.shade700,
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _isAssessing = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final scheme = widget.scheme;

    return Scaffold(
      appBar: AppBar(
        title: Text(scheme.schemeName),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Demo badge banner if demo data
            if (scheme.isDemoData)
              Container(
                margin: const EdgeInsets.only(bottom: 12),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: Colors.amber.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.amber.shade300),
                ),
                child: Row(
                  children: [
                    Icon(Icons.science_outlined, color: Colors.amber.shade900, size: 20),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'DEMO / TEST SCHEME: Curated for MCA major project verification.',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: Colors.amber.shade900,
                        ),
                      ),
                    ),
                  ],
                ),
              ),

            // Title & Department
            Text(
              scheme.schemeName,
              style: const TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
                color: AppTheme.primaryDark,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              scheme.department,
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: Colors.grey.shade700,
              ),
            ),
            const SizedBox(height: 10),

            // Category & State Chips
            Row(
              children: [
                _buildPill(
                  label: scheme.category,
                  color: AppTheme.primaryBlue,
                ),
                const SizedBox(width: 8),
                _buildPill(
                  label: scheme.stateApplicability,
                  color: AppTheme.accentGreen,
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Description
            Card(
              elevation: 0.5,
              child: Padding(
                padding: const EdgeInsets.all(14.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Overview',
                      style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      scheme.description,
                      style: const TextStyle(fontSize: 13, height: 1.5, color: Colors.black87),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),

            // Key Benefits
            if (scheme.benefits.isNotEmpty)
              Card(
                elevation: 0.5,
                child: Padding(
                  padding: const EdgeInsets.all(14.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Row(
                        children: [
                          Icon(Icons.stars, color: Colors.amber, size: 20),
                          SizedBox(width: 6),
                          Text(
                            'Key Benefits',
                            style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      ...scheme.benefits.map((benefit) => Padding(
                            padding: const EdgeInsets.only(bottom: 6),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text('• ', style: TextStyle(fontWeight: FontWeight.bold)),
                                Expanded(
                                  child: Text(
                                    benefit,
                                    style: const TextStyle(fontSize: 13, height: 1.4),
                                  ),
                                ),
                              ],
                            ),
                          )),
                    ],
                  ),
                ),
              ),
            const SizedBox(height: 12),

            // Eligibility Rules
            Card(
              elevation: 0.5,
              child: Padding(
                padding: const EdgeInsets.all(14.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.rule, color: AppTheme.primaryBlue, size: 20),
                        SizedBox(width: 6),
                        Text(
                          'Eligibility Criteria',
                          style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      scheme.eligibilitySummary,
                      style: const TextStyle(fontSize: 13, color: Colors.black87, fontStyle: FontStyle.italic),
                    ),
                    const Divider(height: 20),
                    ...scheme.eligibilityCriteria.map((c) => Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                c.conditionName,
                                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                              ),
                              Text(
                                c.explanation.isNotEmpty ? c.explanation : 'Condition rule on ${c.field}',
                                style: const TextStyle(fontSize: 12, color: Colors.black54),
                              ),
                            ],
                          ),
                        )),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),

            // Required Documents Checklist
            if (scheme.requiredDocuments.isNotEmpty)
              Card(
                elevation: 0.5,
                child: Padding(
                  padding: const EdgeInsets.all(14.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Row(
                        children: [
                          Icon(Icons.description, color: Colors.indigo, size: 20),
                          SizedBox(width: 6),
                          Text(
                            'Required Document Types (Checklist)',
                            style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      SchemeDocumentChecklistWidget(
                        schemeId: scheme.id,
                        schemeName: scheme.schemeName,
                      ),
                    ],
                  ),
                ),
              ),
            const SizedBox(height: 12),


            // Application Process
            if (scheme.applicationProcess.isNotEmpty)
              Card(
                elevation: 0.5,
                child: Padding(
                  padding: const EdgeInsets.all(14.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Row(
                        children: [
                          Icon(Icons.timeline, color: Colors.teal, size: 20),
                          SizedBox(width: 6),
                          Text(
                            'How to Apply (Official Process)',
                            style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      ...scheme.applicationProcess.asMap().entries.map((entry) => Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                CircleAvatar(
                                  radius: 10,
                                  backgroundColor: Colors.teal.shade50,
                                  child: Text(
                                    '${entry.key + 1}',
                                    style: TextStyle(
                                      fontSize: 11,
                                      fontWeight: FontWeight.bold,
                                      color: Colors.teal.shade800,
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Text(
                                    entry.value,
                                    style: const TextStyle(fontSize: 13, height: 1.4),
                                  ),
                                ),
                              ],
                            ),
                          )),
                    ],
                  ),
                ),
              ),
            const SizedBox(height: 12),

            // Official Government Links & Source Verification
            Card(
              elevation: 0.5,
              child: Padding(
                padding: const EdgeInsets.all(14.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.verified, color: AppTheme.primaryBlue, size: 20),
                        SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            'Verified Official Portals & Sources',
                            style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Builder(
                      builder: (context) {
                        Color bgColor = Colors.blueGrey.shade50;
                        Color borderColor = Colors.blueGrey.shade300;
                        Color textColor = Colors.blueGrey.shade800;

                        if (scheme.sourceFreshnessStatus.contains('Verified')) {
                          bgColor = Colors.green.shade50;
                          borderColor = Colors.green.shade300;
                          textColor = Colors.green.shade800;
                        } else if (scheme.sourceFreshnessStatus == 'Review Required') {
                          bgColor = Colors.amber.shade50;
                          borderColor = Colors.amber.shade400;
                          textColor = Colors.amber.shade900;
                        } else if (scheme.sourceFreshnessStatus == 'Stale') {
                          bgColor = Colors.red.shade50;
                          borderColor = Colors.red.shade300;
                          textColor = Colors.red.shade800;
                        }

                        return Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: bgColor,
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: borderColor),
                          ),
                          child: Text(
                            scheme.sourceFreshnessStatus,
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                              color: textColor,
                            ),
                          ),
                        );
                      },
                    ),
                    const SizedBox(height: 10),
                    Text(
                      'Official Application Portal:\n${scheme.officialApplicationUrl}',
                      style: const TextStyle(fontSize: 12, color: AppTheme.primaryBlue, fontWeight: FontWeight.w500),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Official Guidelines Source:\n${scheme.officialSourceUrl}',
                      style: const TextStyle(fontSize: 12, color: Colors.black87),
                    ),
                    if (scheme.eligibilitySourceReference != null) ...[
                      const SizedBox(height: 6),
                      Text(
                        'Eligibility Reference: ${scheme.eligibilitySourceReference}',
                        style: const TextStyle(fontSize: 11, color: Colors.black54),
                      ),
                    ],
                    if (scheme.benefitsSourceReference != null) ...[
                      const SizedBox(height: 4),
                      Text(
                        'Benefits Reference: ${scheme.benefitsSourceReference}',
                        style: const TextStyle(fontSize: 11, color: Colors.black54),
                      ),
                    ],
                    if (scheme.sourceVerificationDetails != null) ...[
                      const SizedBox(height: 6),
                      Text(
                        'Verification Note: ${scheme.sourceVerificationDetails}',
                        style: TextStyle(fontSize: 11, fontStyle: FontStyle.italic, color: Colors.grey.shade700),
                      ),
                    ],
                    if (scheme.sourceLastVerifiedAt != null) ...[
                      const SizedBox(height: 4),
                      Text(
                        'Last Verified: ${scheme.sourceLastVerifiedAt!.split("T").first}',
                        style: const TextStyle(fontSize: 11, color: Colors.black45),
                      ),
                    ],
                    const SizedBox(height: 8),
                    TextButton.icon(
                      icon: const Icon(Icons.copy, size: 16),
                      label: const Text('Copy Portal Link'),
                      onPressed: () {
                        Clipboard.setData(ClipboardData(text: scheme.officialApplicationUrl));
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Portal link copied!')),
                        );
                      },
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),

            // Prominent "Check My Eligibility" Action
            ElevatedButton.icon(
              icon: _isAssessing
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : const Icon(Icons.fact_check),
              label: Text(_isAssessing ? 'Assessing Eligibility...' : 'Check My Eligibility'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.accentGreen,
                padding: const EdgeInsets.symmetric(vertical: 14),
                textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              onPressed: _isAssessing ? null : _handleCheckEligibility,
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  Widget _buildPill({required String label, required Color color}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.bold,
          color: color,
        ),
      ),
    );
  }
}

