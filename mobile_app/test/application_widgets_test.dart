import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:janmitra_assist/features/applications/presentation/widgets/application_disclaimer_card.dart';
import 'package:janmitra_assist/features/applications/presentation/widgets/application_status_badge.dart';
import 'package:janmitra_assist/features/applications/presentation/widgets/scheme_picker_bottom_sheet.dart';
import 'package:janmitra_assist/features/schemes/models/scheme_models.dart';
import 'package:janmitra_assist/features/schemes/services/scheme_service.dart';

/// Fake SchemeService for deterministic widget testing
class FakeSchemeService implements SchemeService {
  final Future<SchemeListResponseModel> Function({
    String? query,
    String? category,
    String? state,
    int page,
    int pageSize,
  }) onGetSchemes;

  FakeSchemeService({required this.onGetSchemes});

  @override
  Future<SchemeListResponseModel> getSchemes({
    String? query,
    String? category,
    String? state,
    int page = 1,
    int pageSize = 20,
  }) {
    return onGetSchemes(
      query: query,
      category: category,
      state: state,
      page: page,
      pageSize: pageSize,
    );
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  final sampleScheme = SchemeModel(
    id: '11111111-1111-1111-1111-111111111111',
    schemeName: 'Pradhan Mantri Kisan Samman Nidhi',
    shortDescription: 'Income support of ₹6,000/year for farmer families.',
    description: 'PM-KISAN is an income support scheme for farmers.',
    department: 'Ministry of Agriculture',
    category: 'Agriculture',
    stateApplicability: 'All India',
    eligibilitySummary: 'All landholding farmer families.',
    benefits: ['₹6,000 per year'],
    eligibilityCriteria: [],
    requiredProfileFields: ['occupation'],
    applicationProcess: ['Apply via online portal'],
    requiredDocuments: ['Aadhaar', 'Land Record'],
    officialSourceUrl: 'https://pmkisan.gov.in',
    officialApplicationUrl: 'https://pmkisan.gov.in/register',
    status: 'active',
    isDemoData: false,
  );

  group('ApplicationStatusBadge Tests', () {
    testWidgets('renders Submitted status correctly', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(body: ApplicationStatusBadge(status: 'Submitted')),
        ),
      );

      expect(find.text('Submitted'), findsOneWidget);
      expect(find.byIcon(Icons.send_rounded), findsOneWidget);
    });

