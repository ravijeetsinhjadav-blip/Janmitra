import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import '../../models/document_models.dart';
import '../../services/document_service.dart';
import '../widgets/upload_document_dialog.dart';
import 'document_detail_screen.dart';

class DocumentVaultScreen extends StatefulWidget {
  const DocumentVaultScreen({super.key});

  @override
  State<DocumentVaultScreen> createState() => _DocumentVaultScreenState();
}

class _DocumentVaultScreenState extends State<DocumentVaultScreen> {
  final DocumentService _documentService = DocumentService();

  List<DocumentMetadataModel> _documents = [];
  bool _isLoading = true;
  String? _errorMessage;
  String _selectedFilter = 'all';

  final List<Map<String, String>> _filterOptions = [
    {'value': 'all', 'label': 'All Documents'},
    {'value': 'income_certificate', 'label': 'Income'},
    {'value': 'caste_certificate', 'label': 'Caste'},
    {'value': 'domicile_certificate', 'label': 'Domicile'},
    {'value': 'ration_card', 'label': 'Ration Card'},
    {'value': 'aadhaar_card', 'label': 'Aadhaar'},
    {'value': 'land_record', 'label': 'Land Record'},
  ];

  @override
  void initState() {
    super.initState();
    _loadDocuments();
  }

  Future<void> _loadDocuments() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final docs = await _documentService.getDocuments(
        documentType: _selectedFilter == 'all' ? null : _selectedFilter,
      );
      if (mounted) {
        setState(() {
          _documents = docs;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _errorMessage = e.toString().replaceFirst('Exception: ', '');
        });
      }
    }
  }

  Future<void> _openUploadDialog() async {
    final uploaded = await UploadDocumentDialog.show(
      context,
      initialDocumentType: _selectedFilter != 'all' ? _selectedFilter : null,
      onUploadSuccess: () {},
    );

    if (uploaded != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Uploaded ${uploaded.originalFilename} successfully.')),
      );
      _loadDocuments();
    }
  }

  @override
  Widget build(BuildContext context) {
    final ocrCompletedCount = _documents.where((d) => d.ocrStatus == DocumentProcessingStatus.ocrCompleted && !d.manualReviewRequired).length;
    final reviewCount = _documents.where((d) => d.manualReviewRequired || d.ocrStatus == DocumentProcessingStatus.manualReviewRequired).length;


    return Scaffold(
      appBar: AppBar(
        title: const Text('Citizen Document Vault'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh Vault',
            onPressed: _loadDocuments,
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: AppTheme.primaryBlue,
        foregroundColor: Colors.white,
        icon: const Icon(Icons.add),
        label: const Text('Upload Document'),
        onPressed: _openUploadDialog,
      ),
      body: RefreshIndicator(
        onRefresh: _loadDocuments,
        child: Column(
          children: [
            // Summary Header Card
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              color: Colors.white,
              child: Row(
                children: [
                  Expanded(
                    child: _buildSummaryItem(
                      label: 'Total Files',
                      value: '${_documents.length}',
                      color: AppTheme.primaryBlue,
                    ),
                  ),
                  Container(height: 36, width: 1, color: Colors.grey.shade300),
                  Expanded(
                    child: _buildSummaryItem(
                      label: 'OCR Completed',
                      value: '$ocrCompletedCount',
                      color: AppTheme.accentGreen,
                    ),
                  ),

                  Container(height: 36, width: 1, color: Colors.grey.shade300),
                  Expanded(
                    child: _buildSummaryItem(
                      label: 'Review Needed',
                      value: '$reviewCount',
                      color: Colors.orange.shade800,
                    ),
                  ),
                ],
              ),
            ),
            const Divider(height: 1),

            // Horizontal Filter Chips
            Container(
              height: 48,
              padding: const EdgeInsets.symmetric(vertical: 6),
              color: Colors.grey.shade50,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                itemCount: _filterOptions.length,
                separatorBuilder: (_, __) => const SizedBox(width: 8),
                itemBuilder: (context, idx) {
                  final opt = _filterOptions[idx];
                  final isSelected = _selectedFilter == opt['value'];
                  return ChoiceChip(
                    label: Text(opt['label']!),
                    selected: isSelected,
                    selectedColor: AppTheme.primaryBlue.withValues(alpha: 0.15),
                    labelStyle: TextStyle(
                      fontSize: 12,
                      fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                      color: isSelected ? AppTheme.primaryBlue : Colors.black87,
                    ),
                    onSelected: (selected) {
                      if (selected) {
                        setState(() => _selectedFilter = opt['value']!);
                        _loadDocuments();
                      }
                    },
                  );
                },
              ),
            ),
            const Divider(height: 1),

            // Body content
            Expanded(
              child: _buildBodyContent(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSummaryItem({required String label, required String value, required Color color}) {
    return Column(
      children: [
        Text(
          value,
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: color),
        ),
        const SizedBox(height: 2),
        Text(
          label,
          style: const TextStyle(fontSize: 11, color: Colors.black54),
        ),
      ],
    );
  }

  Widget _buildBodyContent() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.error_outline, size: 48, color: Colors.red.shade400),
              const SizedBox(height: 12),
              Text(
                _errorMessage!,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.red),
              ),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                icon: const Icon(Icons.refresh),
                label: const Text('Try Again'),
                onPressed: _loadDocuments,
              ),
            ],
          ),
        ),
      );
    }

    if (_documents.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: AppTheme.primaryBlue.withValues(alpha: 0.08),
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.folder_open, size: 56, color: AppTheme.primaryBlue),
              ),
              const SizedBox(height: 16),
              const Text(
                'Your Vault is Empty',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.black87),
              ),
              const SizedBox(height: 8),
              const Text(
                'Upload your certificates, identity cards, and welfare documents to prepare for scheme eligibility checks.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 13, color: Colors.black54, height: 1.4),
              ),
              const SizedBox(height: 20),
              ElevatedButton.icon(
                icon: const Icon(Icons.upload_file),
                label: const Text('Upload Document Now'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primaryBlue,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                ),
                onPressed: _openUploadDialog,
              ),
            ],
          ),
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _documents.length,
      itemBuilder: (context, index) {
        final doc = _documents[index];
        final confPercent = ((doc.ocrConfidence ?? 0.0) * 100).toInt();

        return Card(
          elevation: 1,
          margin: const EdgeInsets.only(bottom: 12),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          child: InkWell(
            borderRadius: BorderRadius.circular(10),
            onTap: () async {
              final refreshed = await Navigator.of(context).push<bool>(
                MaterialPageRoute(
                  builder: (_) => DocumentDetailScreen(document: doc),
                ),
              );
              if (refreshed == true) {
                _loadDocuments();
              }
            },
            child: Padding(
              padding: const EdgeInsets.all(14.0),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: AppTheme.primaryBlue.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Icon(doc.iconData, color: AppTheme.primaryBlue, size: 24),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          doc.displayType,
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                        ),
                        const SizedBox(height: 3),
                        Text(
                          '${doc.originalFilename} • ${doc.formattedFileSize}',
                          style: const TextStyle(fontSize: 12, color: Colors.black54),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 6),
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: doc.statusColor.withValues(alpha: 0.1),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                doc.statusBadgeText,
                                style: TextStyle(
                                  fontSize: 10,
                                  fontWeight: FontWeight.bold,
                                  color: doc.statusColor,
                                ),
                              ),
                            ),
                            if (doc.ocrConfidence != null) ...[
                              const SizedBox(width: 8),
                              Text(
                                '$confPercent% OCR',
                                style: TextStyle(fontSize: 10, color: Colors.grey.shade600),
                              ),
                            ],
                            const Spacer(),
                            Text(
                              doc.formattedDate,
                              style: const TextStyle(fontSize: 11, color: Colors.black38),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  const Icon(Icons.chevron_right, color: Colors.black26),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

