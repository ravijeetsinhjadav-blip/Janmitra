import 'package:flutter/material.dart';

class DocumentProcessingStatus {
  static const String uploaded = 'UPLOADED';
  static const String pendingOcr = 'PENDING_OCR';
  static const String processing = 'PROCESSING';
  static const String ocrCompleted = 'OCR_COMPLETED';
  static const String manualReviewRequired = 'MANUAL_REVIEW_REQUIRED';
  static const String ocrFailed = 'OCR_FAILED';
}

class DocumentMetadataModel {
  final String id;
  final String userId;
  final String documentType;
  final String originalFilename;
  final String storageReference;
  final String mimeType;
  final int fileSize;
  final String uploadStatus;
  final String ocrStatus;
  final double? ocrConfidence;
  final String? ocrExtractedText;
  final Map<String, dynamic> ocrMetadata;
  final DateTime? ocrCompletedAt;
  final bool manualReviewRequired;
  final String? ocrErrorMessage;
  final DateTime createdAt;
  final DateTime updatedAt;

  DocumentMetadataModel({
    required this.id,
    required this.userId,
    required this.documentType,
    required this.originalFilename,
    required this.storageReference,
    required this.mimeType,
    required this.fileSize,
    required this.uploadStatus,
    required this.ocrStatus,
    this.ocrConfidence,
    this.ocrExtractedText,
    this.ocrMetadata = const {},
    this.ocrCompletedAt,
    this.manualReviewRequired = false,
    this.ocrErrorMessage,
    required this.createdAt,
    required this.updatedAt,
  });

  factory DocumentMetadataModel.fromJson(Map<String, dynamic> json) {
    return DocumentMetadataModel(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      documentType: json['document_type'] as String? ?? 'other',
      originalFilename: json['original_filename'] as String? ?? 'document',
      storageReference: json['storage_reference'] as String? ?? '',
      mimeType: json['mime_type'] as String? ?? 'application/octet-stream',
      fileSize: (json['file_size'] as num?)?.toInt() ?? 0,
      uploadStatus: json['upload_status'] as String? ?? 'uploaded',
      ocrStatus:
          json['ocr_status'] as String? ?? DocumentProcessingStatus.uploaded,
      ocrConfidence: (json['ocr_confidence'] as num?)?.toDouble(),
      ocrExtractedText: json['ocr_extracted_text'] as String?,
      ocrMetadata: json['ocr_metadata'] is Map<String, dynamic>
          ? json['ocr_metadata'] as Map<String, dynamic>
          : {},
      ocrCompletedAt: json['ocr_completed_at'] != null
          ? DateTime.tryParse(json['ocr_completed_at'] as String)
          : null,
      manualReviewRequired: json['manual_review_required'] as bool? ?? false,
      ocrErrorMessage: json['ocr_error_message'] as String?,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'] as String) ?? DateTime.now()
          : DateTime.now(),
      updatedAt: json['updated_at'] != null
          ? DateTime.tryParse(json['updated_at'] as String) ?? DateTime.now()
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'user_id': userId,
      'document_type': documentType,
      'original_filename': originalFilename,
      'storage_reference': storageReference,
      'mime_type': mimeType,
      'file_size': fileSize,
      'upload_status': uploadStatus,
      'ocr_status': ocrStatus,
      'ocr_confidence': ocrConfidence,
      'ocr_extracted_text': ocrExtractedText,
      'ocr_metadata': ocrMetadata,
      'ocr_completed_at': ocrCompletedAt?.toIso8601String(),
      'manual_review_required': manualReviewRequired,
      'ocr_error_message': ocrErrorMessage,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }

  // Display name helper
  String get displayType {
    switch (documentType.toLowerCase()) {
      case 'income_certificate':
        return 'Income Certificate';
      case 'caste_certificate':
        return 'Caste Certificate';
      case 'domicile_certificate':
      case 'domicile':
        return 'Domicile / Resident Certificate';
      case 'ration_card':
        return 'Ration Card';
      case 'aadhaar_card':
      case 'aadhaar':
        return 'Aadhaar Card';
      case 'land_record':
      case 'land_records':
        return 'Land Record (7/12 / Khatauni)';
      case 'pan_card':
        return 'PAN Card';
      case 'bank_passbook':
        return 'Bank Passbook / Statement';
      default:
        return documentType
            .replaceAll('_', ' ')
            .split(' ')
            .map((w) =>
                w.isNotEmpty ? '${w[0].toUpperCase()}${w.substring(1)}' : '')
            .join(' ');
    }
  }

  // Formatted file size string
  String get formattedFileSize {
    if (fileSize < 1024) {
      return '$fileSize B';
    }
    if (fileSize < 1024 * 1024) {
      return '${(fileSize / 1024).toStringAsFixed(1)} KB';
    }
    return '${(fileSize / (1024 * 1024)).toStringAsFixed(2)} MB';
  }

  // Formatted date string
  String get formattedDate {
    return '${createdAt.day.toString().padLeft(2, '0')}/${createdAt.month.toString().padLeft(2, '0')}/${createdAt.year}';
  }

  // Status color
  Color get statusColor {
    if (ocrStatus == DocumentProcessingStatus.ocrCompleted &&
        !manualReviewRequired) {
      return Colors.green.shade700;
    }
    if (manualReviewRequired ||
        ocrStatus == DocumentProcessingStatus.manualReviewRequired) {
      return Colors.orange.shade800;
    }
    if (ocrStatus == DocumentProcessingStatus.ocrFailed) {
      return Colors.red.shade700;
    }
    if (ocrStatus == DocumentProcessingStatus.processing) {
      return Colors.blue.shade700;
    }
    return Colors.grey.shade700;
  }

  // Status badge label
  String get statusBadgeText {
    if (ocrStatus == DocumentProcessingStatus.ocrCompleted &&
        !manualReviewRequired) {
      return 'OCR Completed';
    }
    if (manualReviewRequired ||
        ocrStatus == DocumentProcessingStatus.manualReviewRequired) {
      return 'Review Needed';
    }

    if (ocrStatus == DocumentProcessingStatus.ocrFailed) {
      return 'OCR Failed';
    }
    if (ocrStatus == DocumentProcessingStatus.processing) {
      return 'Processing...';
    }
    return 'Uploaded';
  }

  IconData get iconData {
    if (mimeType.contains('pdf')) {
      return Icons.picture_as_pdf;
    }
    return Icons.image;
  }
}

class SchemeDocumentChecklistItemModel {
  final String documentType;
  final String? description;
  final bool isMandatory;
  final bool isUploaded;
  final String? uploadedDocumentId;
  final String? ocrStatus;
  final bool manualReviewRequired;

