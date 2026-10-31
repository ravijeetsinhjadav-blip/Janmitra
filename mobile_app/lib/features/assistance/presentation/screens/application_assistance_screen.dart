import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../documents/presentation/screens/document_vault_screen.dart';
import '../../models/assistance_models.dart';
import '../../services/assistance_service.dart';

class ApplicationAssistanceScreen extends StatefulWidget {
  final String schemeId;
  final String? schemeName;
  final ApplicationAssistanceModel? initialAssistance;

  const ApplicationAssistanceScreen({
    super.key,
    required this.schemeId,
    this.schemeName,
    this.initialAssistance,
  });

  @override
  State<ApplicationAssistanceScreen> createState() =>
      _ApplicationAssistanceScreenState();
}

class _ApplicationAssistanceScreenState
    extends State<ApplicationAssistanceScreen> {
  final AssistanceService _assistanceService = AssistanceService();

  ApplicationAssistanceModel? _assistance;
  bool _isLoading = false;
  String? _errorMessage;
  String _selectedLanguage = 'en';

  @override
  void initState() {
    super.initState();
    if (widget.initialAssistance != null) {
      _assistance = widget.initialAssistance;
      _selectedLanguage = widget.initialAssistance!.language;
    } else {
      _loadAssistance();
    }
  }

  Future<void> _loadAssistance({String? language}) async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final lang = language ?? _selectedLanguage;
      final result = await _assistanceService.prepareApplication(
        widget.schemeId,
        language: lang,
      );

      if (mounted) {
        setState(() {
          _assistance = result;
          _selectedLanguage = result.language;
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

  Future<void> _toggleChecklistItem(ChecklistItemModel item, bool value) async {
    final previousState = item.isCompleted;
    setState(() {
      item.isCompleted = value;
      if (value) {
        _assistance?.checklistCompletedCount++;
      } else {
        _assistance?.checklistCompletedCount--;
      }
      final total = _assistance?.checklistTotalCount ?? 1;
      final completed = _assistance?.checklistCompletedCount ?? 0;
      _assistance?.checklistCompletionPercentage =
          (completed / (total > 0 ? total : 1)) * 100.0;
    });

    try {
      final update = await _assistanceService.toggleChecklistItem(
        schemeId: widget.schemeId,
        itemId: item.itemId,
        isCompleted: value,
      );
      if (mounted) {
        setState(() {
          item.isCompleted = update.isCompleted;
          _assistance?.checklistCompletedCount = update.completedCount;
          _assistance?.checklistTotalCount = update.totalCount;
          _assistance?.checklistCompletionPercentage =
              update.completionPercentage;
        });
      }
    } catch (e) {
      // Rollback on network error
      if (mounted) {
        setState(() {
          item.isCompleted = previousState;
          if (previousState) {
            _assistance?.checklistCompletedCount++;
          } else {
            _assistance?.checklistCompletedCount--;
          }
          final total = _assistance?.checklistTotalCount ?? 1;
          final completed = _assistance?.checklistCompletedCount ?? 0;
          _assistance?.checklistCompletionPercentage =
              (completed / (total > 0 ? total : 1)) * 100.0;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Failed to update checklist: ${e.toString().replaceFirst('Exception: ', '')}',
            ),
            backgroundColor: Colors.red.shade700,
          ),
        );
      }
    }
  }

  Color _getDocStatusColor(String status) {
    switch (status) {
      case 'Ready for Application Preparation':
      case 'Available':
        return AppTheme.accentGreen;
      case 'Manual Review Required':
        return Colors.amber.shade800;
      case 'Needs Correction':
        return Colors.orange.shade800;
      case 'Processing Failed':
      case 'Missing':
      default:
        return Colors.red.shade700;
    }
  }

  IconData _getDocStatusIcon(String status) {
    switch (status) {
      case 'Ready for Application Preparation':
      case 'Available':
        return Icons.check_circle_outline;
      case 'Manual Review Required':
        return Icons.visibility_outlined;
      case 'Needs Correction':
        return Icons.edit_note_outlined;
      case 'Processing Failed':
        return Icons.error_outline;
      case 'Missing':
      default:
        return Icons.cancel_outlined;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.schemeName ?? 'Application Assistance'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh Guidance',
            onPressed: _isLoading ? null : () => _loadAssistance(),
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text(
              'Preparing personalized application guide and checklist...',
              style: TextStyle(fontSize: 15, fontWeight: FontWeight.w500),
            ),
          ],
        ),
      );
    }

    if (_errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline, size: 56, color: Colors.red.shade600),
              const SizedBox(height: 16),
              Text(
                'Preparation Error',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      color: Colors.red.shade800,
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 8),
              Text(
                _errorMessage!,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 14),
              ),
              const SizedBox(height: 24),
              ElevatedButton.icon(
                onPressed: () => _loadAssistance(),
                icon: const Icon(Icons.refresh),
                label: const Text('Try Again'),
              ),
            ],
          ),
        ),
      );
    }

    if (_assistance == null) {
      return const Center(child: Text('No application assistance data available.'));
    }

    final data = _assistance!;

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Statutory Non-Submission Advisory Banner
          _buildStatutoryBanner(data.disclaimer),
          const SizedBox(height: 12),

          // Scheme Identity & Multilingual Chips
          _buildSchemeHeader(data),
          const SizedBox(height: 12),

          // Readiness & Criteria Overview
          _buildReadinessOverview(data),
          const SizedBox(height: 16),

          // Interactive Preparation Checklist
          _buildInteractiveChecklist(data),
          const SizedBox(height: 16),

          // Document Preparation Status List
          _buildDocumentPreparationSection(data),
          const SizedBox(height: 16),

          // Scheme-Specific Information Guide
          _buildInformationGuideSection(data.guide),
          const SizedBox(height: 16),

          // Official Government Portal Guidance Card
          _buildOfficialPortalCard(data),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _buildStatutoryBanner(String disclaimer) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.amber.shade50,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.amber.shade300),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.shield_outlined, color: Colors.amber.shade900, size: 24),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Preparation Assistant Notice',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: Colors.amber.shade900,
                    fontSize: 13,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  disclaimer,
                  style: TextStyle(
                    fontSize: 12,
                    color: Colors.brown.shade800,
                    height: 1.3,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSchemeHeader(ApplicationAssistanceModel data) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    data.schemeName,
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: AppTheme.primaryDark,
                    ),
                  ),
                ),
                if (data.isDemoData)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 3,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.purple.shade50,
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(color: Colors.purple.shade300),
                    ),
                    child: Text(
                      'DEMO DATA',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                        color: Colors.purple.shade800,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              '${data.department} • ${data.category}',
              style: TextStyle(
                fontSize: 13,
                color: Colors.grey.shade700,
              ),
            ),
            const Divider(height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Language / भाषा / ભાષા:',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Row(
                  children: [
                    _buildLanguageChip('en', 'English'),
                    const SizedBox(width: 6),
                    _buildLanguageChip('hi', 'हिंदी'),
                    const SizedBox(width: 6),
                    _buildLanguageChip('gu', 'ગુજરાતી'),
                  ],
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLanguageChip(String langCode, String label) {
    final isSelected = _selectedLanguage == langCode;
    return ChoiceChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (selected) {
        if (selected && _selectedLanguage != langCode) {
          _loadAssistance(language: langCode);
        }
      },
      selectedColor: AppTheme.primaryBlue,
      labelStyle: TextStyle(
        fontSize: 11,
        color: isSelected ? Colors.white : Colors.black87,
        fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
      ),
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 0),
    );
  }

  Widget _buildReadinessOverview(ApplicationAssistanceModel data) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Readiness Assessment',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: AppTheme.primaryBlue.withAlpha(25),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(
                      color: AppTheme.primaryBlue.withAlpha(100),
                    ),
                  ),
                  child: Text(
                    data.overallStatus,
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: AppTheme.primaryBlue,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: _buildMetricTile(
                    label: 'Criteria Match',
                    value: '${data.criteriaMatchPercentage.toStringAsFixed(1)}%',
                    sublabel: 'Conditions satisfied',
                    color: AppTheme.accentGreen,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _buildMetricTile(
                    label: 'Readiness Score',
                    value: '${data.overallReadinessScore.toStringAsFixed(1)}%',
                    sublabel: data.readinessInterpretation,
                    color: data.overallReadinessScore >= 70
                        ? AppTheme.accentGreen
                        : (data.overallReadinessScore >= 40
                            ? Colors.orange.shade800
                            : Colors.red.shade700),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMetricTile({
    required String label,
    required String value,
    required String sublabel,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withAlpha(15),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withAlpha(60)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: Colors.grey.shade700,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            sublabel,
            style: TextStyle(
              fontSize: 10,
              color: Colors.grey.shade600,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  Widget _buildInteractiveChecklist(ApplicationAssistanceModel data) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: AppTheme.primaryBlue.withAlpha(60)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Row(
                  children: [
                    Icon(Icons.checklist_rounded, color: AppTheme.primaryBlue),
                    SizedBox(width: 8),
                    Text(
                      'Preparation Checklist',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.primaryDark,
                      ),
                    ),
                  ],
                ),
                Text(
                  '${data.checklistCompletedCount} of ${data.checklistTotalCount} done',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: Colors.grey.shade800,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: (data.checklistTotalCount > 0)
                    ? (data.checklistCompletedCount / data.checklistTotalCount)
                    : 0.0,
                backgroundColor: Colors.grey.shade200,
                color: AppTheme.accentGreen,
                minHeight: 8,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Interactive preparation tracker. Ticking items does NOT submit your application.',
              style: TextStyle(
                fontSize: 11,
                fontStyle: FontStyle.italic,
                color: Colors.grey.shade600,
              ),
            ),
            const Divider(height: 20),
            if (data.checklist.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 8),
                child: Text('No checklist items defined for this scheme.'),
              )
            else
              ...data.checklist.map((item) => _buildChecklistTile(item)),
          ],
        ),
      ),
    );
  }

  Widget _buildChecklistTile(ChecklistItemModel item) {
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 4),
      decoration: BoxDecoration(
        color: item.isCompleted ? Colors.green.shade50 : Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: item.isCompleted ? Colors.green.shade200 : Colors.grey.shade300,
        ),
      ),
      child: Material(
        color: Colors.transparent,
        child: CheckboxListTile(
          value: item.isCompleted,
        onChanged: (val) {
          if (val != null) {
            _toggleChecklistItem(item, val);
          }
        },
        activeColor: AppTheme.accentGreen,
        title: Row(
          children: [
            Expanded(
              child: Text(
                item.title,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.bold,
                  decoration:
                      item.isCompleted ? TextDecoration.lineThrough : null,
                  color: item.isCompleted ? Colors.grey.shade600 : Colors.black87,
                ),
              ),
            ),
            if (item.isMandatory)
              Container(
                margin: const EdgeInsets.only(left: 6),
                padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: Colors.red.shade200),
                ),
                child: Text(
                  'Mandatory',
                  style: TextStyle(
                    fontSize: 9,
                    fontWeight: FontWeight.bold,
                    color: Colors.red.shade800,
                  ),
                ),
              ),
          ],
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                item.description,
                style: TextStyle(
                  fontSize: 11,
                  color: item.isCompleted
                      ? Colors.grey.shade500
                      : Colors.grey.shade700,
                  height: 1.25,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'Category: ${item.category.replaceAll('_', ' ').toUpperCase()}',
                style: TextStyle(
                  fontSize: 9,
                  fontWeight: FontWeight.w600,
                  color: Colors.grey.shade500,
                ),
              ),
            ],
          ),
        ),
        controlAffinity: ListTileControlAffinity.leading,
        dense: true,
      ),
    ),
  );
}

  Widget _buildDocumentPreparationSection(ApplicationAssistanceModel data) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Row(
                  children: [
                    Icon(Icons.folder_shared_outlined,
                        color: AppTheme.primaryBlue),
                    SizedBox(width: 8),
                    Text(
                      'Document Preparation Status',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                TextButton.icon(
                  onPressed: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => const DocumentVaultScreen(),
                      ),
                    ).then((_) => _loadAssistance());
                  },
                  icon: const Icon(Icons.file_upload_outlined, size: 16),
                  label: const Text('Open Vault', style: TextStyle(fontSize: 12)),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Verify required certificates are uploaded and processed before starting your application.',
              style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
            ),
            const Divider(height: 16),
            ...data.documentPreparationStatuses.map(
              (doc) => _buildDocumentStatusItem(doc),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDocumentStatusItem(DocumentPreparationStatusModel doc) {
    final color = _getDocStatusColor(doc.status);
    final icon = _getDocStatusIcon(doc.status);

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 4),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withAlpha(12),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withAlpha(50)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        doc.documentName,
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 6,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: color.withAlpha(30),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        doc.status,
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                          color: color,
                        ),
                      ),
                    ),
                  ],
                ),
                if (doc.notes.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(
                    doc.notes,
                    style: TextStyle(
                      fontSize: 11,
                      color: Colors.grey.shade700,
                      height: 1.25,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildInformationGuideSection(ApplicationInfoGuideModel guide) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.menu_book_outlined, color: AppTheme.primaryBlue),
                SizedBox(width: 8),
                Text(
                  'Scheme Information Guide',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              'Detailed filing requirements, specifications, and precautions.',
              style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
            ),
            const SizedBox(height: 12),

            // 1. Common Mistakes to Avoid
            if (guide.commonMistakesToAvoid.isNotEmpty)
              _buildGuideCard(
                title: 'Common Mistakes to Avoid',
                icon: Icons.warning_amber_rounded,
                iconColor: Colors.orange.shade800,
                children: guide.commonMistakesToAvoid
                    .map(
                      (m) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('• ',
                                style: TextStyle(
                                    fontWeight: FontWeight.bold, fontSize: 13)),
                            Expanded(
                              child: Text(
                                m,
                                style: const TextStyle(fontSize: 12, height: 1.3),
                              ),
                            ),
                          ],
                        ),
                      ),
                    )
                    .toList(),
              ),

            const SizedBox(height: 10),

            // 2. Submission Precautions
            if (guide.submissionPrecautions.isNotEmpty)
              _buildGuideCard(
                title: 'Submission Precautions',
                icon: Icons.health_and_safety_outlined,
                iconColor: AppTheme.primaryBlue,
                children: guide.submissionPrecautions
                    .map(
                      (p) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 3),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('✓ ',
                                style: TextStyle(
                                    fontWeight: FontWeight.bold,
                                    color: AppTheme.accentGreen,
                                    fontSize: 12)),
                            Expanded(
                              child: Text(
                                p,
                                style: const TextStyle(fontSize: 12, height: 1.3),
                              ),
                            ),
                          ],
                        ),
                      ),
                    )
                    .toList(),
              ),

            const SizedBox(height: 10),

            // 3. Required Information
            if (guide.applicantInfoRequired.isNotEmpty)
              _buildGuideCard(
                title: 'Required Applicant Information',
                icon: Icons.person_search_outlined,
                iconColor: Colors.teal.shade800,
                children: guide.applicantInfoRequired
                    .map(
                      (info) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Text(
                                  info.fieldName,
                                  style: const TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                const SizedBox(width: 6),
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 4,
                                    vertical: 1,
                                  ),
                                  decoration: BoxDecoration(
                                    color: Colors.grey.shade200,
                                    borderRadius: BorderRadius.circular(3),
                                  ),
                                  child: Text(
                                    info.importance,
                                    style: TextStyle(
                                      fontSize: 9,
                                      fontWeight: FontWeight.w600,
                                      color: Colors.grey.shade700,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                            Text(
                              info.description,
                              style: TextStyle(
                                fontSize: 11,
                                color: Colors.grey.shade700,
                              ),
                            ),
                          ],
                        ),
                      ),
                    )
                    .toList(),
              ),

            const SizedBox(height: 10),

            // 4. Supporting Document Specifications
            if (guide.supportingDocumentsSpecs.isNotEmpty)
              _buildGuideCard(
                title: 'Supporting Document Specifications',
                icon: Icons.fact_check_outlined,
                iconColor: Colors.indigo.shade800,
                children: guide.supportingDocumentsSpecs
                    .map(
                      (spec) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              spec.documentType,
                              style: const TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                            Text(
                              'Format/Validity: ${spec.specifications}',
                              style: TextStyle(
                                fontSize: 11,
                                color: Colors.grey.shade700,
                              ),
                            ),
                            Text(
                              'Authority: ${spec.issuingAuthority}',
                              style: TextStyle(
                                fontSize: 10,
                                fontStyle: FontStyle.italic,
                                color: Colors.grey.shade600,
                              ),
                            ),
                          ],
                        ),
                      ),
                    )
                    .toList(),
              ),

            const SizedBox(height: 10),

            // 5. Important Declarations
            if (guide.importantDeclarations.isNotEmpty)
              _buildGuideCard(
                title: 'Important Declarations Required',
                icon: Icons.gavel_outlined,
                iconColor: Colors.purple.shade800,
                children: guide.importantDeclarations
                    .map(
                      (d) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 3),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('• ',
                                style: TextStyle(
                                    fontWeight: FontWeight.bold, fontSize: 13)),
                            Expanded(
                              child: Text(
                                d,
                                style: const TextStyle(fontSize: 12, height: 1.3),
                              ),
                            ),
                          ],
                        ),
                      ),
                    )
                    .toList(),
              ),

            const SizedBox(height: 10),

            // 6. Step-by-Step Portal Steps
            if (guide.portalSteps.isNotEmpty)
              _buildGuideCard(
                title: 'Official Portal Filing Sequence',
                icon: Icons.alt_route_outlined,
                iconColor: AppTheme.secondaryBlue,
                children: guide.portalSteps
                    .map(
                      (step) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 6),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            CircleAvatar(
                              radius: 10,
                              backgroundColor: AppTheme.primaryBlue,
                              child: Text(
                                '${step.stepNumber}',
                                style: const TextStyle(
                                  fontSize: 10,
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    step.title,
                                    style: const TextStyle(
                                      fontSize: 12,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  Text(
                                    step.instruction,
                                    style: TextStyle(
                                      fontSize: 11,
                                      color: Colors.grey.shade700,
                                      height: 1.25,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    )
                    .toList(),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildGuideCard({
    required String title,
    required IconData icon,
    required Color iconColor,
    required List<Widget> children,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: iconColor.withAlpha(8),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: iconColor.withAlpha(40)),
      ),
      child: Material(
        color: Colors.transparent,
        child: Theme(
          data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
          child: ExpansionTile(
            initiallyExpanded: true,
            tilePadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 0),
            childrenPadding:
                const EdgeInsets.only(left: 14, right: 14, bottom: 12),
            leading: Icon(icon, color: iconColor, size: 22),
            title: Text(
              title,
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.bold,
                color: iconColor,
              ),
            ),
            children: children,
          ),
        ),
      ),
    );
  }

  Widget _buildOfficialPortalCard(ApplicationAssistanceModel data) {
    return Card(
      color: Colors.blue.shade50,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: Colors.blue.shade300),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.account_balance,
                    color: AppTheme.secondaryBlue, size: 24),
                const SizedBox(width: 8),
                const Text(
                  'Official Government Portal',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                    color: AppTheme.secondaryBlue,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            const Text(
              'Applications must be officially lodged through the government portal. JanMitra Assist prepares you for filing but never submits on your behalf.',
              style: TextStyle(fontSize: 12, height: 1.3),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: Colors.blue.shade200),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      data.officialApplicationUrl,
                      style: const TextStyle(
                        fontSize: 12,
                        color: AppTheme.primaryBlue,
                        fontWeight: FontWeight.w500,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.copy, size: 18),
                    tooltip: 'Copy Official URL',
                    onPressed: () {
                      Clipboard.setData(
                        ClipboardData(text: data.officialApplicationUrl),
                      );
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Official portal link copied to clipboard'),
                          duration: Duration(seconds: 2),
                        ),
                      );
                    },
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