    testWidgets('renders Under Review status correctly', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(body: ApplicationStatusBadge(status: 'Under Review')),
        ),
      );

      expect(find.text('Under Review'), findsOneWidget);
      expect(find.byIcon(Icons.hourglass_top_rounded), findsOneWidget);
    });

    testWidgets('renders Pending status correctly', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(body: ApplicationStatusBadge(status: 'Pending')),
        ),
      );

      expect(find.text('Pending'), findsOneWidget);
      expect(find.byIcon(Icons.pending_actions_rounded), findsOneWidget);
    });

    testWidgets('renders Document Verification status correctly',
        (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
              body: ApplicationStatusBadge(status: 'Document Verification')),
        ),
      );

      expect(find.text('Document Verification'), findsOneWidget);
      expect(find.byIcon(Icons.fact_check_rounded), findsOneWidget);
    });

    testWidgets(
        'renders Approved status with explicit Citizen Reported qualification',
        (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(body: ApplicationStatusBadge(status: 'Approved')),
        ),
      );

      expect(find.text('Approved (Citizen Reported)'), findsOneWidget);
      expect(find.byIcon(Icons.check_circle_rounded), findsOneWidget);
    });

    testWidgets(
        'renders Rejected status with explicit Citizen Reported qualification',
        (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(body: ApplicationStatusBadge(status: 'Rejected')),
        ),
      );

      expect(find.text('Rejected (Citizen Reported)'), findsOneWidget);
      expect(find.byIcon(Icons.cancel_rounded), findsOneWidget);
    });

    testWidgets('renders Completed status correctly', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(body: ApplicationStatusBadge(status: 'Completed')),
        ),
      );

      expect(find.text('Completed'), findsOneWidget);
      expect(find.byIcon(Icons.task_alt_rounded), findsOneWidget);
    });

    testWidgets('renders fallback style for unknown status gracefully',
        (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(body: ApplicationStatusBadge(status: 'Custom Status')),
        ),
      );

      expect(find.text('Custom Status'), findsOneWidget);
      expect(find.byIcon(Icons.info_outline_rounded), findsOneWidget);
    });

    testWidgets(
        'renders compact mode with abbreviated self-reported tag for Approved and Rejected',
        (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Column(
              children: [
                ApplicationStatusBadge(status: 'Approved', isCompact: true),
                ApplicationStatusBadge(status: 'Rejected', isCompact: true),
              ],
            ),
          ),
        ),
      );

      expect(find.text('Approved (Self-Reported)'), findsOneWidget);
      expect(find.text('Rejected (Self-Reported)'), findsOneWidget);
    });

    testWidgets(
        'renders Approved with Citizen Reported even when showCitizenReportedTag is false',
        (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ApplicationStatusBadge(
              status: 'Approved',
              showCitizenReportedTag: false,
            ),
          ),
        ),
      );

      expect(find.text('Approved (Citizen Reported)'), findsOneWidget);
    });

    testWidgets(
        'renders Rejected with Citizen Reported even when showCitizenReportedTag is false',
        (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ApplicationStatusBadge(
              status: 'Rejected',
              showCitizenReportedTag: false,
            ),
          ),
        ),
      );

      expect(find.text('Rejected (Citizen Reported)'), findsOneWidget);
    });

    testWidgets(
        'renders compact mode for Approved and Rejected even when showCitizenReportedTag is false',
        (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Column(
              children: [
                ApplicationStatusBadge(
                  status: 'Approved',
                  isCompact: true,
                  showCitizenReportedTag: false,
                ),
                ApplicationStatusBadge(
                  status: 'Rejected',
                  isCompact: true,
                  showCitizenReportedTag: false,
                ),
              ],
            ),
          ),
        ),
      );

      expect(find.text('Approved (Self-Reported)'), findsOneWidget);
      expect(find.text('Rejected (Self-Reported)'), findsOneWidget);
    });
  });

  group('ApplicationHistoryEventChip Tests', () {
    testWidgets('renders event types and source tag correctly', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Column(
              children: [
                ApplicationHistoryEventChip(
                  eventType: 'INITIAL_REGISTRATION',
                  source: 'USER_REPORTED',
                ),
                ApplicationHistoryEventChip(
                  eventType: 'STATUS_UPDATE',
                  source: 'SYSTEM_MIGRATION',
                ),
              ],
            ),
          ),
        ),
      );

      expect(find.text('Initial Registration'), findsOneWidget);
      expect(find.text('Citizen Reported'), findsOneWidget);
      expect(find.text('Status Update'), findsOneWidget);
      expect(find.text('System'), findsOneWidget);
    });
  });

  group('ApplicationDisclaimerCard Tests', () {
    testWidgets('renders default statutory boundary notice content',
        (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(body: ApplicationDisclaimerCard()),
        ),
      );

      expect(find.text('Application Tracking Notice'), findsOneWidget);
      expect(find.byIcon(Icons.shield_outlined), findsOneWidget);

      final textFinder = find.byType(Text);
      final allTexts = textFinder
          .evaluate()
          .map((e) => (e.widget as Text).data ?? '')
          .join(' ');

      // Product boundary assertions
      expect(allTexts, contains('not an official government portal'));
      expect(allTexts, contains('official government department websites'));
      expect(allTexts, contains('maintained by the citizen'));
      expect(allTexts,
          contains('does not independently verify, approve, or reject'));
    });

    testWidgets('renders custom text override when provided', (tester) async {
      const customMsg = 'Custom history ledger audit disclaimer note.';

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ApplicationDisclaimerCard(customText: customMsg),
          ),
        ),
      );

      expect(find.text(customMsg), findsOneWidget);
    });

    testWidgets('renders compact styling without overflow', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: ApplicationDisclaimerCard(isCompact: true),
          ),
        ),
      );

      expect(find.text('Application Tracking Notice'), findsOneWidget);
      expect(find.byIcon(Icons.shield_outlined), findsOneWidget);
    });
  });

  group('SchemePickerBottomSheet Tests', () {
    testWidgets('shows loading state while fetching schemes', (tester) async {
      final completer = Completer<SchemeListResponseModel>();

      final fakeService = FakeSchemeService(
        onGetSchemes: ({category, page = 1, pageSize = 20, query, state}) =>
            completer.future,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SchemePickerBottomSheet(schemeService: fakeService),
          ),
        ),
      );

      // Verify progress indicator is rendered before completer resolves
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.text('Searching welfare schemes...'), findsOneWidget);

      // Clean up async completer to avoid hanging test
      completer.complete(SchemeListResponseModel(
        items: [],
        total: 0,
        page: 1,
        pageSize: 30,
        totalPages: 0,
      ));
      await tester.pumpAndSettle();
    });

    testWidgets('renders scheme list and pops selected scheme on tap',
        (tester) async {
      final fakeService = FakeSchemeService(
        onGetSchemes: (
            {category, page = 1, pageSize = 20, query, state}) async {
          return SchemeListResponseModel(
            items: [sampleScheme],
            total: 1,
            page: 1,
            pageSize: 30,
            totalPages: 1,
          );
        },
      );

      SchemeModel? selectedResult;

      await tester.pumpWidget(
        MaterialApp(
          home: Builder(builder: (context) {
            return Scaffold(
              body: ElevatedButton(
                onPressed: () async {
                  selectedResult = await SchemePickerBottomSheet.show(
                    context,
                    schemeService: fakeService,
                  );
                },
                child: const Text('Open Picker'),
              ),
            );
          }),
        ),
      );

      // Tap button to open bottom sheet
      await tester.tap(find.text('Open Picker'));
      await tester.pumpAndSettle();

      // Verify scheme is displayed
      expect(find.text('Select Government Scheme'), findsOneWidget);
      expect(find.text('Pradhan Mantri Kisan Samman Nidhi'), findsOneWidget);
      expect(find.text('Ministry of Agriculture'), findsOneWidget);
      expect(find.text('Agriculture'), findsOneWidget);

      // Tap the scheme item
      await tester.tap(find.text('Pradhan Mantri Kisan Samman Nidhi'));
      await tester.pumpAndSettle();

      // Verify bottom sheet closed and returned selected scheme
      expect(find.text('Select Government Scheme'), findsNothing);
      expect(selectedResult, isNotNull);
      expect(selectedResult?.id, sampleScheme.id);
      expect(selectedResult?.schemeName, sampleScheme.schemeName);
    });

    testWidgets('renders empty state when search returns no schemes',
        (tester) async {
      final fakeService = FakeSchemeService(
        onGetSchemes: (
            {category, page = 1, pageSize = 20, query, state}) async {
          return SchemeListResponseModel(
            items: [],
            total: 0,
            page: 1,
            pageSize: 30,
            totalPages: 0,
          );
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SchemePickerBottomSheet(schemeService: fakeService),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('No schemes found'), findsOneWidget);
      expect(find.byIcon(Icons.search_off_rounded), findsOneWidget);
    });

    testWidgets('renders error state and retries on button press',
        (tester) async {
      int callCount = 0;

      final fakeService = FakeSchemeService(
        onGetSchemes: (
            {category, page = 1, pageSize = 20, query, state}) async {
          callCount++;
          if (callCount == 1) {
            throw Exception('Connection failed');
          }
          return SchemeListResponseModel(
            items: [sampleScheme],
            total: 1,
            page: 1,
            pageSize: 30,
            totalPages: 1,
          );
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SchemePickerBottomSheet(schemeService: fakeService),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Expect error state
      expect(find.text('Connection failed'), findsOneWidget);
      expect(find.byIcon(Icons.error_outline_rounded), findsOneWidget);
      expect(find.text('Try Again'), findsOneWidget);

      // Press retry
      await tester.tap(find.text('Try Again'));
      await tester.pumpAndSettle();

      // Expect successful recovery
      expect(callCount, 2);
      expect(find.text('Pradhan Mantri Kisan Samman Nidhi'), findsOneWidget);
    });

    testWidgets('debounces search queries properly', (tester) async {
      String? lastQuery;

      final fakeService = FakeSchemeService(
        onGetSchemes: (
            {category, page = 1, pageSize = 20, query, state}) async {
          lastQuery = query;
          return SchemeListResponseModel(
            items: [sampleScheme],
            total: 1,
            page: 1,
            pageSize: 30,
            totalPages: 1,
          );
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SchemePickerBottomSheet(schemeService: fakeService),
          ),
        ),
      );

      await tester.pumpAndSettle();
      expect(lastQuery, isNull); // Initial load with empty query

      // Enter search text
      await tester.enterText(find.byType(TextField), 'scholarship');

      // Before debounce duration (350ms), service should not have been called with new query yet
      await tester.pump(const Duration(milliseconds: 100));
      expect(lastQuery, isNull);

      // After debounce duration passes
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pumpAndSettle();
      expect(lastQuery, 'scholarship');
    });
  });
}
