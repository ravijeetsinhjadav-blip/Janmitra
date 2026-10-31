import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:janmitra_assist/features/assistance/models/assistance_models.dart';
import 'package:janmitra_assist/features/assistance/presentation/screens/application_assistance_screen.dart';

void main() {
  group('Application Assistance Models Unit Tests', () {
    test('ApplicationAssistanceModel correctly deserializes from JSON', () {
      final json = {
        'scheme_id': '11111111-1111-1111-1111-111111111111',
        'scheme_name': 'Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)',
        'category': 'Agriculture',
        'department': 'Ministry of Agriculture and Farmers Welfare',
        'assessment_id': '22222222-2222-2222-2222-222222222222',
        'overall_status': 'Potentially Eligible',
        'criteria_match_percentage': 100.0,
        'overall_readiness_score': 85.0,
        'readiness_interpretation': 'Ready for Application Preparation',
        'document_preparation_statuses': [
          {
            'document_name': 'Aadhaar Card',
            'status': 'Ready for Application Preparation',
            'notes': 'Document verified with OCR confidence 0.95.',
            'matching_document_id': '33333333-3333-3333-3333-333333333333',
          },
          {
            'document_name': 'Bank Passbook',
            'status': 'Missing',
            'notes': 'No matching document in vault.',
            'matching_document_id': null,
          },
        ],
        'checklist': [
          {
            'item_id': 'doc_aadhaar_card',
            'category': 'document',
            'title': 'Verify Aadhaar Card in Vault',
            'description': 'Ensure clear copy is uploaded.',
            'is_mandatory': true,
            'is_completed': true,
          },
          {
            'item_id': 'portal_registration',
            'category': 'portal_action',
            'title': 'Register on PM-KISAN Portal',
            'description': 'Visit official portal with Aadhaar OTP.',
            'is_mandatory': true,
            'is_completed': false,
          },
        ],
        'checklist_completed_count': 1,
        'checklist_total_count': 2,
        'checklist_completion_percentage': 50.0,
        'guide': {
          'applicant_info_required': [
            {
              'field_name': 'Aadhaar Number',
              'description': '12-digit UIDAI number',
              'importance': 'Mandatory',
            }
          ],
          'supporting_documents_specs': [
            {
              'document_type': 'Aadhaar Card',
              'specifications': 'PDF or JPEG under 2MB',
              'issuing_authority': 'UIDAI',
            }
          ],
          'important_declarations': [
            'Applicant does not pay income tax',
          ],
          'common_mistakes_to_avoid': [
            'Do not enter merged bank old IFSC code',
            'Ensure spelling in land record matches Aadhaar',
          ],
          'submission_precautions': [
            'Verify active mobile linked to Aadhaar for OTP',
          ],
          'portal_steps': [
            {
              'step_number': 1,
              'title': 'Visit Official Portal',
              'instruction': 'Navigate to pmkisan.gov.in and click New Farmer Registration.',
            }
          ],
          'language': 'en',
          'disclaimer': 'AI-assisted guidance does not guarantee application approval.',
        },
        'official_application_url': 'https://pmkisan.gov.in/RegistrationFormNew.aspx',
        'official_source_url': 'https://pmkisan.gov.in/',
        'is_demo_data': true,
        'language': 'en',
        'evaluated_at': '2026-10-31T12:00:00Z',
        'disclaimer': 'JanMitra Assist is an application preparation assistant. It does NOT submit your application.',
      };

      final model = ApplicationAssistanceModel.fromJson(json);

      expect(model.schemeId, '11111111-1111-1111-1111-111111111111');
      expect(model.schemeName, 'Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)');
      expect(model.overallStatus, 'Potentially Eligible');
      expect(model.criteriaMatchPercentage, 100.0);
      expect(model.overallReadinessScore, 85.0);
      expect(model.documentPreparationStatuses.length, 2);
      expect(model.documentPreparationStatuses[0].status, 'Ready for Application Preparation');
      expect(model.documentPreparationStatuses[1].status, 'Missing');
      expect(model.checklist.length, 2);
      expect(model.checklist[0].isCompleted, isTrue);
      expect(model.checklist[1].isCompleted, isFalse);
      expect(model.checklistCompletedCount, 1);
      expect(model.checklistTotalCount, 2);
      expect(model.checklistCompletionPercentage, 50.0);
      expect(model.guide.commonMistakesToAvoid.length, 2);
      expect(model.guide.commonMistakesToAvoid[0], contains('IFSC'));
      expect(model.guide.portalSteps.length, 1);
      expect(model.officialApplicationUrl, contains('pmkisan.gov.in'));
      expect(model.disclaimer, contains('does NOT submit'));
    });

    test('ChecklistUpdateResponseModel deserialization', () {
      final json = {
        'item_id': 'doc_aadhaar_card',
        'is_completed': true,
        'completed_count': 3,
        'total_count': 4,
        'completion_percentage': 75.0,
        'message': 'Checklist progress updated. This preparation checklist does NOT submit your application to the government.',
      };

      final res = ChecklistUpdateResponseModel.fromJson(json);
      expect(res.itemId, 'doc_aadhaar_card');
      expect(res.isCompleted, isTrue);
      expect(res.completedCount, 3);
      expect(res.totalCount, 4);
      expect(res.completionPercentage, 75.0);
      expect(res.message, contains('does NOT submit'));
    });
  });

  group('ApplicationAssistanceScreen Widget Tests', () {
    late ApplicationAssistanceModel testAssistance;

    setUp(() {
      testAssistance = ApplicationAssistanceModel(
        schemeId: '11111111-1111-1111-1111-111111111111',
        schemeName: 'Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)',
        category: 'Agriculture',
        department: 'Ministry of Agriculture and Farmers Welfare',
        overallStatus: 'Potentially Eligible',
        criteriaMatchPercentage: 100.0,
        overallReadinessScore: 85.0,
        readinessInterpretation: 'Ready for Application Preparation',
        documentPreparationStatuses: [
          DocumentPreparationStatusModel(
            documentName: 'Aadhaar Card',
            status: 'Ready for Application Preparation',
            notes: 'Verified via OCR with confidence 0.95',
            matchingDocumentId: 'doc-1',
          ),
          DocumentPreparationStatusModel(
            documentName: 'Bank Passbook',
            status: 'Missing',
            notes: 'No matching document in vault.',
          ),
        ],
        checklist: [
          ChecklistItemModel(
            itemId: 'item_1',
            category: 'document',
            title: 'Verify Aadhaar Card in Vault',
            description: 'Ensure name matches land record.',
            isMandatory: true,
            isCompleted: true,
          ),
          ChecklistItemModel(
            itemId: 'item_2',
            category: 'portal_action',
            title: 'Register on PM-KISAN Portal',
            description: 'Log in with Aadhaar and enter bank details.',
            isMandatory: true,
            isCompleted: false,
          ),
        ],
        checklistCompletedCount: 1,
        checklistTotalCount: 2,
        checklistCompletionPercentage: 50.0,
        guide: ApplicationInfoGuideModel(
          applicantInfoRequired: [
            ApplicantInfoRequirementModel(
              fieldName: 'Bank Account & IFSC',
              description: 'Active savings account for DBT credit',
              importance: 'Mandatory',
            ),
          ],
          supportingDocumentsSpecs: [
            SupportingDocumentSpecModel(
              documentType: 'Land Record (7/12)',
              specifications: 'PDF format under 2MB',
              issuingAuthority: 'Revenue Department',
            ),
          ],
          importantDeclarations: [
            'Applicant does not hold constitutional post or pay income tax.',
          ],
          commonMistakesToAvoid: [
            'Do NOT use outdated IFSC for merged banks (e.g. Allahabad Bank, Syndicate Bank).',
            'Ensure spelling in bank account exactly matches Aadhaar card.',
          ],
          submissionPrecautions: [
            'Verify Aadhaar is linked to active mobile for OTP authentication.',
          ],
          portalSteps: [
            PortalStepInstructionModel(
              stepNumber: 1,
              title: 'Access Official Portal',
              instruction: 'Visit https://pmkisan.gov.in/ and select New Farmer Registration.',
            ),
          ],
          language: 'en',
          disclaimer: 'Guidance does not guarantee official approval.',
        ),
        officialApplicationUrl: 'https://pmkisan.gov.in/RegistrationFormNew.aspx',
        officialSourceUrl: 'https://pmkisan.gov.in/',
        isDemoData: true,
        language: 'en',
        evaluatedAt: DateTime.parse('2026-10-31T12:00:00Z'),
        disclaimer: 'JanMitra Assist is an application preparation assistant. It does NOT submit your application to the government.',
      );
    });

    testWidgets('renders statutory non-submission disclaimer and scheme headers', (tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationAssistanceScreen(
            schemeId: '11111111-1111-1111-1111-111111111111',
            schemeName: 'PM-KISAN Assistance',
            initialAssistance: testAssistance,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Statutory Banner
      expect(find.text('Preparation Assistant Notice'), findsOneWidget);
      expect(find.textContaining('does NOT submit your application to the government'), findsAtLeastNWidgets(1));

      // Scheme Header & Badges
      expect(find.text('Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)'), findsOneWidget);
      expect(find.text('DEMO DATA'), findsOneWidget);
      expect(find.textContaining('Ministry of Agriculture'), findsOneWidget);

      // Multilingual selector chips
      expect(find.text('English'), findsOneWidget);
      expect(find.text('हिंदी'), findsOneWidget);
      expect(find.text('ગુજરાતી'), findsOneWidget);
    });

    testWidgets('renders interactive checklist and updates checkbox state', (tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationAssistanceScreen(
            schemeId: '11111111-1111-1111-1111-111111111111',
            schemeName: 'PM-KISAN Assistance',
            initialAssistance: testAssistance,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Checklist Title and Progress
      expect(find.text('Preparation Checklist'), findsOneWidget);
      expect(find.text('1 of 2 done'), findsOneWidget);
      expect(find.text('Verify Aadhaar Card in Vault'), findsOneWidget);
      expect(find.text('Register on PM-KISAN Portal'), findsOneWidget);

      // Verify checkboxes are present
      expect(find.byType(CheckboxListTile), findsNWidgets(2));

      // Checkbox state test
      final checkboxTiles = tester.widgetList<CheckboxListTile>(find.byType(CheckboxListTile)).toList();
      expect(checkboxTiles[0].value, isTrue);
      expect(checkboxTiles[1].value, isFalse);
    });

    testWidgets('renders document preparation status items and vault button', (tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationAssistanceScreen(
            schemeId: '11111111-1111-1111-1111-111111111111',
            initialAssistance: testAssistance,
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Document Preparation Status'), findsOneWidget);
      expect(find.text('Open Vault'), findsOneWidget);
      expect(find.text('Aadhaar Card'), findsOneWidget);
      expect(find.text('Ready for Application Preparation'), findsAtLeastNWidgets(1));
      expect(find.text('Bank Passbook'), findsOneWidget);
      expect(find.text('Missing'), findsOneWidget);
    });

    testWidgets('renders scheme guide with common mistakes and precautions', (tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationAssistanceScreen(
            schemeId: '11111111-1111-1111-1111-111111111111',
            initialAssistance: testAssistance,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Guide Headers
      expect(find.text('Scheme Information Guide'), findsOneWidget);
      expect(find.text('Common Mistakes to Avoid'), findsOneWidget);
      expect(find.textContaining('outdated IFSC for merged banks'), findsOneWidget);
      expect(find.text('Submission Precautions'), findsOneWidget);
      expect(find.textContaining('Aadhaar is linked to active mobile'), findsOneWidget);

      // Official Portal Card
      expect(find.text('Official Government Portal'), findsOneWidget);
      expect(find.text('https://pmkisan.gov.in/RegistrationFormNew.aspx'), findsOneWidget);
      expect(find.byIcon(Icons.copy), findsOneWidget);
    });
  });
}
