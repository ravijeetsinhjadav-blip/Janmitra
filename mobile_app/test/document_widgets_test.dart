import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:janmitra_assist/features/documents/models/document_models.dart';
import 'package:janmitra_assist/features/documents/presentation/screens/document_detail_screen.dart';
import 'package:janmitra_assist/features/documents/presentation/screens/document_vault_screen.dart';
import 'package:janmitra_assist/features/documents/presentation/widgets/upload_document_dialog.dart';

void main() {
  group('DocumentMetadataModel Tests', () {
    test('Correctly serializes and deserializes from JSON', () {
      final json = {
        'id': '11111111-2222-3333-4444-555555555555',
        'user_id': '99999999-8888-7777-6666-555555555555',
        'document_type': 'income_certificate',
        'original_filename': 'tahsildar_income_cert.pdf',
        'storage_reference': '99999999-8888-7777-6666-555555555555/abc1234.pdf',
        'mime_type': 'application/pdf',
        'file_size': 1048576, // 1 MB
        'upload_status': 'uploaded',
        'ocr_status': 'OCR_COMPLETED',
        'ocr_confidence': 0.945,
        'ocr_extracted_text': 'GOVERNMENT OF MAHARASHTRA INCOME CERTIFICATE',
        'ocr_metadata': {'provider': 'google_cloud_vision', 'pages': 1},
        'ocr_completed_at': '2026-10-31T15:00:00Z',
        'manual_review_required': false,
        'ocr_error_message': null,
        'created_at': '2026-10-31T15:00:00Z',
        'updated_at': '2026-10-31T15:00:00Z',
      };

      final doc = DocumentMetadataModel.fromJson(json);

      expect(doc.id, '11111111-2222-3333-4444-555555555555');
      expect(doc.displayType, 'Income Certificate');
      expect(doc.formattedFileSize, '1.00 MB');
      expect(doc.statusBadgeText, 'OCR Verified');
      expect(doc.manualReviewRequired, isFalse);
      expect(doc.ocrConfidence, 0.945);

      final exportedJson = doc.toJson();
      expect(exportedJson['document_type'], 'income_certificate');
      expect(exportedJson['file_size'], 1048576);
    });

    test('Formats various file sizes correctly', () {
      final small = DocumentMetadataModel(
        id: '1',
        userId: 'u',
        documentType: 'aadhaar_card',
        originalFilename: 'a.png',
        storageReference: 'ref',
        mimeType: 'image/png',
        fileSize: 512,
        uploadStatus: 'uploaded',
        ocrStatus: DocumentProcessingStatus.ocrCompleted,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );
      expect(small.formattedFileSize, '512 B');
      expect(small.displayType, 'Aadhaar Card');

      final medium = DocumentMetadataModel(
        id: '2',
        userId: 'u',
        documentType: 'caste_certificate',
        originalFilename: 'c.jpg',
        storageReference: 'ref',
        mimeType: 'image/jpeg',
        fileSize: 450560,
        uploadStatus: 'uploaded',
        ocrStatus: DocumentProcessingStatus.ocrCompleted,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );
      expect(medium.formattedFileSize, '440.0 KB');
      expect(medium.displayType, 'Caste Certificate');
    });

    test('Low confidence correctly triggers Review Needed status badge', () {
      final lowConfDoc = DocumentMetadataModel(
        id: '3',
        userId: 'u',
        documentType: 'ration_card',
        originalFilename: 'blurry_ration.jpg',
        storageReference: 'ref',
        mimeType: 'image/jpeg',
        fileSize: 200000,
        uploadStatus: 'uploaded',
        ocrStatus: DocumentProcessingStatus.manualReviewRequired,
        ocrConfidence: 0.52,
        manualReviewRequired: true,
        ocrErrorMessage: 'Low extraction confidence.',
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );

      expect(lowConfDoc.statusBadgeText, 'Review Needed');
      expect(lowConfDoc.manualReviewRequired, isTrue);
    });
  });

  group('DocumentDetailScreen Widget Tests', () {
    testWidgets('Renders document details, confidence bar, and extracted text', (WidgetTester tester) async {
      final doc = DocumentMetadataModel(
        id: '123',
        userId: 'u1',
        documentType: 'income_certificate',
        originalFilename: 'annual_income_2026.pdf',
        storageReference: 'storage/ref.pdf',
        mimeType: 'application/pdf',
        fileSize: 524288,
        uploadStatus: 'uploaded',
        ocrStatus: DocumentProcessingStatus.ocrCompleted,
        ocrConfidence: 0.94,
        ocrExtractedText: 'ANNUAL FAMILY INCOME: INR 1,20,000 CERTIFIED BY TAHSILDAR',
        ocrMetadata: {'provider': 'mock_ocr', 'word_count': 12},
        manualReviewRequired: false,
        createdAt: DateTime(2026, 10, 31),
        updatedAt: DateTime(2026, 10, 31),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: DocumentDetailScreen(document: doc),
        ),
      );

      expect(find.text('Income Certificate'), findsWidgets);
      expect(find.text('annual_income_2026.pdf'), findsOneWidget);
      expect(find.text('OCR Verified'), findsOneWidget);
      expect(find.text('Extraction Confidence'), findsOneWidget);
      expect(find.text('94%'), findsOneWidget);
      expect(find.text('Extracted Text'), findsOneWidget);
      expect(find.textContaining('ANNUAL FAMILY INCOME'), findsOneWidget);
      expect(find.text('Retry OCR Processing'), findsOneWidget);
    });

    testWidgets('Renders warning banner when manualReviewRequired is true', (WidgetTester tester) async {
      final docReview = DocumentMetadataModel(
        id: '456',
        userId: 'u1',
        documentType: 'ration_card',
        originalFilename: 'blurred_card.jpg',
        storageReference: 'storage/ref.jpg',
        mimeType: 'image/jpeg',
        fileSize: 120000,
        uploadStatus: 'uploaded',
        ocrStatus: DocumentProcessingStatus.manualReviewRequired,
        ocrConfidence: 0.50,
        ocrExtractedText: 'Partial text [Unreadable]',
        manualReviewRequired: true,
        ocrErrorMessage: 'Low extraction confidence detected. Review the document text carefully.',
        createdAt: DateTime(2026, 10, 31),
        updatedAt: DateTime(2026, 10, 31),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: DocumentDetailScreen(document: docReview),
        ),
      );

      expect(find.text('Review Needed'), findsOneWidget);
      expect(find.textContaining('Low extraction confidence detected'), findsOneWidget);
    });
  });

  group('UploadDocumentDialog Widget Tests', () {
    testWidgets('Renders upload dialog options and document classification dropdown', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: UploadDocumentDialog(),
          ),
        ),
      );
      await tester.pump();

      expect(find.text('Upload to Document Vault'), findsOneWidget);
      expect(find.text('Document Classification'), findsOneWidget);
      expect(find.text('Income Certificate'), findsOneWidget);
      expect(find.text('Camera'), findsOneWidget);
      expect(find.text('Gallery'), findsOneWidget);
      expect(find.text('File'), findsOneWidget);
      expect(find.textContaining('Accepted: PDF, JPG, PNG'), findsOneWidget);
    });
  });

  group('DocumentVaultScreen Widget Tests', () {
    testWidgets('Renders vault title, summary counters, and upload FAB', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: DocumentVaultScreen(),
        ),
      );
      await tester.pump();

      expect(find.text('Citizen Document Vault'), findsOneWidget);
      expect(find.text('Total Files'), findsOneWidget);
      expect(find.text('OCR Verified'), findsOneWidget);
      expect(find.text('Review Needed'), findsOneWidget);
      expect(find.text('All Documents'), findsOneWidget);
      expect(find.text('Upload Document'), findsOneWidget);
    });
  });

}
