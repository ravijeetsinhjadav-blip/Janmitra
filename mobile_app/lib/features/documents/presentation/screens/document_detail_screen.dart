import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../../core/theme/app_theme.dart';
import '../../models/document_models.dart';
import '../../services/document_service.dart';

class DocumentDetailScreen extends StatefulWidget {
  final DocumentMetadataModel document;

  const DocumentDetailScreen({super.key, required this.document});

  @override
  State<DocumentDetailScreen> createState() => _DocumentDetailScreenState();
}

class _DocumentDetailScreenState extends State<DocumentDetailScreen> {
  final DocumentService _documentService = DocumentService();
  late DocumentMetadataModel _doc;
  bool _isRetrying = false;
  bool _isDeleting = false;

  @override
  void initState() {
    super.initState();
    _doc = widget.document;
  }

  Future<void> _handleRetryOcr() async {
    setState(() => _isRetrying = true);
    try {
      final updated = await _documentService.retryOcr(_doc.id);
      if (!mounted) return;
      setState(() {
        _doc = updated;
        _isRetrying = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('OCR re-processing completed.')),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => _isRetrying = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to retry OCR: $e'), backgroundColor: Colors.red),
      );
    }
  }

  Future<void> _handleDelete() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Document'),
        content: Text(
          'Are you sure you want to permanently delete "${_doc.originalFilename}" from your vault?\n\nThis action cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    setState(() => _isDeleting = true);
    try {
      await _documentService.deleteDocument(_doc.id);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Document deleted successfully.')),
      );
      Navigator.of(context).pop(true); // Return true to trigger refresh on list
    } catch (e) {
      if (!mounted) return;
      setState(() => _isDeleting = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to delete document: $e'), backgroundColor: Colors.red),
      );
    }
  }

  void _copyExtractedText() {
    final text = _doc.ocrExtractedText ?? '';
    if (text.isEmpty) return;
    Clipboard.setData(ClipboardData(text: text));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('OCR extracted text copied to clipboard.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final confPercent = ((_doc.ocrConfidence ?? 0.0) * 100).toInt();

    return Scaffold(
      appBar: AppBar(
        title: Text(_doc.displayType),
        actions: [
          IconButton(
            icon: const Icon(Icons.delete_outline, color: Colors.white),
            tooltip: 'Delete Document',
            onPressed: _isDeleting ? null : _handleDelete,
          ),
        ],
      ),
      body: _isDeleting
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Document Overview Card
                  Card(
                    elevation: 1,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Container(
                                padding: const EdgeInsets.all(12),
                                decoration: BoxDecoration(
                                  color: AppTheme.primaryBlue.withValues(alpha: 0.1),
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: Icon(_doc.iconData, color: AppTheme.primaryBlue, size: 28),
                              ),
                              const SizedBox(width: 14),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      _doc.originalFilename,
                                      style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      '${_doc.displayType} • ${_doc.formattedFileSize}',
                                      style: const TextStyle(fontSize: 12, color: Colors.black54),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                          const Divider(height: 24),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              const Text('Uploaded On:', style: TextStyle(color: Colors.black54, fontSize: 13)),
                              Text(_doc.formattedDate, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                            ],
                          ),
                          const SizedBox(height: 8),
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              const Text('MIME Type:', style: TextStyle(color: Colors.black54, fontSize: 13)),
                              Text(_doc.mimeType, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // OCR Intelligence Card
                  Card(
                    elevation: 1,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    child: Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              const Text(
                                'OCR Document Intelligence',
                                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                              ),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                decoration: BoxDecoration(
                                  color: _doc.statusColor.withValues(alpha: 0.1),
                                  borderRadius: BorderRadius.circular(20),
                                  border: Border.all(color: _doc.statusColor.withValues(alpha: 0.4)),
                                ),
                                child: Text(
                                  _doc.statusBadgeText,
                                  style: TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.bold,
                                    color: _doc.statusColor,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 14),

                          // Confidence bar
                          Row(
                            children: [
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                      children: [
                                        const Text('Extraction Confidence', style: TextStyle(fontSize: 12, color: Colors.black54)),
                                        Text('$confPercent%', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: _doc.statusColor)),
                                      ],
                                    ),
                                    const SizedBox(height: 6),
                                    LinearProgressIndicator(
                                      value: (_doc.ocrConfidence ?? 0.0).clamp(0.0, 1.0),
                                      backgroundColor: Colors.grey.shade200,
                                      color: _doc.statusColor,
                                      minHeight: 6,
                                      borderRadius: BorderRadius.circular(3),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),

                          // Manual Review Warning Alert
                          if (_doc.manualReviewRequired) ...[
                            const SizedBox(height: 14),
                            Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: Colors.orange.shade50,
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: Colors.orange.shade300),
                              ),
                              child: Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Icon(Icons.warning_amber_rounded, color: Colors.orange.shade800, size: 22),
                                  const SizedBox(width: 10),
                                  Expanded(
                                    child: Text(
                                      _doc.ocrErrorMessage ??
                                          'Low extraction confidence detected. Review the document text carefully or upload a sharper scan.',
                                      style: TextStyle(fontSize: 12, color: Colors.orange.shade900),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],

                          const Divider(height: 24),

                          // Extracted Text Header with Copy Button
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              const Text('Extracted Text', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                              if ((_doc.ocrExtractedText ?? '').isNotEmpty)
                                TextButton.icon(
                                  icon: const Icon(Icons.copy, size: 14),
                                  label: const Text('Copy Text', style: TextStyle(fontSize: 12)),
                                  onPressed: _copyExtractedText,
                                ),
                            ],
                          ),
                          const SizedBox(height: 8),

                          // Extracted Text Display Box
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: Colors.grey.shade50,
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: Colors.grey.shade300),
                            ),
                            child: SelectableText(
                              (_doc.ocrExtractedText ?? '').isNotEmpty
                                  ? _doc.ocrExtractedText!
                                  : 'No text extracted from this document.',
                              style: const TextStyle(
                                fontFamily: 'monospace',
                                fontSize: 12,
                                height: 1.4,
                                color: Colors.black87,
                              ),
                            ),
                          ),

                          // OCR Metadata details
                          if (_doc.ocrMetadata.isNotEmpty) ...[
                            const SizedBox(height: 14),
                            Wrap(
                              spacing: 8,
                              runSpacing: 6,
                              children: [
                                if (_doc.ocrMetadata.containsKey('provider'))
                                  Chip(
                                    label: Text('Engine: ${_doc.ocrMetadata['provider']}', style: const TextStyle(fontSize: 11)),
                                    padding: EdgeInsets.zero,
                                    visualDensity: VisualDensity.compact,
                                  ),
                                if (_doc.ocrMetadata.containsKey('word_count'))
                                  Chip(
                                    label: Text('${_doc.ocrMetadata['word_count']} words', style: const TextStyle(fontSize: 11)),
                                    padding: EdgeInsets.zero,
                                    visualDensity: VisualDensity.compact,
                                  ),
                              ],
                            ),
                          ],
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 20),

                  // Actions
                  ElevatedButton.icon(
                    icon: _isRetrying
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                          )
                        : const Icon(Icons.refresh, size: 18),
                    label: Text(_isRetrying ? 'Re-running OCR...' : 'Retry OCR Processing'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primaryBlue,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    onPressed: _isRetrying ? null : _handleRetryOcr,
                  ),
                ],
              ),
            ),
    );
  }
}
