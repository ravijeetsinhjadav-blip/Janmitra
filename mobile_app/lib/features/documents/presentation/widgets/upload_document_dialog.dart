import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:file_picker/file_picker.dart';
import '../../../../core/theme/app_theme.dart';
import '../../models/document_models.dart';
import '../../services/document_service.dart';

class UploadDocumentDialog extends StatefulWidget {
  final String? initialDocumentType;
  final VoidCallback? onUploadSuccess;

  const UploadDocumentDialog({
    super.key,
    this.initialDocumentType,
    this.onUploadSuccess,
  });

  static Future<DocumentMetadataModel?> show(
    BuildContext context, {
    String? initialDocumentType,
    VoidCallback? onUploadSuccess,
  }) {
    return showModalBottomSheet<DocumentMetadataModel>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(ctx).viewInsets.bottom,
        ),
        child: UploadDocumentDialog(
          initialDocumentType: initialDocumentType,
          onUploadSuccess: onUploadSuccess,
        ),
      ),
    );
  }

  @override
  State<UploadDocumentDialog> createState() => _UploadDocumentDialogState();
}

class _UploadDocumentDialogState extends State<UploadDocumentDialog> {
  final DocumentService _documentService = DocumentService();
  final ImagePicker _picker = ImagePicker();

  late String _selectedType;
  Uint8List? _fileBytes;
  String? _fileName;
  bool _isUploading = false;
  String? _errorMessage;

  final List<Map<String, String>> _documentTypes = [
    {'value': 'income_certificate', 'label': 'Income Certificate'},
    {'value': 'caste_certificate', 'label': 'Caste Certificate'},
    {'value': 'domicile_certificate', 'label': 'Domicile Certificate'},
    {'value': 'ration_card', 'label': 'Ration Card'},
    {'value': 'voter_id', 'label': 'Voter ID / Photo ID'},
    {'value': 'land_record', 'label': 'Land Record (7/12)'},
    {'value': 'bank_passbook', 'label': 'Bank Passbook'},
    {'value': 'other', 'label': 'Other Document'},
    {
      'value': 'income_certificate',
      'label': 'Income Certificate (आय प्रमाण पत्र)'
    },
    {
      'value': 'caste_certificate',
      'label': 'Caste Certificate (जाति प्रमाण पत्र)'
    },
    {
      'value': 'domicile_certificate',
      'label': 'Domicile Certificate (निवास प्रमाण पत्र)'
    },
    {'value': 'ration_card', 'label': 'Ration Card (राशन कार्ड)'},
    {'value': 'aadhaar_card', 'label': 'Aadhaar Card (आधार कार्ड)'},
    {'value': 'pan_card', 'label': 'PAN Card (पैन कार्ड)'},
    {'value': 'voter_id', 'label': 'Voter ID (मतदाता पहचान पत्र)'},
    {'value': 'land_record', 'label': 'Land Record (7/12 / भूलेख)'},
    {'value': 'bank_passbook', 'label': 'Bank Passbook (बैंक पासबुक)'},
    {'value': 'other', 'label': 'Other Official Document'},
  ];

  @override
  void initState() {
    super.initState();
    _selectedType = widget.initialDocumentType ?? 'income_certificate';
  }

  Future<void> _pickFromCamera() async {
    setState(() => _errorMessage = null);
    try {
      final photo = await _picker.pickImage(
        source: ImageSource.camera,
        imageQuality: 85,
      );
      if (photo != null) {
        final bytes = await photo.readAsBytes();
        setState(() {
          _fileBytes = bytes;
          _fileName = photo.name;
        });
      }
    } catch (e) {
      setState(() => _errorMessage = 'Failed to capture photo: $e');
    }
  }

  Future<void> _pickFromGallery() async {
    setState(() => _errorMessage = null);
    try {
      final image = await _picker.pickImage(
        source: ImageSource.gallery,
        imageQuality: 85,
      );
      if (image != null) {
        final bytes = await image.readAsBytes();
        setState(() {
          _fileBytes = bytes;
          _fileName = image.name;
        });
      }
    } catch (e) {
      setState(() => _errorMessage = 'Failed to select image: $e');
    }
  }

