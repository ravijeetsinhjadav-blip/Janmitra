import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:janmitra_assist/features/applications/models/application_models.dart';
import 'package:janmitra_assist/features/applications/presentation/screens/add_application_screen.dart';
import 'package:janmitra_assist/features/applications/presentation/screens/application_detail_screen.dart';
import 'package:janmitra_assist/features/applications/presentation/widgets/application_status_badge.dart';
import 'package:janmitra_assist/features/applications/services/application_service.dart';
import 'package:janmitra_assist/features/schemes/models/scheme_models.dart';
import 'package:janmitra_assist/features/schemes/services/scheme_service.dart';

class FakeApplicationService implements ApplicationService {
  final Future<ApplicationModel> Function(ApplicationCreateRequestModel)?
      onCreateApplication;
  final Future<ApplicationModel> Function(String)? onGetApplicationById;
  final Future<ApplicationModel> Function(
      String, ApplicationUpdateRequestModel)? onUpdateApplication;
  final Future<ApplicationDeleteResponseModel> Function(String)?
      onDeleteApplication;
  final Future<ApplicationStatusHistoryListModel> Function(String)?
      onGetApplicationHistory;
  final Future<ReminderListResponseModel> Function(String, {bool? isCompleted})?
      onGetApplicationReminders;
  final Future<ReminderModel> Function(String, ReminderCreateRequestModel)?
      onCreateReminder;
  final Future<ReminderModel> Function(
      String, String, ReminderUpdateRequestModel)? onUpdateReminder;
  final Future<ReminderDeleteResponseModel> Function(String, String)?
      onDeleteReminder;

  FakeApplicationService({
    this.onCreateApplication,
    this.onGetApplicationById,
    this.onUpdateApplication,
    this.onDeleteApplication,
    this.onGetApplicationHistory,
    this.onGetApplicationReminders,
    this.onCreateReminder,
    this.onUpdateReminder,
    this.onDeleteReminder,
  });

  @override
  Future<ApplicationModel> createApplication(
      ApplicationCreateRequestModel request) async {
    if (onCreateApplication != null) {
      return onCreateApplication!(request);
    }
    throw UnimplementedError();
  }

  @override
  Future<ApplicationModel> getApplicationById(String applicationId) async {
    if (onGetApplicationById != null) {
      return onGetApplicationById!(applicationId);
    }
    throw UnimplementedError();
  }

  @override
  Future<ApplicationModel> updateApplication(
      String applicationId, ApplicationUpdateRequestModel request) async {
    if (onUpdateApplication != null) {
      return onUpdateApplication!(applicationId, request);
    }
    throw UnimplementedError();
  }

  @override
  Future<ApplicationDeleteResponseModel> deleteApplication(
      String applicationId) async {
    if (onDeleteApplication != null) {
      return onDeleteApplication!(applicationId);
    }
    throw UnimplementedError();
  }

  @override
  Future<ApplicationStatusHistoryListModel> getApplicationHistory(
      String applicationId) async {
    if (onGetApplicationHistory != null) {
      return onGetApplicationHistory!(applicationId);
    }
    return ApplicationStatusHistoryListModel(
      applicationId: applicationId,
      currentStatus: 'Submitted',
      total: 0,
      history: [],
    );
  }

  @override
  Future<ReminderListResponseModel> getApplicationReminders(
      String applicationId,
      {bool? isCompleted}) async {
    if (onGetApplicationReminders != null) {
      return onGetApplicationReminders!(applicationId,
          isCompleted: isCompleted);
    }
    return ReminderListResponseModel(total: 0, reminders: []);
  }

  @override
  Future<ReminderModel> createReminder(
      String applicationId, ReminderCreateRequestModel request) async {
    if (onCreateReminder != null) {
      return onCreateReminder!(applicationId, request);
    }
    throw UnimplementedError();
  }

  @override
  Future<ReminderModel> updateReminder(String applicationId, String reminderId,
      ReminderUpdateRequestModel request) async {
    if (onUpdateReminder != null) {
      return onUpdateReminder!(applicationId, reminderId, request);
    }
    throw UnimplementedError();
  }