  SchemeDocumentChecklistItemModel({
    required this.documentType,
    this.description,
    this.isMandatory = true,
    required this.isUploaded,
    this.uploadedDocumentId,
    this.ocrStatus,
    this.manualReviewRequired = false,
  });

  factory SchemeDocumentChecklistItemModel.fromJson(Map<String, dynamic> json) {
    return SchemeDocumentChecklistItemModel(
      documentType: json['document_type'] as String? ?? '',
      description: json['description'] as String?,
      isMandatory: json['is_mandatory'] as bool? ?? true,
      isUploaded: json['is_uploaded'] as bool? ?? false,
      uploadedDocumentId: json['uploaded_document_id'] as String?,
      ocrStatus: json['ocr_status'] as String?,
      manualReviewRequired: json['manual_review_required'] as bool? ?? false,
    );
  }
}

class SchemeDocumentChecklistModel {
  final String schemeId;
  final String schemeName;
  final int totalRequired;
  final int totalUploaded;
  final bool isFullyPrepared;
  final List<SchemeDocumentChecklistItemModel> checklist;
  final String disclaimer;

  SchemeDocumentChecklistModel({
    required this.schemeId,
    required this.schemeName,
    required this.totalRequired,
    required this.totalUploaded,
    required this.isFullyPrepared,
    required this.checklist,
    required this.disclaimer,
  });

  factory SchemeDocumentChecklistModel.fromJson(Map<String, dynamic> json) {
    final rawChecklist = json['checklist'] as List<dynamic>? ?? [];
    return SchemeDocumentChecklistModel(
      schemeId: json['scheme_id'] as String,
      schemeName: json['scheme_name'] as String? ?? '',
      totalRequired: (json['total_required'] as num?)?.toInt() ?? 0,
      totalUploaded: (json['total_uploaded'] as num?)?.toInt() ?? 0,
      isFullyPrepared: json['is_fully_prepared'] as bool? ?? false,
      checklist: rawChecklist
          .map((item) => SchemeDocumentChecklistItemModel.fromJson(
              item as Map<String, dynamic>))
          .toList(),
      disclaimer: json['disclaimer'] as String? ?? '',
    );
  }
}
