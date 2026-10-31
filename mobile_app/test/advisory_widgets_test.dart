import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:janmitra_assist/features/readiness/models/advisory_models.dart';
import 'package:janmitra_assist/features/readiness/presentation/screens/ai_advisory_screen.dart';

void main() {
  group('Advisory Models Unit Tests', () {
    test('AdvisoryAssessmentModel correctly serializes and deserializes from JSON', () {
      final json = {
        'assessment_id': '11111111-1111-1111-1111-111111111111',
        'scheme_id': '22222222-2222-2222-2222-222222222222',
        'scheme_name': 'Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)',
        'category': 'Agriculture',
        'overall_status': 'Potentially Eligible',
        'readiness': {
          'overall_readiness_score': 85.5,
          'criteria_match_percentage': 100.0,
          'document_coverage_percentage': 75.0,
          'information_completeness_percentage': 80.0,
          'consistency_score': 100.0,
          'consistency_status': 'Consistent',
          'score_interpretation': 'Readiness score is an advisory index.',
          'uploaded_document_types': ['Aadhaar Card', 'Land Record (7/12)'],
          'missing_document_types': ['Bank Passbook'],
          'discrepancies': [],
          'low_confidence_documents': [],
        },
        'advisory': {
          'summary': 'You meet preliminary criteria for PM-KISAN with 100% criteria match.',
          'assessment_explanation': 'Your profile satisfies the evaluated landholding parameters.',
          'criteria_analysis': [
            {'condition': 'Landholding', 'status': 'satisfied', 'note': 'Landholding satisfied.'}
          ],
          'document_analysis': 'Uploaded 2 of 3 required documents.',
          'potential_inconsistencies': [],
          'next_steps': ['Upload bank passbook to vault', 'Visit pmkisan.gov.in'],
          'official_portal_guidance': 'Visit pmkisan.gov.in to register.',
          'citations': [
            {
              'title': 'PM-KISAN Guidelines',
              'source_title': 'Ministry of Agriculture Guidelines',
              'source_reference': 'Section 3.1',
              'source_url': 'https://pmkisan.gov.in/',
              'source_freshness_status': 'Verified Official Source',
              'is_demo_data': true,
            }
          ],
          'language': 'en',
          'is_mock': true,
          'disclaimer': 'Advisory Notice: This guidance is AI-assisted and does not replace official determinations.',
        },
        'evaluated_at': '2026-10-31T12:00:00Z',
        'official_source_url': 'https://pmkisan.gov.in/',
        'official_application_url': 'https://pmkisan.gov.in/RegistrationFormNew.aspx',
      };

      final model = AdvisoryAssessmentModel.fromJson(json);

      expect(model.assessmentId, '11111111-1111-1111-1111-111111111111');
      expect(model.schemeName, 'Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)');
      expect(model.category, 'Agriculture');
      expect(model.overallStatus, 'Potentially Eligible');
      expect(model.readiness.overallReadinessScore, 85.5);
      expect(model.readiness.criteriaMatchPercentage, 100.0);
      expect(model.readiness.consistencyStatus, 'Consistent');
      expect(model.readiness.uploadedDocumentTypes.length, 2);
      expect(model.readiness.missingDocumentTypes.length, 1);
      expect(model.advisory.citations.length, 1);
      expect(model.advisory.citations.first.sourceReference, 'Section 3.1');
      expect(model.advisory.nextSteps.length, 2);
      expect(model.advisory.language, 'en');
      expect(model.advisory.isMock, isTrue);
    });

    test('ReadinessBreakdownModel handles low confidence and discrepancies', () {
      final json = {
        'overall_readiness_score': 52.0,
        'criteria_match_percentage': 60.0,
        'document_coverage_percentage': 50.0,
        'information_completeness_percentage': 60.0,
        'consistency_score': 50.0,
        'consistency_status': 'Discrepancy Detected',
        'score_interpretation': 'Discrepancy detected between profile and documents.',
        'uploaded_document_types': ['Aadhaar Card'],
        'missing_document_types': ['Ration Card'],
        'discrepancies': ['Name mismatch in Aadhaar Card'],
        'low_confidence_documents': ['Ration Card (blurry.pdf)'],
      };

      final model = ReadinessBreakdownModel.fromJson(json);
      expect(model.overallReadinessScore, 52.0);
      expect(model.consistencyStatus, 'Discrepancy Detected');
      expect(model.discrepancies.length, 1);
      expect(model.lowConfidenceDocuments.length, 1);
    });
  });

  group('AIAdvisoryScreen Widget Tests', () {
    final sampleAdvisory = AdvisoryAssessmentModel(
      assessmentId: 'test-assessment-uuid',
      schemeId: 'test-scheme-uuid',
      schemeName: 'Ayushman Bharat PM-JAY',
      category: 'Healthcare',
      overallStatus: 'Potentially Eligible',
      readiness: ReadinessBreakdownModel(
        overallReadinessScore: 92.0,
        criteriaMatchPercentage: 100.0,
        documentCoveragePercentage: 100.0,
        informationCompletenessPercentage: 100.0,
        consistencyScore: 100.0,
        consistencyStatus: 'Consistent',
        scoreInterpretation: 'Advisory composite readiness score.',
        uploadedDocumentTypes: ['Aadhaar Card', 'Ration Card'],
        missingDocumentTypes: [],
        discrepancies: [],
        lowConfidenceDocuments: [],
      ),
      advisory: AIAdvisoryGuidanceModel(
        summary: 'Your family is eligible for cashless hospitalization up to ₹5 Lakh/year.',
        assessmentExplanation: 'Income and SECC deprivation criteria are fully satisfied.',
        criteriaAnalysis: [
          ConditionAnalysisModel(condition: 'Annual Income', status: 'satisfied', note: 'Income within limits.')
        ],
        documentAnalysis: 'All mandatory identity and household documents are uploaded in vault.',
        potentialInconsistencies: [],
        nextSteps: ['Visit empanelled hospital Aarogyamitra desk', 'Present Aadhaar for golden card generation'],
        officialPortalGuidance: 'Visit pmjay.gov.in to locate network hospitals.',
        citations: [
          CitationModel(
            title: 'NHA BIS Guidelines',
            sourceTitle: 'National Health Authority',
            sourceReference: 'Chapter 2',
            sourceUrl: 'https://pmjay.gov.in/',
            sourceFreshnessStatus: 'Verified Official Source',
            isDemoData: true,
          )
        ],
        language: 'en',
        isMock: true,
        disclaimer: 'Advisory Notice: This guidance is AI-assisted and does not constitute official government approval.',
      ),
      evaluatedAt: DateTime.now(),
      officialSourceUrl: 'https://pmjay.gov.in/',
      officialApplicationUrl: 'https://mera.pmjay.gov.in/',
    );

    testWidgets('Renders advisory screen with score gauge, language selector, and next steps', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: AIAdvisoryScreen(initialAdvisory: sampleAdvisory),
        ),
      );

      // Verify AppBar and Language Chips
      expect(find.text('AI Advisory & Readiness'), findsOneWidget);
      expect(find.text('EN'), findsOneWidget);
      expect(find.text('हिंदी'), findsOneWidget);
      expect(find.text('ગુજરાતી'), findsOneWidget);

      // Verify Statutory Advisory Banner
      expect(find.textContaining('Advisory Notice: This guidance is AI-assisted'), findsOneWidget);

      // Verify Scheme Overview
      expect(find.text('Ayushman Bharat PM-JAY'), findsOneWidget);
      expect(find.text('Healthcare'), findsOneWidget);
      expect(find.text('Potentially Eligible'), findsOneWidget);

      // Verify Readiness Score and Component Bars
      expect(find.text('Application Readiness Score'), findsOneWidget);
      expect(find.text('92.0%'), findsOneWidget);
      expect(find.text('Criteria Match'), findsOneWidget);
      expect(find.text('Document Consistency'), findsOneWidget);

      // Verify AI Guidance & Next Steps
      expect(find.textContaining('Your family is eligible for cashless hospitalization'), findsOneWidget);
      expect(find.text('Actionable Next Steps'), findsOneWidget);
      expect(find.textContaining('Visit empanelled hospital Aarogyamitra desk'), findsOneWidget);

      // Verify Citations
      expect(find.text('Verified Scheme Source References'), findsOneWidget);
      expect(find.text('NHA BIS Guidelines'), findsOneWidget);
    });

    testWidgets('Renders discrepancy warning banner when inconsistencies are detected', (tester) async {
      final discrepancyAdvisory = AdvisoryAssessmentModel(
        assessmentId: 'test-disc-uuid',
        schemeId: 'test-scheme-uuid',
        schemeName: 'PMAY-G (Gramin)',
        category: 'Housing',
        overallStatus: 'Insufficient Information',
        readiness: ReadinessBreakdownModel(
          overallReadinessScore: 48.0,
          criteriaMatchPercentage: 50.0,
          documentCoveragePercentage: 50.0,
          informationCompletenessPercentage: 50.0,
          consistencyScore: 50.0,
          consistencyStatus: 'Discrepancy Detected',
          scoreInterpretation: 'Advisory composite readiness score.',
          uploadedDocumentTypes: ['Aadhaar Card'],
          missingDocumentTypes: ['MGNREGA Job Card'],
          discrepancies: ['Name mismatch in Aadhaar Card'],
          lowConfidenceDocuments: [],
        ),
        advisory: AIAdvisoryGuidanceModel(
          summary: 'Missing mandatory job card and name mismatch detected.',
          assessmentExplanation: 'Cannot verify housing deprivation without complete records.',
          criteriaAnalysis: [],
          documentAnalysis: 'Upload MGNREGA Job Card.',
          potentialInconsistencies: ['Name in profile differs from name in Aadhaar Card.'],
          nextSteps: ['Correct name on profile or re-upload Aadhaar'],
          officialPortalGuidance: 'Visit pmayg.nic.in',
          citations: [],
          language: 'en',
          isMock: true,
          disclaimer: 'Advisory Notice: Guidance is advisory only.',
        ),
        evaluatedAt: DateTime.now(),
        officialSourceUrl: 'https://pmayg.nic.in/',
        officialApplicationUrl: 'https://pmayg.nic.in/',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: AIAdvisoryScreen(initialAdvisory: discrepancyAdvisory),
        ),
      );

      expect(find.text('Potential Inconsistencies Detected'), findsOneWidget);
      expect(find.textContaining('Name in profile differs from name in Aadhaar Card'), findsOneWidget);
      expect(find.text('Discrepancy Detected'), findsWidgets);
    });
  });
}
