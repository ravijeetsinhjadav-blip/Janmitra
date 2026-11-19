import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:janmitra_assist/features/documents/presentation/screens/document_guide_screen.dart';
import 'package:janmitra_assist/features/schemes/models/scheme_intelligence_models.dart';
import 'package:janmitra_assist/features/schemes/presentation/widgets/scheme_beneficiary_analytics_widget.dart';

void main() {
  group('Scheme Intelligence Models Test', () {
    test('SchemeCategoryRuleModel deserializes correctly', () {
      final json = {
        'id': 'rule-123',
        'scheme_id': 'scheme-123',
        'category': 'OBC',
        'condition_name': 'Income Limit',
        'field': 'annual_family_income',
        'operator': 'lte',
        'expected_value': 250000,
        'special_conditions': 'Requires valid NCL certificate',
      };
      final model = SchemeCategoryRuleModel.fromJson(json);
      expect(model.id, 'rule-123');
      expect(model.category, 'OBC');
      expect(model.operator, 'lte');
      expect(model.expectedValue, 250000);
      expect(model.specialConditions, contains('NCL'));
    });

    test('DocumentGuideModel deserializes with state authority and steps', () {
      final json = {
        'id': 'guide-123',
        'document_type': 'income_certificate',
        'document_name': 'Income Certificate',
        'description': 'Certifies annual family income',
        'issuing_department': 'Revenue Department',
        'state_specific_authority': {
          'Maharashtra': 'Tahsildar via Aaple Sarkar',
          'Gujarat': 'Mamlatdar via Digital Gujarat',
        },
        'required_supporting_documents': [
          'Voter ID',
          'Electricity Bill',
          'Salary Slip',
        ],
        'online_steps': {
          'en': ['Step 1: Visit portal', 'Step 2: Submit form'],
        },
        'offline_steps': {
          'en': ['Step 1: Visit office', 'Step 2: Collect certificate'],
        },
        'fees_and_timelines': {
          'statutory_fee_inr': 33,
          'statutory_delivery_days': 15,
        },
        'official_links': {
          'application_portal': 'https://aaplesarkar.mahaonline.gov.in',
        },
        'languages_supported': ['en', 'hi', 'gu'],
      };

      final model = DocumentGuideModel.fromJson(json);
      expect(model.documentType, 'income_certificate');
      expect(model.stateSpecificAuthority['Maharashtra'], contains('Aaple Sarkar'));
      expect(model.requiredSupportingDocuments.length, 3);
      expect(model.onlineSteps['en']?.length, 2);
      expect(model.feesAndTimelines['statutory_fee_inr'], 33);
    });

    test('SchemeAnalyticsDatasetModel deserializes breakdowns correctly', () {
      final json = {
        'id': 'dataset-123',
        'scheme_id': 'scheme-123',
        'source_name': 'Ministry of Agriculture',
        'source_url': 'https://pmkisan.gov.in',
        'reporting_period': 'FY 2023-24',
        'metric_type': 'unique_farmer_households',
        'total_beneficiaries': 110000000,
        'dataset_version': 1,
        'verification_status': 'Verified',
        'is_published': true,
        'civic_disclaimer': 'Official Government Aggregate Data.',
        'breakdowns': [
          {
            'id': 'b-1',
            'dimension': 'caste_category',
            'category_name': 'OBC',
            'metric_value': 37400000,
            'percentage': 34.0,
          },
          {
            'id': 'b-2',
            'dimension': 'gender',
            'category_name': 'Female',
            'metric_value': 28600000,
            'percentage': 26.0,
          },
        ],
      };

      final model = SchemeAnalyticsDatasetModel.fromJson(json);
      expect(model.totalBeneficiaries, 110000000);
      expect(model.isPublished, true);
      expect(model.verificationStatus, 'Verified');
      expect(model.breakdowns.length, 2);
      expect(model.breakdowns.first.categoryName, 'OBC');
      expect(model.breakdowns.first.percentage, 34.0);
    });
  });

  group('Scheme Intelligence Widgets Test', () {
    testWidgets('DocumentGuideScreen renders loading then structure',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: DocumentGuideScreen(
            documentType: 'income_certificate',
            documentTitle: 'Income Certificate',
          ),
        ),
      );

      // Verify app bar title exists
      expect(find.text('Income Certificate'), findsOneWidget);
    });

    testWidgets('SchemeBeneficiaryAnalyticsWidget displays fallback when loading',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: SchemeBeneficiaryAnalyticsWidget(
              schemeId: '11111111-1111-1111-1111-111111111111',
              schemeName: 'PM-KISAN',
            ),
          ),
        ),
      );

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });
  });
}

