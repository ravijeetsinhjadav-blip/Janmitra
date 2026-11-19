import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:janmitra_assist/features/applications/models/application_models.dart';
import 'package:janmitra_assist/features/applications/presentation/screens/applications_list_screen.dart';
import 'package:janmitra_assist/features/applications/presentation/widgets/application_card.dart';
import 'package:janmitra_assist/features/applications/presentation/widgets/application_disclaimer_card.dart';
import 'package:janmitra_assist/features/applications/presentation/widgets/application_status_badge.dart';
import 'package:janmitra_assist/features/applications/services/application_service.dart';
import 'package:janmitra_assist/features/home/presentation/screens/home_screen.dart';

/// Fake ApplicationService for deterministic list and pagination widget testing
class FakeApplicationService implements ApplicationService {
  final Future<ApplicationListResponseModel> Function({
    String? status,
    String? schemeId,
    int page,
    int pageSize,
  }) onGetApplications;

  FakeApplicationService({required this.onGetApplications});

  @override
  Future<ApplicationListResponseModel> getApplications({
    String? status,
    String? schemeId,
    int page = 1,
    int pageSize = 20,
  }) {
    return onGetApplications(
      status: status,
      schemeId: schemeId,
      page: page,
      pageSize: pageSize,
    );
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  final sampleApp1 = ApplicationModel(
    id: '11111111-1111-1111-1111-111111111111',
    userId: 'user-1',
    schemeId: 'scheme-1',
    schemeName: 'Pradhan Mantri Kisan Samman Nidhi',
    category: 'Agriculture',
    department: 'Ministry of Agriculture',
    applicationReferenceNumber: 'PMK-2026-001',
    submissionDate: DateTime.utc(2026, 10, 25),
    status: 'Submitted',
    createdAt: DateTime.utc(2026, 10, 25),
    updatedAt: DateTime.utc(2026, 10, 25),
  );

  final sampleApp2 = ApplicationModel(
    id: '22222222-2222-2222-2222-222222222222',
    userId: 'user-1',
    schemeId: 'scheme-2',
    schemeName: 'Post-Matric Scholarship Scheme',
    category: null,
    department: null,
    applicationReferenceNumber: null,
    submissionDate: null,
    status: 'Approved',
    createdAt: DateTime.utc(2026, 10, 26),
    updatedAt: DateTime.utc(2026, 10, 26),
  );

  final sampleApp3 = ApplicationModel(
    id: '33333333-3333-3333-3333-333333333333',
    userId: 'user-1',
    schemeId: 'scheme-3',
    schemeName: 'National Health Mission Assistance',
    category: 'Healthcare',
    department: 'Ministry of Health and Family Welfare',
    applicationReferenceNumber: 'NHM-999',
    submissionDate: DateTime.utc(2026, 10, 27),
    status: 'Rejected',
    createdAt: DateTime.utc(2026, 10, 27),
    updatedAt: DateTime.utc(2026, 10, 27),
  );

  group('ApplicationsListScreen Widget & Presentation Tests', () {
    testWidgets('shows loading indicator while fetching applications',
        (tester) async {
      final completer = Completer<ApplicationListResponseModel>();

      final fakeService = FakeApplicationService(
        onGetApplications: ({page = 1, pageSize = 20, schemeId, status}) =>
            completer.future,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationsListScreen(applicationService: fakeService),
        ),
      );

      expect(find.byType(CircularProgressIndicator), findsOneWidget);

      completer.complete(ApplicationListResponseModel(
        total: 0,
        page: 1,
        pageSize: 20,
        totalPages: 0,
        applications: [],
      ));
      await tester.pumpAndSettle();
    });

    testWidgets(
        'renders successful list with scheme names, categories, and disclaimers',
        (tester) async {
      final fakeService = FakeApplicationService(
        onGetApplications: ({page = 1, pageSize = 20, schemeId, status}) async {
          return ApplicationListResponseModel(
            total: 2,
            page: 1,
            pageSize: 20,
            totalPages: 1,
            applications: [sampleApp1, sampleApp2],
          );
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationsListScreen(applicationService: fakeService),
        ),
      );

      await tester.pumpAndSettle();

      // Top disclaimer banner
      expect(find.byType(ApplicationDisclaimerCard), findsOneWidget);

      // Scheme details
      expect(find.text('Pradhan Mantri Kisan Samman Nidhi'), findsOneWidget);
      expect(find.text('Agriculture'), findsOneWidget);
      expect(find.text('Ministry of Agriculture'), findsOneWidget);
      expect(find.text('Post-Matric Scholarship Scheme'), findsOneWidget);

      // Application cards
      expect(find.byType(ApplicationCard), findsNWidgets(2));
    });

    testWidgets(
        'renders reference number and missing reference fallback correctly',
        (tester) async {
      final fakeService = FakeApplicationService(
        onGetApplications: ({page = 1, pageSize = 20, schemeId, status}) async {
          return ApplicationListResponseModel(
            total: 2,
            page: 1,
            pageSize: 20,
            totalPages: 1,
            applications: [sampleApp1, sampleApp2],
          );
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationsListScreen(applicationService: fakeService),
        ),
      );

      await tester.pumpAndSettle();

      // Given reference number
      expect(find.text('PMK-2026-001'), findsOneWidget);

      // Missing reference fallback
      expect(find.text('Ref: Not Issued'), findsOneWidget);
    });

    testWidgets('renders submission date and null-date fallback correctly',
        (tester) async {
      final fakeService = FakeApplicationService(
        onGetApplications: ({page = 1, pageSize = 20, schemeId, status}) async {
          return ApplicationListResponseModel(
            total: 2,
            page: 1,
            pageSize: 20,
            totalPages: 1,
            applications: [sampleApp1, sampleApp2],
          );
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationsListScreen(applicationService: fakeService),
        ),
      );

      await tester.pumpAndSettle();

      // Formatted date for sampleApp1 (25 Oct 2026)
      expect(find.text('25 Oct 2026'), findsOneWidget);

      // Null date fallback for sampleApp2
      expect(find.text('Date: Not Recorded'), findsOneWidget);
    });

    testWidgets(
        'renders citizen-reported qualification on Approved and Rejected status badges',
        (tester) async {
      final fakeService = FakeApplicationService(
        onGetApplications: ({page = 1, pageSize = 20, schemeId, status}) async {
          return ApplicationListResponseModel(
            total: 3,
            page: 1,
            pageSize: 20,
            totalPages: 1,
            applications: [sampleApp1, sampleApp2, sampleApp3],
          );
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationsListScreen(applicationService: fakeService),
        ),
      );

      await tester.pumpAndSettle();

      // Submitted (in status badge)
      expect(
        find.descendant(
          of: find.byType(ApplicationStatusBadge),
          matching: find.text('Submitted'),
        ),
        findsOneWidget,
      );

      // Approved (Self-Reported in compact card badge)
      expect(find.text('Approved (Self-Reported)'), findsOneWidget);

      // Scroll to reveal the 3rd card (Rejected)
      await tester.drag(
        find.byKey(const Key('applications_list_view')),
        const Offset(0, -200),
      );
      await tester.pumpAndSettle();

      // Rejected (Self-Reported in compact card badge)
      expect(find.text('Rejected (Self-Reported)'), findsOneWidget);
    });

    testWidgets(
        'filters applications by status and executes correct service query',
        (tester) async {
      String? queriedStatus;

      final fakeService = FakeApplicationService(
        onGetApplications: ({page = 1, pageSize = 20, schemeId, status}) async {
          queriedStatus = status;
          if (status == 'Approved') {
            return ApplicationListResponseModel(
              total: 1,
              page: 1,
              pageSize: 20,
              totalPages: 1,
              applications: [sampleApp2],
            );
          }
          return ApplicationListResponseModel(
            total: 3,
            page: 1,
            pageSize: 20,
            totalPages: 1,
            applications: [sampleApp1, sampleApp2, sampleApp3],
          );
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationsListScreen(applicationService: fakeService),
        ),
      );

      await tester.pumpAndSettle();
      expect(queriedStatus, isNull); // Initial 'All' filter

      // Scroll horizontal status filter bar to reveal 'Approved'
      await tester.drag(
        find.byKey(const Key('status_filter_list_view')),
        const Offset(-250, 0),
      );
      await tester.pumpAndSettle();

      final approvedChipFinder = find.widgetWithText(ChoiceChip, 'Approved');
      expect(approvedChipFinder, findsOneWidget);
      await tester.tap(approvedChipFinder);
      await tester.pumpAndSettle();

      expect(queriedStatus, 'Approved');
      expect(find.byType(ApplicationCard), findsOneWidget);
      expect(find.text('Post-Matric Scholarship Scheme'), findsOneWidget);
    });

    testWidgets(
        'renders global empty state when citizen has no tracked applications',
        (tester) async {
      final fakeService = FakeApplicationService(
        onGetApplications: ({page = 1, pageSize = 20, schemeId, status}) async {
          return ApplicationListResponseModel(
            total: 0,
            page: 1,
            pageSize: 20,
            totalPages: 0,
            applications: [],
          );
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationsListScreen(applicationService: fakeService),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('No Tracked Applications Yet'), findsOneWidget);
      expect(find.text('Track Your First Application'), findsOneWidget);
    });

    testWidgets('renders filter-specific empty state with clear filter button',
        (tester) async {
      String? queriedStatus;

      final fakeService = FakeApplicationService(
        onGetApplications: ({page = 1, pageSize = 20, schemeId, status}) async {
          queriedStatus = status;
          if (status == 'Document Verification') {
            return ApplicationListResponseModel(
              total: 0,
              page: 1,
              pageSize: 20,
              totalPages: 0,
              applications: [],
            );
          }
          return ApplicationListResponseModel(
            total: 1,
            page: 1,
            pageSize: 20,
            totalPages: 1,
            applications: [sampleApp1],
          );
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationsListScreen(applicationService: fakeService),
        ),
      );

      await tester.pumpAndSettle();

      // Tap filter with 0 items
      await tester.tap(find.text('Document Verification'));
      await tester.pumpAndSettle();

      expect(queriedStatus, 'Document Verification');
      expect(find.text('No Applications Found'), findsOneWidget);
      expect(find.text('Show All Applications'), findsOneWidget);

      // Tap 'Show All Applications'
      await tester.tap(find.text('Show All Applications'));
      await tester.pumpAndSettle();

      expect(queriedStatus, isNull); // Reset to 'All'
      expect(find.byType(ApplicationCard), findsOneWidget);
    });

    testWidgets(
        'renders error state on network failure and retries on button press',
        (tester) async {
      int attemptCount = 0;

      final fakeService = FakeApplicationService(
        onGetApplications: ({page = 1, pageSize = 20, schemeId, status}) async {
          attemptCount++;
          if (attemptCount == 1) {
            throw Exception('Connection timed out');
          }
          return ApplicationListResponseModel(
            total: 1,
            page: 1,
            pageSize: 20,
            totalPages: 1,
            applications: [sampleApp1],
          );
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationsListScreen(applicationService: fakeService),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Connection timed out'), findsOneWidget);
      expect(find.text('Try Again'), findsOneWidget);

      // Press retry
      await tester.tap(find.text('Try Again'));
      await tester.pumpAndSettle();

      expect(attemptCount, 2);
      expect(find.byType(ApplicationCard), findsOneWidget);
      expect(find.text('Pradhan Mantri Kisan Samman Nidhi'), findsOneWidget);
    });

    testWidgets('pull-to-refresh reloads applications from page 1',
        (tester) async {
      int callCount = 0;

      final fakeService = FakeApplicationService(
        onGetApplications: ({page = 1, pageSize = 20, schemeId, status}) async {
          callCount++;
          return ApplicationListResponseModel(
            total: 1,
            page: 1,
            pageSize: 20,
            totalPages: 1,
            applications: [sampleApp1],
          );
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationsListScreen(applicationService: fakeService),
        ),
      );

      await tester.pumpAndSettle();
      expect(callCount, 1);

      // Trigger pull to refresh gesture on the vertical applications list
      await tester.fling(
        find.byKey(const Key('applications_list_view')),
        const Offset(0, 300),
        1000,
      );
      await tester.pumpAndSettle();

      expect(callCount, greaterThanOrEqualTo(2));
    });

    testWidgets('invokes onAddApplication callback when FAB is tapped',
        (tester) async {
      bool addTapped = false;

      final fakeService = FakeApplicationService(
        onGetApplications: ({page = 1, pageSize = 20, schemeId, status}) async {
          return ApplicationListResponseModel(
            total: 1,
            page: 1,
            pageSize: 20,
            totalPages: 1,
            applications: [sampleApp1],
          );
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationsListScreen(
            applicationService: fakeService,
            onAddApplication: () {
              addTapped = true;
            },
          ),
        ),
      );

      await tester.pumpAndSettle();

      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();

      expect(addTapped, isTrue);
    });

    testWidgets(
        'invokes onApplicationTap callback with application model when tapped',
        (tester) async {
      ApplicationModel? tappedApp;

      final fakeService = FakeApplicationService(
        onGetApplications: ({page = 1, pageSize = 20, schemeId, status}) async {
          return ApplicationListResponseModel(
            total: 1,
            page: 1,
            pageSize: 20,
            totalPages: 1,
            applications: [sampleApp1],
          );
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationsListScreen(
            applicationService: fakeService,
            onApplicationTap: (app) {
              tappedApp = app;
            },
          ),
        ),
      );

      await tester.pumpAndSettle();

      await tester.tap(find.byType(ApplicationCard));
      await tester.pumpAndSettle();

      expect(tappedApp, isNotNull);
      expect(tappedApp?.id, sampleApp1.id);
      expect(tappedApp?.schemeName, sampleApp1.schemeName);
    });
  });

  group('Pagination & Load-More Tests', () {
    testWidgets('loads next page and prevents duplicates on scroll',
        (tester) async {
      final requestedPages = <int>[];

      final fakeService = FakeApplicationService(
        onGetApplications: ({page = 1, pageSize = 20, schemeId, status}) async {
          requestedPages.add(page);
          if (page == 1) {
            return ApplicationListResponseModel(
              total: 3,
              page: 1,
              pageSize: 2,
              totalPages: 2,
              applications: [sampleApp1, sampleApp2],
            );
          } else {
            return ApplicationListResponseModel(
              total: 3,
              page: 2,
              pageSize: 2,
              totalPages: 2,
              applications: [sampleApp3],
            );
          }
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationsListScreen(applicationService: fakeService),
        ),
      );

      await tester.pumpAndSettle();
      expect(requestedPages, [1]);
      expect(find.byType(ApplicationCard), findsNWidgets(2));

      // Scroll to trigger load more
      await tester.drag(
        find.byKey(const Key('applications_list_view')),
        const Offset(0, -300),
      );
      await tester.pumpAndSettle();

      expect(requestedPages, contains(2));
      expect(find.byType(ApplicationCard), findsNWidgets(3));
      expect(find.text('National Health Mission Assistance'), findsOneWidget);
    });

    testWidgets('does not request further pages when final page is reached',
        (tester) async {
      int requestCount = 0;

      final fakeService = FakeApplicationService(
        onGetApplications: ({page = 1, pageSize = 20, schemeId, status}) async {
          requestCount++;
          return ApplicationListResponseModel(
            total: 1,
            page: 1,
            pageSize: 20,
            totalPages: 1,
            applications: [sampleApp1],
          );
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationsListScreen(applicationService: fakeService),
        ),
      );

      await tester.pumpAndSettle();
      expect(requestCount, 1);

      // Scroll attempt when already on page 1 of 1
      await tester.drag(
        find.byKey(const Key('applications_list_view')),
        const Offset(0, -300),
      );
      await tester.pumpAndSettle();

      expect(requestCount, 1);
    });
  });

  group('Stale Request & Race Condition Protection Tests', () {
    testWidgets(
        'newer filter response displays even if older filter response completes later',
        (tester) async {
      final initialCompleter = Completer<ApplicationListResponseModel>();
      final submittedCompleter = Completer<ApplicationListResponseModel>();
      final approvedCompleter = Completer<ApplicationListResponseModel>();

      final fakeService = FakeApplicationService(
        onGetApplications: ({page = 1, pageSize = 20, schemeId, status}) {
          if (status == 'Submitted') {
            return submittedCompleter.future;
          } else if (status == 'Approved') {
            return approvedCompleter.future;
          }
          return initialCompleter.future;
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationsListScreen(applicationService: fakeService),
        ),
      );

      // Complete initial load
      initialCompleter.complete(ApplicationListResponseModel(
        total: 1,
        page: 1,
        pageSize: 20,
        totalPages: 1,
        applications: [sampleApp1],
      ));
      await tester.pumpAndSettle();

      // Tap 'Submitted' filter
      await tester.tap(find.widgetWithText(ChoiceChip, 'Submitted'));
      await tester.pump(); // Request for Submitted is in-flight

      // Scroll horizontal bar and tap 'Approved' filter
      await tester.drag(
        find.byKey(const Key('status_filter_list_view')),
        const Offset(-250, 0),
      );
      await tester.pump(const Duration(milliseconds: 100));
      await tester.tap(find.widgetWithText(ChoiceChip, 'Approved'));
      await tester.pump(); // Request for Approved is now in-flight

      // Approved completes first
      approvedCompleter.complete(ApplicationListResponseModel(
        total: 1,
        page: 1,
        pageSize: 20,
        totalPages: 1,
        applications: [sampleApp2],
      ));
      await tester.pumpAndSettle();

      // Verified Approved data is displayed
      expect(find.text('Post-Matric Scholarship Scheme'), findsOneWidget);
      expect(find.text('Pradhan Mantri Kisan Samman Nidhi'), findsNothing);

      // Now Submitted (the older request) completes later
      submittedCompleter.complete(ApplicationListResponseModel(
        total: 1,
        page: 1,
        pageSize: 20,
        totalPages: 1,
        applications: [sampleApp1],
      ));
      await tester.pumpAndSettle();

      // Verify that Approved data remains displayed and was NOT overwritten by late Submitted response
      expect(find.text('Post-Matric Scholarship Scheme'), findsOneWidget);
      expect(find.text('Pradhan Mantri Kisan Samman Nidhi'), findsNothing);
    });

    testWidgets(
        'older request completing does not dismiss loading indicator while newer request is pending',
        (tester) async {
      final initialCompleter = Completer<ApplicationListResponseModel>();
      final submittedCompleter = Completer<ApplicationListResponseModel>();
      final approvedCompleter = Completer<ApplicationListResponseModel>();

      final fakeService = FakeApplicationService(
        onGetApplications: ({page = 1, pageSize = 20, schemeId, status}) {
          if (status == 'Submitted') {
            return submittedCompleter.future;
          } else if (status == 'Approved') {
            return approvedCompleter.future;
          }
          return initialCompleter.future;
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationsListScreen(applicationService: fakeService),
        ),
      );

      // Complete initial load
      initialCompleter.complete(ApplicationListResponseModel(
        total: 1,
        page: 1,
        pageSize: 20,
        totalPages: 1,
        applications: [sampleApp1],
      ));
      await tester.pumpAndSettle();

      // Tap 'Submitted'
      await tester.tap(find.widgetWithText(ChoiceChip, 'Submitted'));
      await tester.pump();

      // Scroll bar and tap 'Approved'
      await tester.drag(
        find.byKey(const Key('status_filter_list_view')),
        const Offset(-250, 0),
      );
      await tester.pump(const Duration(milliseconds: 100));
      await tester.tap(find.widgetWithText(ChoiceChip, 'Approved'));
      await tester.pump();

      // Older request (Submitted) completes while newer request (Approved) is still pending
      submittedCompleter.complete(ApplicationListResponseModel(
        total: 1,
        page: 1,
        pageSize: 20,
        totalPages: 1,
        applications: [sampleApp1],
      ));
      await tester.pump();

      // Screen must still be loading because Approved is still pending
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.byType(ApplicationCard), findsNothing);

      // Now Approved completes
      approvedCompleter.complete(ApplicationListResponseModel(
        total: 1,
        page: 1,
        pageSize: 20,
        totalPages: 1,
        applications: [sampleApp2],
      ));
      await tester.pumpAndSettle();

      // Screen is no longer loading and shows Approved data
      expect(find.byType(CircularProgressIndicator), findsNothing);
      expect(find.text('Post-Matric Scholarship Scheme'), findsOneWidget);
    });

    testWidgets(
        'filter change discards in-flight load-more pagination response',
        (tester) async {
      final loadMoreCompleter = Completer<ApplicationListResponseModel>();

      final fakeService = FakeApplicationService(
        onGetApplications: ({page = 1, pageSize = 20, schemeId, status}) async {
          if (status == null && page == 1) {
            return ApplicationListResponseModel(
              total: 3,
              page: 1,
              pageSize: 2,
              totalPages: 2,
              applications: [sampleApp1, sampleApp2],
            );
          } else if (status == null && page == 2) {
            // Load more in flight
            return loadMoreCompleter.future;
          } else if (status == 'Rejected') {
            return ApplicationListResponseModel(
              total: 1,
              page: 1,
              pageSize: 20,
              totalPages: 1,
              applications: [sampleApp3],
            );
          }
          return ApplicationListResponseModel(
            total: 0,
            page: 1,
            pageSize: 20,
            totalPages: 0,
            applications: [],
          );
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationsListScreen(applicationService: fakeService),
        ),
      );

      await tester.pumpAndSettle();
      expect(find.byType(ApplicationCard), findsNWidgets(2));

      // Trigger scroll to start load more
      await tester.drag(
        find.byKey(const Key('applications_list_view')),
        const Offset(0, -300),
      );
      await tester.pump(); // load-more request is now pending

      // User changes filter to 'Rejected' while load-more is still pending
      await tester.drag(
        find.byKey(const Key('status_filter_list_view')),
        const Offset(-350, 0),
      );
      await tester.pump(const Duration(milliseconds: 100));
      await tester.tap(find.widgetWithText(ChoiceChip, 'Rejected'));
      await tester.pumpAndSettle();

      // Screen now displays 'Rejected' filter with sampleApp3
      expect(find.text('National Health Mission Assistance'), findsOneWidget);
      expect(find.byType(ApplicationCard), findsOneWidget);

      // The old load-more response completes
      loadMoreCompleter.complete(ApplicationListResponseModel(
        total: 3,
        page: 2,
        pageSize: 2,
        totalPages: 2,
        applications: [sampleApp1], // old item
      ));
      await tester.pumpAndSettle();

      // Verify that the old load-more item was NOT appended to the new filter
      expect(find.byType(ApplicationCard), findsOneWidget);
      expect(find.text('National Health Mission Assistance'), findsOneWidget);
      expect(find.text('Pradhan Mantri Kisan Samman Nidhi'), findsNothing);
    });

    testWidgets('refresh invalidates earlier outstanding request',
        (tester) async {
      final initialCompleter = Completer<ApplicationListResponseModel>();
      final refreshCompleter = Completer<ApplicationListResponseModel>();
      int callCount = 0;

      final fakeService = FakeApplicationService(
        onGetApplications: ({page = 1, pageSize = 20, schemeId, status}) {
          callCount++;
          if (callCount == 1) {
            return initialCompleter.future;
          }
          return refreshCompleter.future;
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationsListScreen(applicationService: fakeService),
        ),
      );

      expect(find.byType(CircularProgressIndicator), findsOneWidget);

      // Trigger refresh via AppBar refresh action while initial request is pending
      await tester.tap(find.byTooltip('Refresh Applications'));
      await tester.pump();

      // Complete initial (invalidated) request
      initialCompleter.complete(ApplicationListResponseModel(
        total: 1,
        page: 1,
        pageSize: 20,
        totalPages: 1,
        applications: [sampleApp1],
      ));
      await tester.pump();

      // Should still be loading because the refresh request is active
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.byType(ApplicationCard), findsNothing);

      // Complete refresh request with updated data
      refreshCompleter.complete(ApplicationListResponseModel(
        total: 1,
        page: 1,
        pageSize: 20,
        totalPages: 1,
        applications: [sampleApp2],
      ));
      await tester.pumpAndSettle();

      // Display updated data from refresh
      expect(find.text('Post-Matric Scholarship Scheme'), findsOneWidget);
      expect(find.text('Pradhan Mantri Kisan Samman Nidhi'), findsNothing);
    });

    testWidgets(
        'refresh discards in-flight pagination request, clears pagination loading indicator, and allows subsequent pagination',
        (tester) async {
      final oldLoadMoreCompleter = Completer<ApplicationListResponseModel>();
      final refreshCompleter = Completer<ApplicationListResponseModel>();
      final newLoadMoreCompleter = Completer<ApplicationListResponseModel>();
      final requestedPages = <int>[];
      int page1Calls = 0;
      int page2Calls = 0;

      final fakeService = FakeApplicationService(
        onGetApplications: ({page = 1, pageSize = 20, schemeId, status}) {
          requestedPages.add(page);
          if (page == 1) {
            page1Calls++;
            if (page1Calls == 1) {
              // Initial load
              return Future.value(ApplicationListResponseModel(
                total: 4,
                page: 1,
                pageSize: 2,
                totalPages: 2,
                applications: [sampleApp1, sampleApp2],
              ));
            } else {
              // Refresh in flight
              return refreshCompleter.future;
            }
          } else {
            page2Calls++;
            if (page2Calls == 1) {
              // In-flight old load more
              return oldLoadMoreCompleter.future;
            } else {
              // Subsequent load more after refresh
              return newLoadMoreCompleter.future;
            }
          }
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationsListScreen(applicationService: fakeService),
        ),
      );

      await tester.pumpAndSettle();
      expect(find.byType(ApplicationCard), findsNWidgets(2));
      expect(requestedPages, [1]);

      // 1. Trigger load more for page 2
      await tester.drag(
        find.byKey(const Key('applications_list_view')),
        const Offset(0, -300),
      );
      await tester.pump(); // load-more request is in-flight

      expect(requestedPages, [1, 2]);
      // Verify pagination loading indicator is visible at list bottom
      expect(find.byKey(const Key('pagination_loading_indicator')),
          findsOneWidget);

      // 2. While pagination is in-flight, trigger refresh via AppBar action
      await tester.tap(find.byTooltip('Refresh Applications'));
      await tester.pump();

      // Verify pagination loading indicator at bottom was immediately cleared by refresh start
      expect(
          find.byKey(const Key('pagination_loading_indicator')), findsNothing);

      // 3. Complete the old obsolete load-more request
      oldLoadMoreCompleter.complete(ApplicationListResponseModel(
        total: 4,
        page: 2,
        pageSize: 2,
        totalPages: 2,
        applications: [sampleApp3], // should be discarded
      ));
      await tester.pump();

      // Old pagination data must NOT be present
      expect(find.text('National Health Mission Assistance'), findsNothing);

      // 4. Complete the refresh request with a fresh page 1 of 2
      refreshCompleter.complete(ApplicationListResponseModel(
        total: 4,
        page: 1,
        pageSize: 2,
        totalPages: 2,
        applications: [sampleApp1, sampleApp2],
      ));
      await tester.pumpAndSettle();

      // Verified refresh replaced application list with page 1 items
      expect(find.byType(ApplicationCard), findsNWidgets(2));
      expect(find.text('Pradhan Mantri Kisan Samman Nidhi'), findsOneWidget);
      expect(find.text('Post-Matric Scholarship Scheme'), findsOneWidget);
      expect(find.text('National Health Mission Assistance'), findsNothing);
      expect(
          find.byKey(const Key('pagination_loading_indicator')), findsNothing);

      // 5. Verify pagination can be triggered AGAIN after refresh succeeds
      // Move scroll offset slightly up (without reaching 0 to avoid triggering pull-to-refresh),
      // then scroll down to the bottom threshold.
      await tester.drag(
        find.byKey(const Key('applications_list_view')),
        const Offset(0, 50),
      );
      await tester.pump();

      await tester.drag(
        find.byKey(const Key('applications_list_view')),
        const Offset(0, -50),
      );
      await tester.pump(); // new load-more request is in-flight

      // Verify page 2 was requested again after refresh
      expect(requestedPages, [1, 2, 1, 2]);
      expect(find.byKey(const Key('pagination_loading_indicator')),
          findsOneWidget);

      // Complete subsequent load-more
      newLoadMoreCompleter.complete(ApplicationListResponseModel(
        total: 4,
        page: 2,
        pageSize: 2,
        totalPages: 2,
        applications: [sampleApp3],
      ));
      await tester.pumpAndSettle();

      // All 3 items rendered successfully
      expect(find.byType(ApplicationCard), findsNWidgets(3));
      expect(find.text('National Health Mission Assistance'), findsOneWidget);
      expect(
          find.byKey(const Key('pagination_loading_indicator')), findsNothing);
    });

    testWidgets('pagination loading state is cleared when refresh fails',
        (tester) async {
      final oldLoadMoreCompleter = Completer<ApplicationListResponseModel>();
      final refreshCompleter = Completer<ApplicationListResponseModel>();
      int page1Calls = 0;

      final fakeService = FakeApplicationService(
        onGetApplications: ({page = 1, pageSize = 20, schemeId, status}) {
          if (page == 1) {
            page1Calls++;
            if (page1Calls == 1) {
              return Future.value(ApplicationListResponseModel(
                total: 4,
                page: 1,
                pageSize: 2,
                totalPages: 2,
                applications: [sampleApp1, sampleApp2],
              ));
            } else {
              return refreshCompleter.future;
            }
          } else {
            return oldLoadMoreCompleter.future;
          }
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationsListScreen(applicationService: fakeService),
        ),
      );

      await tester.pumpAndSettle();
      expect(find.byType(ApplicationCard), findsNWidgets(2));

      // Trigger load more
      await tester.drag(
        find.byKey(const Key('applications_list_view')),
        const Offset(0, -300),
      );
      await tester.pump();
      expect(find.byKey(const Key('pagination_loading_indicator')),
          findsOneWidget);

      // Trigger refresh via AppBar action
      await tester.tap(find.byTooltip('Refresh Applications'));
      await tester.pump();
      expect(
          find.byKey(const Key('pagination_loading_indicator')), findsNothing);

      // Old load more completes
      oldLoadMoreCompleter.complete(ApplicationListResponseModel(
        total: 4,
        page: 2,
        pageSize: 2,
        totalPages: 2,
        applications: [sampleApp3],
      ));
      await tester.pump();

      // Refresh fails with network error
      refreshCompleter.completeError(Exception('Server unreachable'));
      await tester.pumpAndSettle();

      // Error view rendered and pagination loading indicator is cleared
      expect(find.text('Server unreachable'), findsOneWidget);
      expect(find.text('Try Again'), findsOneWidget);
      expect(
          find.byKey(const Key('pagination_loading_indicator')), findsNothing);
    });
  });

  group('HomeScreen Integration Tests', () {
    testWidgets(
        'HomeScreen renders active Track Government Applications card and navigates',
        (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: HomeScreen(),
        ),
      );

      await tester.pumpAndSettle();

      // Scroll down to find the Application Tracking section
      final trackingTitleFinder =
          find.text('Application Tracking & Status History');
      await tester.scrollUntilVisible(
        trackingTitleFinder,
        500,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.pumpAndSettle();

      expect(trackingTitleFinder, findsOneWidget);
      expect(find.text('Track Government Applications'), findsOneWidget);

      // Tap "Track Government Applications" button
      await tester.tap(find.text('Track Government Applications'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));

      // Verify navigated to ApplicationsListScreen
      expect(find.byType(ApplicationsListScreen), findsOneWidget);
      expect(find.text('My Applications'), findsOneWidget);
    });
  });
}