  Future<void> _pickFromFilePicker() async {
    setState(() => _errorMessage = null);
    try {
      final result = await FilePicker.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['pdf', 'jpg', 'jpeg', 'png'],
        withData: true,
      );
      if (result != null && result.files.isNotEmpty) {
        final file = result.files.first;
        Uint8List? bytes = file.bytes;
        if (bytes == null) {
          try {
            bytes = await file.xFile.readAsBytes();
          } catch (_) {}
        }
        if (bytes != null && bytes.isNotEmpty) {
          setState(() {
            _fileBytes = bytes;
            _fileName = file.name;
          });
        } else {
          setState(() => _errorMessage =
              'Could not read file bytes. Please try another file.');
        }
      }
    } catch (e) {
      setState(() => _errorMessage = 'Failed to select file: $e');
    }
  }

  void _loadSampleDocument() {
    setState(() => _errorMessage = null);
    // Standard valid PDF header & structure conforming to magic bytes validation (%PDF-1.4)
    const samplePdfString = "%PDF-1.4\n"
        "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        "trailer\n<< /Root 1 0 R >>\n%%EOF";
    final bytes = Uint8List.fromList(samplePdfString.codeUnits);
    final extMap = {
      'income_certificate': 'income_certificate_sample.pdf',
      'caste_certificate': 'caste_certificate_sample.pdf',
      'domicile_certificate': 'domicile_certificate_sample.pdf',
      'ration_card': 'ration_card_sample.pdf',
      'voter_id': 'voter_id_sample.pdf',
      'land_record': 'land_record_sample.pdf',
      'bank_passbook': 'bank_passbook_sample.pdf',
    };
    final name = extMap[_selectedType] ?? 'official_document_sample.pdf';
    setState(() {
      _fileBytes = bytes;
      _fileName = name;
    });
  }

  Future<void> _handleUpload() async {
    if (_fileBytes == null || _fileName == null) {
      setState(() => _errorMessage = 'Please choose a document to upload.');
      return;
    }

    setState(() {
      _isUploading = true;
      _errorMessage = null;
    });

    try {
      final result = await _documentService.uploadDocument(
        fileBytes: _fileBytes!,
        filename: _fileName!,
        documentType: _selectedType,
      );

      // Verify OCR outcome: If OCR failed (e.g. invalid document or unmatched type), reject immediately
      if (result.ocrStatus == DocumentProcessingStatus.ocrFailed) {
        // Automatically purge the invalid document from vault
        try {
          await _documentService.deleteDocument(result.id);
        } catch (_) {}

        if (!mounted) return;
        setState(() {
          _isUploading = false;
          _errorMessage = result.ocrErrorMessage ??
              'Document verification failed: Uploaded image does not match the selected document type. Please upload a genuine, clear document.';
        });
        return;
      }

      if (!mounted) return;
      widget.onUploadSuccess?.call();
      Navigator.of(context).pop(result);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isUploading = false;
        _errorMessage = e.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppTheme.primaryBlue.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child:
                    const Icon(Icons.upload_file, color: AppTheme.primaryBlue),
              ),
              const SizedBox(width: 12),
              const Expanded(
                child: Text(
                  'Upload to Document Vault',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: Colors.black87,
                  ),
                ),
              ),
              IconButton(
                icon: const Icon(Icons.close, color: Colors.grey),
                onPressed: () => Navigator.of(context).pop(),
              ),
            ],
          ),
          const SizedBox(height: 16),
          // Document Type Selector
          DropdownButtonFormField<String>(
            initialValue: _selectedType,
            decoration: const InputDecoration(
              labelText: 'Document Classification',
              border: OutlineInputBorder(),
              contentPadding:
                  EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            ),
            items: _documentTypes.map((t) {
              return DropdownMenuItem<String>(
                value: t['value'],
                child: Text(t['label']!),
              );
            }).toList(),
            onChanged: (val) {
              if (val != null) setState(() => _selectedType = val);
            },
          ),
          const SizedBox(height: 16),
          // Source Options
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  icon: const Icon(Icons.camera_alt, size: 18),
                  label: const Text('Camera'),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                  onPressed: _isUploading ? null : _pickFromCamera,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: OutlinedButton.icon(
                  icon: const Icon(Icons.photo_library, size: 18),
                  label: const Text('Gallery'),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                  onPressed: _isUploading ? null : _pickFromGallery,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: OutlinedButton.icon(
                  icon: const Icon(Icons.attach_file, size: 18),
                  label: const Text('File'),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                  onPressed: _isUploading ? null : _pickFromFilePicker,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          OutlinedButton.icon(
            icon: const Icon(Icons.auto_awesome,
                color: AppTheme.primaryBlue, size: 18),
            label: const Text('⚡ Use Sample Document (Viva Demo)'),
            style: OutlinedButton.styleFrom(
              foregroundColor: AppTheme.primaryBlue,
              side: const BorderSide(color: AppTheme.primaryBlue, width: 1.2),
              padding: const EdgeInsets.symmetric(vertical: 10),
            ),
            onPressed: _isUploading ? null : _loadSampleDocument,
          ),
          const SizedBox(height: 14),
          // Selected File Indicator
          if (_fileName != null)
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.blue.shade50,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.blue.shade200),
              ),
              child: Row(
                children: [
                  Icon(
                    _fileName!.endsWith('.pdf')
                        ? Icons.picture_as_pdf
                        : Icons.image,
                    color: AppTheme.primaryBlue,
                    size: 24,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _fileName!,
                          style: const TextStyle(
                              fontWeight: FontWeight.w600, fontSize: 13),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        if (_fileBytes != null)
                          Text(
                            '${(_fileBytes!.lengthInBytes / 1024).toStringAsFixed(1)} KB ready for OCR',
                            style: const TextStyle(
                                fontSize: 11, color: Colors.black54),
                          ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.delete_outline,
                        color: Colors.red, size: 20),
                    onPressed: () {
                      setState(() {
                        _fileBytes = null;
                        _fileName = null;
                      });
                    },
                  ),
                ],
              ),
            ),
          if (_errorMessage != null) ...[
            const SizedBox(height: 10),
            Text(
              _errorMessage!,
              style: const TextStyle(color: Colors.red, fontSize: 12),
            ),
          ],
          const SizedBox(height: 18),
          ElevatedButton(
            onPressed:
                (_fileBytes != null && !_isUploading) ? _handleUpload : null,
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.primaryBlue,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 14),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8)),
            ),
            child: _isUploading
                ? const Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: Colors.white),
                      ),
                      SizedBox(width: 12),
                      Text('Analyzing Document with OCR...'),
                    ],
                  )
                : const Text('Upload & Run OCR Extraction',
                    style: TextStyle(fontWeight: FontWeight.bold)),
          ),
          const SizedBox(height: 8),
          const Text(
            'Accepted: PDF, JPG, PNG (Max 10 MB). Safe local storage with zero cloud retention.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 11, color: Colors.black45),
          ),
        ],
      ),
    );
  }
}
