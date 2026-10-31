import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../documents/presentation/screens/document_vault_screen.dart';
import '../../../assistance/presentation/screens/application_assistance_screen.dart';
import '../../models/advisory_models.dart';
import '../../services/advisory_service.dart';

class AIAdvisoryScreen extends StatefulWidget {
  final String? schemeId;
  final String? assessmentId;
  final AdvisoryAssessmentModel? initialAdvisory;

  const AIAdvisoryScreen({
    super.key,
    this.schemeId,
    this.assessmentId,
    this.initialAdvisory,
  });

  @override
  State<AIAdvisoryScreen> createState() => _AIAdvisoryScreenState();
}

class _AIAdvisoryScreenState extends State<AIAdvisoryScreen> {
  final AdvisoryService _advisoryService = AdvisoryService();

  AdvisoryAssessmentModel? _advisory;
  bool _isLoading = false;
  String? _errorMessage;
  String _selectedLanguage = 'en';

  @override
  void initState() {
    super.initState();
    if (widget.initialAdvisory != null) {
      _advisory = widget.initialAdvisory;
      _selectedLanguage = widget.initialAdvisory!.advisory.language;
    } else {
      _loadAdvisory();
    }
  }

  Future<void> _loadAdvisory({String? language}) async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final lang = language ?? _selectedLanguage;
      AdvisoryAssessmentModel result;

      if (widget.assessmentId != null) {
        if (language != null && language != _advisory?.advisory.language) {
          result = await _advisoryService.regenerateAdvisory(widget.assessmentId!, language: lang);
        } else {
          result = await _advisoryService.getAssessmentAdvisory(widget.assessmentId!);
        }
      } else if (widget.schemeId != null) {
        result = await _advisoryService.assessAndAdvise(widget.schemeId!, language: lang);
      } else if (_advisory != null) {
        result = await _advisoryService.regenerateAdvisory(_advisory!.assessmentId, language: lang);
      } else {
        throw Exception('No scheme or assessment ID provided.');
      }