  @override
  Future<ReminderDeleteResponseModel> deleteReminder(
      String applicationId, String reminderId) async {
    if (onDeleteReminder != null) {
      return onDeleteReminder!(applicationId, reminderId);
    }
    throw UnimplementedError();
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class FakeSchemeService implements SchemeService {
  final Future<SchemeListResponseModel> Function({
    String? query,
    String? category,
    String? state,
    int page,
    int pageSize,
  })? onGetSchemes;

  FakeSchemeService({this.onGetSchemes});

  @override
  Future<SchemeListResponseModel> getSchemes({
    String? query,
    String? category,
    String? state,
    int page = 1,
    int pageSize = 20,
  }) async {
    if (onGetSchemes != null) {
      return onGetSchemes!(
        query: query,
        category: category,
        state: state,
        page: page,
        pageSize: pageSize,
      );
    }
    return SchemeListResponseModel(
      total: 0,
      page: 1,
      pageSize: 20,
      totalPages: 1,
      items: [],
    );
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  final sampleScheme = SchemeModel(
    id: 'scheme-uuid-1',
    schemeName: 'Pradhan Mantri Awas Yojana - Gramin',
    shortDescription: 'Housing assistance scheme for rural citizens',
    description: 'Detailed description',
    category: 'Housing',
    department: 'Ministry of Rural Development',
    stateApplicability: 'All India',
    eligibilitySummary: 'Rural households without pucca house',
    officialSourceUrl: 'https://pmayg.nic.in',
    officialApplicationUrl: 'https://pmayg.nic.in/apply',
    sourceVerificationDetails: 'Official gazette notification',
    sourceFreshnessStatus: 'Verified Official Source',
    status: 'active',
    isDemoData: true,
    benefits: ['Financial assistance of Rs 1.20 Lakh'],
    eligibilityCriteria: [],
    requiredProfileFields: [],
    applicationProcess: [],
    requiredDocuments: ['Aadhaar Card', 'Ration Card'],
  );

  final sampleApp = ApplicationModel(
    id: 'app-uuid-1',
    userId: 'user-uuid-1',
    schemeId: 'scheme-uuid-1',
    schemeName: 'Pradhan Mantri Awas Yojana - Gramin',
    category: 'Housing',
    department: 'Ministry of Rural Development',
    applicationReferenceNumber: 'PMAY-MH-2026-9921',
    submissionDate: DateTime.utc(2026, 10, 15),
    status: 'Submitted',
    createdAt: DateTime.utc(2026, 10, 15, 10, 0),
    updatedAt: DateTime.utc(2026, 10, 15, 10, 0),
    officialApplicationUrl: 'https://pmayg.nic.in/apply',
  );

  group('AddApplicationScreen Tests', () {
    testWidgets('renders form fields and validation errors when empty',
        (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: AddApplicationScreen(),
        ),
      );

      // Verify disclaimer card is present
      expect(find.byType(Card), findsWidgets);
      expect(find.text('Select Scheme from Catalog'), findsOneWidget);
      expect(find.byKey(const Key('reference_number_input')), findsOneWidget);
      expect(find.byKey(const Key('ref_not_issued_checkbox')), findsOneWidget);
      expect(
          find.byKey(const Key('submission_date_picker_tile')), findsOneWidget);
      expect(
          find.byKey(const Key('submit_application_button')), findsOneWidget);

      // Tap submit without selecting a scheme
      await tester
          .ensureVisible(find.byKey(const Key('submit_application_button')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('submit_application_button')));
      await tester.pumpAndSettle();

      expect(find.text('Please select a government scheme to track.'),
          findsOneWidget);
    });

    testWidgets('checking ref number not issued clears and disables input',
        (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: AddApplicationScreen(initialScheme: sampleScheme),
        ),
      );

      // Scheme is pre-selected
      expect(find.text('Pradhan Mantri Awas Yojana - Gramin'), findsOneWidget);

      // Enter a reference number
      await tester.enterText(
          find.byKey(const Key('reference_number_input')), 'REF-12345');
      await tester.pump();
      expect(find.text('REF-12345'), findsOneWidget);

      // Check "not yet issued" checkbox
      await tester.tap(find.byKey(const Key('ref_not_issued_checkbox')));
      await tester.pumpAndSettle();

      // Text input should be cleared
      expect(find.text('REF-12345'), findsNothing);
    });

    testWidgets('submits application successfully and pops with result',
        (tester) async {
      ApplicationCreateRequestModel? capturedRequest;

      final fakeService = FakeApplicationService(
        onCreateApplication: (req) async {
          capturedRequest = req;
          return sampleApp;
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: AddApplicationScreen(
            initialScheme: sampleScheme,
            applicationService: fakeService,
          ),
        ),
      );

      // Fill in reference number
      await tester.enterText(
          find.byKey(const Key('reference_number_input')), 'PMAY-MH-2026-9921');
      await tester.enterText(find.byKey(const Key('remarks_input')),
          'Submitted at CSC Kendra Pune');
      await tester.pump();

      // Submit
      await tester
          .ensureVisible(find.byKey(const Key('submit_application_button')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('submit_application_button')));
      await tester.pumpAndSettle();

      // Verify request payload
      expect(capturedRequest, isNotNull);
      expect(capturedRequest!.schemeId, 'scheme-uuid-1');
      expect(capturedRequest!.applicationReferenceNumber, 'PMAY-MH-2026-9921');
      expect(capturedRequest!.referenceNumberNotIssued, isFalse);
      expect(capturedRequest!.remarks, 'Submitted at CSC Kendra Pune');
    });
  });

  group('ApplicationDetailScreen Tests', () {
    testWidgets('renders application details with qualified status badge',
        (tester) async {
      final fakeService = FakeApplicationService(
        onGetApplicationById: (id) async => sampleApp,
        onGetApplicationHistory: (id) async =>
            ApplicationStatusHistoryListModel(
          applicationId: id,
          currentStatus: 'Submitted',
          total: 1,
          history: [
            ApplicationStatusHistoryModel(
              id: 'hist-1',
              applicationId: id,
              previousStatus: null,
              newStatus: 'Submitted',
              eventType: 'INITIAL_REGISTRATION',
              source: 'USER_REPORTED',
              remarks: 'Initial tracking created',
              changedByUserId: 'user-uuid-1',
              createdAt: DateTime.utc(2026, 10, 15, 10, 0),
            ),
          ],
        ),
        onGetApplicationReminders: (id, {isCompleted}) async =>
            ReminderListResponseModel(total: 0, reminders: []),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationDetailScreen(
            applicationId: 'app-uuid-1',
            initialApplication: sampleApp,
            applicationService: fakeService,
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Verify scheme name & status
      expect(find.text('Pradhan Mantri Awas Yojana - Gramin'), findsWidgets);
      expect(find.byType(ApplicationStatusBadge), findsWidgets);
      expect(find.byKey(const Key('detail_reference_number')), findsOneWidget);
      expect(find.text('PMAY-MH-2026-9921'), findsOneWidget);

      // Verify history item rendered
      expect(find.text('Initial tracking created'), findsWidgets);
      expect(find.text('USER_REPORTED'), findsOneWidget);
    });

    testWidgets('official portal departure dialog opens and shows link',
        (tester) async {
      final fakeService = FakeApplicationService(
        onGetApplicationById: (id) async => sampleApp,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationDetailScreen(
            applicationId: 'app-uuid-1',
            initialApplication: sampleApp,
            applicationService: fakeService,
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Tap official portal button
      await tester.tap(find.byKey(const Key('official_portal_button')));
      await tester.pumpAndSettle();

      // Dialog confirms departure to external government portal
      expect(find.text('Official Portal Departure'), findsOneWidget);
      expect(find.text('https://pmayg.nic.in/apply'), findsOneWidget);
      expect(find.text('Copy Portal Link'), findsOneWidget);

      await tester.tap(find.text('Close'));
      await tester.pumpAndSettle();
      expect(find.text('Official Portal Departure'), findsNothing);
    });

    testWidgets('update status modal submits changes and updates view',
        (tester) async {
      ApplicationUpdateRequestModel? capturedUpdateRequest;

      final updatedApp = ApplicationModel(
        id: 'app-uuid-1',
        userId: 'user-uuid-1',
        schemeId: 'scheme-uuid-1',
        schemeName: 'Pradhan Mantri Awas Yojana - Gramin',
        category: 'Housing',
        department: 'Ministry of Rural Development',
        applicationReferenceNumber: 'PMAY-MH-2026-9921',
        submissionDate: DateTime.utc(2026, 10, 15),
        status: 'Under Review',
        createdAt: DateTime.utc(2026, 10, 15, 10, 0),
        updatedAt: DateTime.utc(2026, 10, 16, 12, 0),
      );

      final fakeService = FakeApplicationService(
        onGetApplicationById: (id) async => sampleApp,
        onUpdateApplication: (id, req) async {
          capturedUpdateRequest = req;
          return updatedApp;
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationDetailScreen(
            applicationId: 'app-uuid-1',
            initialApplication: sampleApp,
            applicationService: fakeService,
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Tap Update Status button
      await tester.tap(find.byKey(const Key('update_status_button')));
      await tester.pumpAndSettle();

      expect(find.text('Update Application Progress'), findsOneWidget);

      // Select 'Under Review' from dropdown
      await tester.tap(find.byKey(const Key('status_dropdown')));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Under Review').last);
      await tester.pumpAndSettle();

      // Enter remarks
      await tester.enterText(find.byKey(const Key('update_remarks_input')),
          'Documents verified at Tahsil');
      await tester.pump();

      // Save
      await tester.tap(find.byKey(const Key('save_status_update_button')));
      await tester.pumpAndSettle();

      expect(capturedUpdateRequest, isNotNull);
      expect(capturedUpdateRequest!.status, 'Under Review');
      expect(capturedUpdateRequest!.remarks, 'Documents verified at Tahsil');
    });

    testWidgets('reminders can be added and completion toggled',
        (tester) async {
      final sampleReminder = ReminderModel(
        id: 'rem-1',
        applicationId: 'app-uuid-1',
        userId: 'user-uuid-1',
        title: 'Submit Bank Passbook Copy',
        description: 'Bring at block office',
        reminderDate: DateTime.utc(2026, 10, 20),
        isCompleted: false,
        createdAt: DateTime.utc(2026, 10, 15),
        updatedAt: DateTime.utc(2026, 10, 15),
      );

      bool reminderToggled = false;
      ReminderCreateRequestModel? capturedReminderCreate;

      final fakeService = FakeApplicationService(
        onGetApplicationById: (id) async => sampleApp,
        onGetApplicationReminders: (id, {isCompleted}) async =>
            ReminderListResponseModel(total: 1, reminders: [sampleReminder]),
        onCreateReminder: (id, req) async {
          capturedReminderCreate = req;
          return sampleReminder;
        },
        onUpdateReminder: (id, remId, req) async {
          reminderToggled = true;
          return ReminderModel(
            id: sampleReminder.id,
            applicationId: sampleReminder.applicationId,
            userId: sampleReminder.userId,
            title: sampleReminder.title,
            description: sampleReminder.description,
            reminderDate: sampleReminder.reminderDate,
            isCompleted: req.isCompleted ?? sampleReminder.isCompleted,
            createdAt: sampleReminder.createdAt,
            updatedAt: sampleReminder.updatedAt,
          );
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationDetailScreen(
            applicationId: 'app-uuid-1',
            initialApplication: sampleApp,
            applicationService: fakeService,
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Submit Bank Passbook Copy'), findsOneWidget);

      // Toggle reminder checkbox
      await tester
          .ensureVisible(find.byKey(const Key('reminder_checkbox_rem-1')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('reminder_checkbox_rem-1')));
      await tester.pumpAndSettle();
      expect(reminderToggled, isTrue);

      // Add a new reminder via dialog
      await tester.ensureVisible(find.byKey(const Key('add_reminder_button')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('add_reminder_button')));
      await tester.pumpAndSettle();

      expect(find.text('Add Application Reminder'), findsOneWidget);
      await tester.enterText(
          find.byKey(const Key('reminder_title_input')), 'Collect Ration Card');
      await tester.pump();

      await tester.tap(find.byKey(const Key('save_reminder_button')));
      await tester.pumpAndSettle();

      expect(capturedReminderCreate, isNotNull);
      expect(capturedReminderCreate!.title, 'Collect Ration Card');
    });

    testWidgets('reminders can be edited with updated task title and date',
        (tester) async {
      final sampleReminder = ReminderModel(
        id: 'rem-edit-1',
        applicationId: 'app-uuid-1',
        userId: 'user-uuid-1',
        title: 'Original Task Title',
        description: 'Original instructions',
        reminderDate: DateTime.utc(2026, 10, 20),
        isCompleted: false,
        createdAt: DateTime.utc(2026, 10, 15),
        updatedAt: DateTime.utc(2026, 10, 15),
      );

      ReminderUpdateRequestModel? capturedUpdate;

      final fakeService = FakeApplicationService(
        onGetApplicationById: (id) async => sampleApp,
        onGetApplicationReminders: (id, {isCompleted}) async =>
            ReminderListResponseModel(total: 1, reminders: [sampleReminder]),
        onUpdateReminder: (id, remId, req) async {
          capturedUpdate = req;
          return ReminderModel(
            id: sampleReminder.id,
            applicationId: sampleReminder.applicationId,
            userId: sampleReminder.userId,
            title: req.title ?? sampleReminder.title,
            description: req.description ?? sampleReminder.description,
            reminderDate: req.reminderDate ?? sampleReminder.reminderDate,
            isCompleted: req.isCompleted ?? sampleReminder.isCompleted,
            createdAt: sampleReminder.createdAt,
            updatedAt: DateTime.utc(2026, 10, 16),
          );
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: ApplicationDetailScreen(
            applicationId: 'app-uuid-1',
            initialApplication: sampleApp,
            applicationService: fakeService,
          ),
        ),
      );

      await tester.pumpAndSettle();

      await tester
          .ensureVisible(find.byKey(const Key('edit_reminder_rem-edit-1')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('edit_reminder_rem-edit-1')));
      await tester.pumpAndSettle();

      expect(find.text('Edit Application Reminder'), findsOneWidget);
      await tester.enterText(find.byKey(const Key('edit_reminder_title_input')),
          'Updated Task Title');
      await tester.pump();

      await tester.tap(find.byKey(const Key('update_reminder_button')));
      await tester.pumpAndSettle();

      expect(capturedUpdate, isNotNull);
      expect(capturedUpdate!.title, 'Updated Task Title');
      expect(find.text('Updated Task Title'), findsOneWidget);
    });
  });
}
