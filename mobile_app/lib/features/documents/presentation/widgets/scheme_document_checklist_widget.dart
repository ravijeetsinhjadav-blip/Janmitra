import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import '../../models/document_models.dart';
import '../../services/document_service.dart';
import 'upload_document_dialog.dart';

class SchemeDocumentChecklistWidget extends StatefulWidget {
  final String schemeId;
  final String schemeName;

  const SchemeDocumentChecklistWidget({
    super.key,
    required this.schemeId,
    required this.schemeName,
  });

  @override
  State<SchemeDocumentChecklistWidget> createState() => _SchemeDocumentChecklistWidgetState();
}

class _SchemeDocumentChecklistWidgetState extends State<SchemeDocumentChecklistWidget> {
  final DocumentService _documentService = DocumentService();
  SchemeDocumentChecklistModel? _checklist;
  bool _isLoading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadChecklist();
  }

  Future<void> _loadChecklist() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final res = await _documentService.getSchemeDocumentChecklist(widget.schemeId);
      if (mounted) {
        setState(() {
          _checklist = res;
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

  Future<void> _uploadMissingDocument(String documentType) async {
    final cleanType = documentType.toLowerCase().replaceAll(' ', '_');
    final uploaded = await UploadDocumentDialog.show(
      context,
      initialDocumentType: cleanType,
      onUploadSuccess: () {},
    );

    if (uploaded != null) {
      _loadChecklist();
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 24.0),
        child: Center(child: CircularProgressIndicator()),
      );
    }

    if (_errorMessage != null) {
      return Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.red.shade50,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Row(
          children: [
            const Icon(Icons.error_outline, color: Colors.red, size: 20),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                _errorMessage!,
                style: const TextStyle(color: Colors.red, fontSize: 12),
              ),
            ),
            IconButton(
              icon: const Icon(Icons.refresh, size: 18),
              onPressed: _loadChecklist,
            ),
          ],
        ),
      );
    }

    final data = _checklist;
    if (data == null || data.checklist.isEmpty) {
      return const Padding(
        padding: EdgeInsets.all(12.0),
        child: Text(
          'No specific document checklist required for this scheme.',
          style: TextStyle(color: Colors.black54, fontSize: 13),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Preparation Progress Header
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: data.isFullyPrepared ? Colors.green.shade50 : Colors.blue.shade50,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: data.isFullyPrepared ? Colors.green.shade200 : Colors.blue.shade200,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      Icon(
                        data.isFullyPrepared ? Icons.check_circle : Icons.pending_actions,
                        color: data.isFullyPrepared ? AppTheme.accentGreen : AppTheme.primaryBlue,
                        size: 20,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        data.isFullyPrepared
                            ? 'All Required Documents Prepared'
                            : 'Document Preparation In Progress',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.bold,
                          color: data.isFullyPrepared ? AppTheme.accentGreen : AppTheme.primaryBlue,
                        ),
                      ),
                    ],
                  ),
                  Text(
                    '${data.totalUploaded} / ${data.totalRequired}',
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              LinearProgressIndicator(
                value: data.totalRequired > 0 ? (data.totalUploaded / data.totalRequired) : 1.0,
                backgroundColor: Colors.white,
                color: data.isFullyPrepared ? AppTheme.accentGreen : AppTheme.primaryBlue,
                minHeight: 5,
                borderRadius: BorderRadius.circular(3),
              ),
            ],
          ),
        ),
        const SizedBox(height: 10),

        // Statutory Legal Disclaimer Banner
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
          decoration: BoxDecoration(
            color: Colors.grey.shade100,
            borderRadius: BorderRadius.circular(6),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(Icons.info_outline, size: 16, color: Colors.grey.shade700),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  data.disclaimer,
                  style: TextStyle(fontSize: 11, color: Colors.grey.shade800, height: 1.3),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),

        // Checklist Items
        ...data.checklist.map((item) {
          return Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: item.isUploaded ? Colors.green.shade200 : Colors.grey.shade300,
              ),
            ),
            child: Row(
              children: [
                Icon(
                  item.isUploaded ? Icons.check_circle : Icons.radio_button_unchecked,
                  color: item.isUploaded ? AppTheme.accentGreen : Colors.grey,
                  size: 20,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item.documentType,
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.bold,
                          color: item.isUploaded ? Colors.black87 : Colors.black54,
                        ),
                      ),
                      if (item.description != null && item.description!.isNotEmpty)
                        Text(
                          item.description!,
                          style: const TextStyle(fontSize: 11, color: Colors.black45),
                        ),
                    ],
                  ),
                ),
                if (item.isUploaded)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: Colors.green.shade50,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      item.manualReviewRequired ? 'Review Needed' : 'Uploaded',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                        color: item.manualReviewRequired ? Colors.orange.shade800 : AppTheme.accentGreen,
                      ),
                    ),
                  )
                else
                  TextButton.icon(
                    icon: const Icon(Icons.upload, size: 14),
                    label: const Text('Upload', style: TextStyle(fontSize: 12)),
                    style: TextButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      visualDensity: VisualDensity.compact,
                    ),
                    onPressed: () => _uploadMissingDocument(item.documentType),
                  ),
              ],
            ),
          );
        }),
      ],
    );
  }
}