      if (mounted) {
        setState(() {
          _advisory = result;
          _selectedLanguage = result.advisory.language;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString().replaceFirst('Exception: ', '');
          _isLoading = false;
        });
      }
    }
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'Potentially Eligible':
        return AppTheme.accentGreen;
      case 'Not Eligible Based on Available Information':
        return Colors.red.shade700;
      case 'Insufficient Information':
      default:
        return Colors.orange.shade800;
    }
  }

  Color _getReadinessScoreColor(double score) {
    if (score >= 80) return AppTheme.accentGreen;
    if (score >= 50) return Colors.orange.shade800;
    return Colors.red.shade700;
  }

  Color _getConsistencyColor(String status) {
    switch (status) {
      case 'Consistent':
        return Colors.green;
      case 'Review Required':
        return Colors.orange.shade800;
      case 'Discrepancy Detected':
        return Colors.red.shade700;
      case 'Not Evaluated (No Documents)':
      case 'Not Evaluated':
      default:
        return Colors.blueGrey;
    }
  }

  Color _getFreshnessColor(String freshness) {
    if (freshness == 'Verified Official Source') {
      return Colors.green.shade800;
    }
    return Colors.orange.shade900;
  }

  Widget _buildLanguagePill(String code, String label) {
    final isSelected = _selectedLanguage == code;
    return ChoiceChip(
      label: Text(label),
      selected: isSelected,
      onSelected: _isLoading
          ? null
          : (selected) {
              if (selected && _selectedLanguage != code) {
                _loadAdvisory(language: code);
              }
            },
      selectedColor: AppTheme.primaryBlue,
      labelStyle: TextStyle(
        color: isSelected ? Colors.white : Colors.black87,
        fontSize: 12,
        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
      ),
      padding: const EdgeInsets.symmetric(horizontal: 4),
    );
  }

  Widget _buildScoreBar(String label, double percentage, Color color) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(label, style: const TextStyle(fontSize: 12, color: Colors.black87)),
              Text('${percentage.toStringAsFixed(1)}%', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: color)),
            ],
          ),
          const SizedBox(height: 3),
          LinearProgressIndicator(
            value: (percentage / 100.0).clamp(0.0, 1.0),
            backgroundColor: Colors.grey.shade200,
            color: color,
            minHeight: 6,
            borderRadius: BorderRadius.circular(3),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('AI Advisory & Readiness'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 8.0),
            child: Row(
              children: [
                _buildLanguagePill('en', 'EN'),
                const SizedBox(width: 4),
                _buildLanguagePill('hi', 'हिंदी'),
                const SizedBox(width: 4),
                _buildLanguagePill('gu', 'ગુજરાતી'),
              ],
            ),
          ),
        ],
      ),
      body: _isLoading
          ? const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 16),
                  Text('Synthesizing AI Advisory Guidance & Readiness...', style: TextStyle(fontSize: 13, color: Colors.black54)),
                ],
              ),
            )
          : _errorMessage != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24.0),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.error_outline, size: 48, color: Colors.red),
                        const SizedBox(height: 12),
                        Text(_errorMessage!, textAlign: TextAlign.center, style: const TextStyle(fontSize: 14)),
                        const SizedBox(height: 16),
                        ElevatedButton.icon(
                          onPressed: () => _loadAdvisory(),
                          icon: const Icon(Icons.refresh),
                          label: const Text('Retry'),
                        ),
                      ],
                    ),
                  ),
                )
              : _advisory == null
                  ? const Center(child: Text('No advisory information available.'))
                  : _buildAdvisoryContent(),
    );
  }

  Widget _buildAdvisoryContent() {
    final adv = _advisory!;
    final readiness = adv.readiness;
    final guidance = adv.advisory;
    final statusColor = _getStatusColor(adv.overallStatus);
    final readinessScoreColor = _getReadinessScoreColor(readiness.overallReadinessScore);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Statutory Non-Guarantee Advisory Banner
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
                Icon(Icons.gavel, color: Colors.amber.shade900, size: 20),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    guidance.disclaimer,
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

          // Scheme Overview Card
          Card(
            elevation: 1,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: AppTheme.primaryBlue.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(adv.category, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.primaryBlue)),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: statusColor.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: statusColor.withValues(alpha: 0.3)),
                        ),
                        child: Text(adv.overallStatus, style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: statusColor)),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(
                    adv.schemeName,
                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.black87),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Multi-Dimensional Readiness Dashboard
          Card(
            elevation: 2,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.speed, color: readinessScoreColor, size: 22),
                      const SizedBox(width: 8),
                      const Text(
                        'Application Readiness Score',
                        style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                      ),
                      const Spacer(),
                      Text(
                        '${readiness.overallReadinessScore.toStringAsFixed(1)}%',
                        style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: readinessScoreColor),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    readiness.scoreInterpretation,
                    style: const TextStyle(fontSize: 11, color: Colors.black54, height: 1.3),
                  ),
                  const Divider(height: 20),

                  // 4 Component Scores
                  _buildScoreBar('Criteria Match', readiness.criteriaMatchPercentage, AppTheme.primaryBlue),
                  _buildScoreBar('Required Document Type Coverage', readiness.documentCoveragePercentage, AppTheme.accentGreen),
                  _buildScoreBar('Information Completeness', readiness.informationCompletenessPercentage, Colors.purple),
                  _buildScoreBar('Document Consistency', readiness.consistencyScore, Colors.teal),

                  const SizedBox(height: 10),
                  Row(
                    children: [
                      const Text('Consistency Status: ', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: _getConsistencyColor(readiness.consistencyStatus).withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: _getConsistencyColor(readiness.consistencyStatus)),
                        ),
                        child: Text(
                          readiness.consistencyStatus,
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                            color: _getConsistencyColor(readiness.consistencyStatus),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // AI Advisory Summary Card
          Card(
            elevation: 1,
            color: Colors.blue.shade50.withValues(alpha: 0.5),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(10),
              side: BorderSide(color: AppTheme.primaryBlue.withValues(alpha: 0.2)),
            ),
            child: Padding(
              padding: const EdgeInsets.all(14.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.auto_awesome, color: AppTheme.primaryBlue, size: 20),
                      const SizedBox(width: 8),
                      const Text('AI Advisory Evaluation', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.primaryBlue)),
                      const Spacer(),
                      if (guidance.isMock)
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(color: Colors.grey.shade200, borderRadius: BorderRadius.circular(4)),
                          child: const Text('Dev Simulation', style: TextStyle(fontSize: 10, color: Colors.black54)),
                        ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(guidance.summary, style: const TextStyle(fontSize: 13, height: 1.4, color: Colors.black87)),
                  const SizedBox(height: 8),
                  Text(guidance.assessmentExplanation, style: const TextStyle(fontSize: 12, height: 1.4, color: Colors.black54)),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Document Intelligence Analysis
          Card(
            elevation: 1,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            child: Padding(
              padding: const EdgeInsets.all(14.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.description_outlined, color: AppTheme.primaryDark, size: 20),
                      SizedBox(width: 8),
                      Text('Document Intelligence', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold)),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(guidance.documentAnalysis, style: const TextStyle(fontSize: 12, height: 1.3, color: Colors.black87)),
                  const SizedBox(height: 10),

                  if (readiness.uploadedDocumentTypes.isNotEmpty) ...[
                    const Text('Uploaded Types in Vault:', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.black54)),
                    const SizedBox(height: 4),
                    Wrap(
                      spacing: 6,
                      runSpacing: 4,
                      children: readiness.uploadedDocumentTypes
                          .map((t) => Chip(
                                label: Text(t, style: const TextStyle(fontSize: 11)),
                                visualDensity: VisualDensity.compact,
                                backgroundColor: Colors.green.shade50,
                              ))
                          .toList(),
                    ),
                    const SizedBox(height: 8),
                  ],

                  if (readiness.missingDocumentTypes.isNotEmpty) ...[
                    const Text('Missing Document Types:', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.red)),
                    const SizedBox(height: 4),
                    Wrap(
                      spacing: 6,
                      runSpacing: 4,
                      children: readiness.missingDocumentTypes
                          .map((t) => Chip(
                                label: Text(t, style: TextStyle(fontSize: 11, color: Colors.red.shade900)),
                                visualDensity: VisualDensity.compact,
                                backgroundColor: Colors.red.shade50,
                              ))
                          .toList(),
                    ),
                    const SizedBox(height: 8),
                    OutlinedButton.icon(
                      onPressed: () {
                        Navigator.of(context).push(MaterialPageRoute(builder: (_) => const DocumentVaultScreen()));
                      },
                      icon: const Icon(Icons.upload_file, size: 16),
                      label: const Text('Open Vault & Upload Missing Docs'),
                    ),
                  ],
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Discrepancy Alerts (if any)
          if (guidance.potentialInconsistencies.isNotEmpty) ...[
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.red.shade50,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.red.shade300),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.warning_amber_rounded, color: Colors.red.shade900, size: 20),
                      const SizedBox(width: 8),
                      Text('Potential Inconsistencies Detected', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.red.shade900)),
                    ],
                  ),
                  const SizedBox(height: 6),
                  ...guidance.potentialInconsistencies.map((disc) => Padding(
                        padding: const EdgeInsets.only(top: 4.0),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('• ', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.red)),
                            Expanded(child: Text(disc, style: TextStyle(fontSize: 12, color: Colors.red.shade900))),
                          ],
                        ),
                      )),
                ],
              ),
            ),
            const SizedBox(height: 16),
          ],

          // Next Steps Preparation Checklist
          Card(
            elevation: 1,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            child: Padding(
              padding: const EdgeInsets.all(14.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.checklist, color: AppTheme.primaryBlue, size: 20),
                      SizedBox(width: 8),
                      Text('Actionable Next Steps', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold)),
                    ],
                  ),
                  const SizedBox(height: 8),
                  ...guidance.nextSteps.asMap().entries.map((entry) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4.0),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            CircleAvatar(
                              radius: 10,
                              backgroundColor: AppTheme.primaryBlue.withValues(alpha: 0.1),
                              child: Text('${entry.key + 1}', style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppTheme.primaryBlue)),
                            ),
                            const SizedBox(width: 10),
                            Expanded(child: Text(entry.value, style: const TextStyle(fontSize: 12, height: 1.3, color: Colors.black87))),
                          ],
                        ),
                      )),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Official Government Portal Guidance & Open Portal CTA
          Card(
            elevation: 1,
            color: Colors.green.shade50.withValues(alpha: 0.5),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(10),
              side: BorderSide(color: AppTheme.accentGreen.withValues(alpha: 0.3)),
            ),
            child: Padding(
              padding: const EdgeInsets.all(14.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.public, color: AppTheme.accentGreen, size: 20),
                      SizedBox(width: 8),
                      Text('Official Application Portal', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.accentGreen)),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text(guidance.officialPortalGuidance, style: const TextStyle(fontSize: 12, height: 1.3, color: Colors.black87)),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (context) => ApplicationAssistanceScreen(
                                  schemeId: adv.schemeId,
                                  schemeName: adv.schemeName,
                                ),
                              ),
                            );
                          },
                          icon: const Icon(Icons.assignment_turned_in_outlined, size: 16),
                          label: const Text('Prepare Application with Checklist'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: AppTheme.primaryBlue,
                            foregroundColor: Colors.white,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  ElevatedButton.icon(
                    onPressed: () {
                      Clipboard.setData(ClipboardData(text: adv.officialApplicationUrl));
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text('Copied official URL: ${adv.officialApplicationUrl}'),
                          duration: const Duration(seconds: 3),
                        ),
                      );
                    },
                    icon: const Icon(Icons.open_in_new, size: 16),
                    label: const Text('Copy Official Portal URL'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.accentGreen,
                      foregroundColor: Colors.white,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Official RAG Citations
          if (guidance.citations.isNotEmpty) ...[
            const Text('Verified Scheme Source References', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.black87)),
            const SizedBox(height: 6),
            ...guidance.citations.map((cite) => Card(
                  margin: const EdgeInsets.symmetric(vertical: 4),
                  elevation: 0.5,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  child: Padding(
                    padding: const EdgeInsets.all(10.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(child: Text(cite.title, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold))),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: _getFreshnessColor(cite.sourceFreshnessStatus).withValues(alpha: 0.1),
                                borderRadius: BorderRadius.circular(4),
                                border: Border.all(color: _getFreshnessColor(cite.sourceFreshnessStatus)),
                              ),
                              child: Text(
                                cite.sourceFreshnessStatus,
                                style: TextStyle(
                                  fontSize: 10,
                                  color: _getFreshnessColor(cite.sourceFreshnessStatus),
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                          ],
                        ),
                        if (cite.sourceReference != null) ...[
                          const SizedBox(height: 2),
                          Text(cite.sourceReference!, style: const TextStyle(fontSize: 11, color: Colors.black54)),
                        ],
                        const SizedBox(height: 2),
                        Text(cite.sourceUrl, style: const TextStyle(fontSize: 10, color: AppTheme.primaryBlue)),
                      ],
                    ),
                  ),
                )),
          ],
        ],
      ),
    );
  }
}

