import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../schemes/models/scheme_intelligence_models.dart';
import '../../../schemes/services/scheme_service.dart';
import '../../models/document_models.dart';
import '../../services/document_service.dart';
import '../screens/document_guide_screen.dart';
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
  State<SchemeDocumentChecklistWidget> createState() =>
      _SchemeDocumentChecklistWidgetState();
}

class _SchemeDocumentChecklistWidgetState
    extends State<SchemeDocumentChecklistWidget> {
  final DocumentService _documentService = DocumentService();
  final SchemeService _schemeService = SchemeService();

  SchemeDocumentChecklistModel? _checklist;
  List<SchemeCategoryDocumentModel> _categoryDocs = [];
  List<String> _availableCategories = ['All', 'General', 'OBC', 'SC', 'ST', 'EWS'];
  String _selectedCategory = 'All';

  bool _isLoading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadChecklistAndCategories();
  }

  Future<void> _loadChecklistAndCategories() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final res =
          await _documentService.getSchemeDocumentChecklist(widget.schemeId);
      final cats =
          await _schemeService.getSchemeCategoriesList(widget.schemeId);
      final catDocs = await _schemeService.getSchemeCategoryDocuments(
        widget.schemeId,
        category: _selectedCategory == 'All' ? null : _selectedCategory,
      );

      if (mounted) {
        setState(() {
          _checklist = res;
          if (cats.isNotEmpty) {
            _availableCategories = cats;
          }
          _categoryDocs = catDocs;
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

  Future<void> _onCategoryChanged(String newCategory) async {
    setState(() {
      _selectedCategory = newCategory;
      _isLoading = true;
    });
    try {
      final catDocs = await _schemeService.getSchemeCategoryDocuments(
        widget.schemeId,
        category: newCategory == 'All' ? null : newCategory,
      );
      if (mounted) {
        setState(() {
          _categoryDocs = catDocs;
          _isLoading = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  void _openDocumentGuide(String docType, String docTitle) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => DocumentGuideScreen(
          documentType: docType,
          documentTitle: docTitle,
        ),
      ),
    );
  }

  Future<void> _uploadMissingDocument(String documentType) async {
    final cleanType = documentType.toLowerCase().replaceAll(' ', '_');
    final uploaded = await UploadDocumentDialog.show(
      context,
      initialDocumentType: cleanType,
      onUploadSuccess: () {},
    );

    if (uploaded != null) {
      _loadChecklistAndCategories();
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
              onPressed: _loadChecklistAndCategories,
            ),
          ],
        ),
      );
    }

    final data = _checklist;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Category Filter Selector (Section 7: Category-Wise Document Requirements)
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: const Color(0xFFF1F5F9),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: const Color(0xFFE2E8F0)),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: const [
                  Icon(Icons.tune, size: 16, color: AppTheme.primaryNavy),
                  SizedBox(width: 6),
                  Text(
                    'Filter by Category:',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                      color: AppTheme.primaryNavy,
                    ),
                  ),
                ],
              ),
              DropdownButton<String>(
                value: _availableCategories.contains(_selectedCategory)
                    ? _selectedCategory
                    : _availableCategories.first,
                isDense: true,
                underline: const SizedBox.shrink(),
                style: const TextStyle(
                  color: AppTheme.primaryNavy,
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                ),
                items: _availableCategories.map((c) {
                  return DropdownMenuItem<String>(
                    value: c,
                    child: Text(c == 'All' ? 'All Categories' : c),
                  );
                }).toList(),
                onChanged: (val) {
                  if (val != null) {
                    _onCategoryChanged(val);
                  }
                },
              ),
            ],
          ),
        ),
        const SizedBox(height: 10),

        // Preparation Progress Header
        if (data != null) ...[
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: data.isFullyPrepared
                  ? Colors.green.shade50
                  : Colors.blue.shade50,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: data.isFullyPrepared
                    ? Colors.green.shade200
                    : Colors.blue.shade200,
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
                          data.isFullyPrepared
                              ? Icons.check_circle
                              : Icons.pending_actions,
                          color: data.isFullyPrepared
                              ? AppTheme.accentGreen
                              : AppTheme.primaryBlue,
                          size: 20,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          data.isFullyPrepared
                              ? 'All Required Documents Uploaded'
                              : 'Document Uploads In Progress',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.bold,
                            color: data.isFullyPrepared
                                ? AppTheme.accentGreen
                                : AppTheme.primaryBlue,
                          ),
                        ),
                      ],
                    ),
                    Text(
                      '${data.totalUploaded} / ${data.totalRequired}',
                      style: const TextStyle(
                          fontWeight: FontWeight.bold, fontSize: 13),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                LinearProgressIndicator(
                  value: data.totalRequired > 0
                      ? (data.totalUploaded / data.totalRequired)
                      : 1.0,
                  backgroundColor: Colors.white,
                  color: data.isFullyPrepared
                      ? AppTheme.accentGreen
                      : AppTheme.primaryBlue,
                  minHeight: 5,
                  borderRadius: BorderRadius.circular(3),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
        ],

        // Clickable Guidance Hint
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            color: const Color(0xFFEFF6FF),
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: const Color(0xFFBFDBFE)),
          ),
          child: Row(
            children: const [
              Icon(Icons.touch_app, size: 14, color: AppTheme.primaryBlue),
              SizedBox(width: 6),
              Expanded(
                child: Text(
                  'Tap any document to view step-by-step guidance, issuing authority, and official application links.',
                  style: TextStyle(
                      fontSize: 11,
                      color: Color(0xFF1E40AF),
                      fontWeight: FontWeight.w500),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 10),

        // Category-Specific Documents List if available
        if (_categoryDocs.isNotEmpty) ...[
          ..._categoryDocs.map((cdoc) {
            final isUploaded = data?.checklist.any((item) =>
                    item.documentType.toLowerCase().replaceAll(' ', '_') ==
                        cdoc.documentType.toLowerCase().replaceAll(' ', '_') &&
                    item.isUploaded) ??
                false;

            return InkWell(
              onTap: () => _openDocumentGuide(cdoc.documentType, cdoc.documentName),
              borderRadius: BorderRadius.circular(8),
              child: Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: isUploaded
                        ? Colors.green.shade300
                        : Colors.grey.shade300,
                  ),
                ),
                child: Row(
                  children: [
                    Icon(
                      isUploaded
                          ? Icons.check_circle
                          : Icons.radio_button_unchecked,
                      color: isUploaded ? AppTheme.accentGreen : Colors.grey,
                      size: 20,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Expanded(
                                child: Text(
                                  cdoc.documentName,
                                  style: TextStyle(
                                    fontSize: 13,
                                    fontWeight: FontWeight.bold,
                                    color: isUploaded
                                        ? Colors.black87
                                        : Colors.black87,
                                  ),
                                ),
                              ),
                              if (cdoc.category != 'All')
                                Container(
                                  margin: const EdgeInsets.only(left: 4),
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 6, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFFEDE9FE),
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                  child: Text(
                                    cdoc.category,
                                    style: const TextStyle(
                                      fontSize: 10,
                                      fontWeight: FontWeight.bold,
                                      color: Color(0xFF6D28D9),
                                    ),
                                  ),
                                ),
                            ],
                          ),
                          const SizedBox(height: 2),
                          Text(
                            'Authority: ${cdoc.issuingAuthority}',
                            style: const TextStyle(
                                fontSize: 11, color: Colors.black54),
                          ),
                          if (cdoc.conditionsDescription != null)
                            Text(
                              cdoc.conditionsDescription!,
                              style: const TextStyle(
                                fontSize: 10,
                                color: Colors.black45,
                                fontStyle: FontStyle.italic,
                              ),
                            ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    // Guide Pill & Upload Button
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Row(
                          mainAxisSize: MainAxisSize.min,
                          children: const [
                            Text(
                              'Guide',
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                                color: AppTheme.primaryNavy,
                              ),
                            ),
                            Icon(Icons.chevron_right,
                                size: 16, color: AppTheme.primaryNavy),
                          ],
                        ),
                        if (!isUploaded)
                          TextButton(
                            style: TextButton.styleFrom(
                              padding: EdgeInsets.zero,
                              minimumSize: const Size(50, 24),
                              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                            ),
                            onPressed: () =>
                                _uploadMissingDocument(cdoc.documentType),
                            child: const Text('Upload',
                                style: TextStyle(fontSize: 11)),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            );
          }),
        ] else if (data != null && data.checklist.isNotEmpty) ...[
          // Fallback to standard checklist if no category docs returned
          ...data.checklist.map((item) {
            final cleanType =
                item.documentType.toLowerCase().replaceAll(' ', '_');
            return InkWell(
              onTap: () => _openDocumentGuide(cleanType, item.documentType),
              borderRadius: BorderRadius.circular(8),
              child: Container(
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: item.isUploaded
                        ? Colors.green.shade200
                        : Colors.grey.shade300,
                  ),
                ),
                child: Row(
                  children: [
                    Icon(
                      item.isUploaded
                          ? Icons.check_circle
                          : Icons.radio_button_unchecked,
                      color:
                          item.isUploaded ? AppTheme.accentGreen : Colors.grey,
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
                              color: item.isUploaded
                                  ? Colors.black87
                                  : Colors.black54,
                            ),
                          ),
                          if (item.description != null &&
                              item.description!.isNotEmpty)
                            Text(
                              item.description!,
                              style: const TextStyle(
                                  fontSize: 11, color: Colors.black45),
                            ),
                        ],
                      ),
                    ),
                    const Icon(Icons.chevron_right,
                        size: 18, color: Colors.grey),
                  ],
                ),
              ),
            );
          }),
        ],
      ],
    );
  }
}
