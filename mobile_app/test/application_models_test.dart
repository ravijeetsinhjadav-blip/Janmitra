import 'package:flutter_test/flutter_test.dart';
import 'package:janmitra_assist/features/applications/models/application_models.dart';

void main() {
  group('ApplicationModel Unit Tests', () {
    test('deserializes full JSON response with eager-loaded scheme metadata',
        () {
      final json = {
        'id': '11111111-1111-1111-1111-111111111111',
        'user_id': '22222222-2222-2222-2222-222222222222',
        'scheme_id': '33333333-3333-3333-3333-333333333333',
        'scheme_name': 'PM-KISAN Samman Nidhi',
        'category': 'Agriculture',
        'department': 'Ministry of Agriculture',
        'official_application_url': 'https://pmkisan.gov.in/apply',
        'application_reference_number': 'PMKISAN-2026-9901',
        'submission_date': '2026-10-15T10:30:00.000Z',
        'status': 'Under Review',
        'created_at': '2026-10-15T10:35:00.000Z',
        'updated_at': '2026-10-16T14:20:00.000Z',
      };

      final model = ApplicationModel.fromJson(json);

      expect(model.id, '11111111-1111-1111-1111-111111111111');
      expect(model.userId, '22222222-2222-2222-2222-222222222222');
      expect(model.schemeId, '33333333-3333-3333-3333-333333333333');
      expect(model.schemeName, 'PM-KISAN Samman Nidhi');
      expect(model.category, 'Agriculture');
      expect(model.department, 'Ministry of Agriculture');
      expect(model.officialApplicationUrl, 'https://pmkisan.gov.in/apply');
      expect(model.applicationReferenceNumber, 'PMKISAN-2026-9901');
      expect(model.submissionDate, DateTime.parse('2026-10-15T10:30:00.000Z'));
      expect(model.status, 'Under Review');
      expect(model.hasReferenceNumber, isTrue);
      expect(model.displayReferenceNumber, 'PMKISAN-2026-9901');

      final serialized = model.toJson();
      expect(serialized['id'], model.id);
      expect(serialized['scheme_name'], 'PM-KISAN Samman Nidhi');
      expect(serialized['submission_date'], '2026-10-15T10:30:00.000Z');
      expect(serialized['status'], 'Under Review');
    });

    test('handles nullable reference number and submission date correctly', () {
      final json = {
        'id': '11111111-1111-1111-1111-111111111111',
        'user_id': '22222222-2222-2222-2222-222222222222',
        'scheme_id': '33333333-3333-3333-3333-333333333333',
        'scheme_name': 'State Widow Pension',
        'category': null,
        'department': null,
        'official_application_url': null,
        'application_reference_number': null,
        'submission_date': null,
        'status': 'Submitted',
        'created_at': '2026-10-20T08:00:00.000Z',
        'updated_at': '2026-10-20T08:00:00.000Z',
      };

      final model = ApplicationModel.fromJson(json);

      expect(model.applicationReferenceNumber, isNull);
      expect(model.submissionDate, isNull);
      expect(model.hasReferenceNumber, isFalse);
      expect(model.displayReferenceNumber, 'Not Issued');
    });

    test(
        'hasReferenceNumber handles empty or whitespace-only reference strings',
        () {
      final modelEmpty = ApplicationModel(
        id: '1',
        userId: 'u',
        schemeId: 's',
        schemeName: 'Scheme',
        applicationReferenceNumber: '   ',
        status: ApplicationStatus.submitted,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );
      expect(modelEmpty.hasReferenceNumber, isFalse);
      expect(modelEmpty.displayReferenceNumber, 'Not Issued');
    });
  });

  group('ApplicationListResponseModel Unit Tests', () {
    test('deserializes pagination metadata and application list', () {
      final json = {
        'total': 1,
        'page': 1,
        'page_size': 20,
        'total_pages': 1,
        'applications': [
          {
            'id': 'app-1',
            'user_id': 'user-1',
            'scheme_id': 'scheme-1',
            'scheme_name': 'Awas Yojana',
            'status': 'Submitted',
            'created_at': '2026-10-01T00:00:00.000Z',
            'updated_at': '2026-10-01T00:00:00.000Z',
          }
        ],
      };

      final listModel = ApplicationListResponseModel.fromJson(json);

      expect(listModel.total, 1);
      expect(listModel.page, 1);
      expect(listModel.pageSize, 20);
      expect(listModel.totalPages, 1);
      expect(listModel.applications.length, 1);
      expect(listModel.applications.first.schemeName, 'Awas Yojana');

      final serialized = listModel.toJson();
      expect(serialized['total'], 1);
      expect((serialized['applications'] as List).length, 1);
    });
  });

  group('ApplicationCreateRequestModel Unit Tests', () {
    test(
        'serializes with reference number and reference_number_not_issued=false',
        () {
      final subDate = DateTime.utc(2026, 10, 25, 9, 0, 0);
      final req = ApplicationCreateRequestModel(
        schemeId: 'scheme-uuid-1234',
        submissionDate: subDate,
        applicationReferenceNumber: '  ACK-12345  ',
        referenceNumberNotIssued: false,
        remarks: '  Receipt filed at CSC centre  ',
      );

      final map = req.toJson();

      expect(map['scheme_id'], 'scheme-uuid-1234');
      expect(map['submission_date'], '2026-10-25T09:00:00.000Z');
      expect(map['application_reference_number'], 'ACK-12345');
      expect(map['reference_number_not_issued'], isFalse);
      expect(map['remarks'], 'Receipt filed at CSC centre');
    });

    test('serializes when reference number is not issued', () {
      final subDate = DateTime.utc(2026, 10, 26, 14, 0, 0);
      final req = ApplicationCreateRequestModel(
        schemeId: 'scheme-uuid-5678',
        submissionDate: subDate,
        applicationReferenceNumber: null,
        referenceNumberNotIssued: true,
      );

      final map = req.toJson();

      expect(map['scheme_id'], 'scheme-uuid-5678');
      expect(map['submission_date'], '2026-10-26T14:00:00.000Z');
      expect(map['reference_number_not_issued'], isTrue);
      expect(map.containsKey('application_reference_number'), isFalse);
      expect(map.containsKey('remarks'), isFalse);
    });

    test('converts non-UTC submission date to UTC ISO-8601 string', () {
      final localDate = DateTime.parse('2026-10-27T10:00:00+05:30');
      final req = ApplicationCreateRequestModel(
        schemeId: 'scheme-uuid',
        submissionDate: localDate,
        referenceNumberNotIssued: true,
      );

      final map = req.toJson();
      expect(map['submission_date'], localDate.toUtc().toIso8601String());
      expect((map['submission_date'] as String).endsWith('Z'), isTrue);
    });
  });

  group('ApplicationUpdateRequestModel Unit Tests', () {
    test('status-only update omits other fields', () {
      final req = ApplicationUpdateRequestModel(status: 'Approved');
      final map = req.toJson();

      expect(map, {'status': 'Approved'});
    });

    test('remarks-only update omits status and reference fields', () {
      final req = ApplicationUpdateRequestModel(
          remarks: 'Follow-up inspection scheduled');
      final map = req.toJson();

      expect(map, {'remarks': 'Follow-up inspection scheduled'});
    });

    test('reference number update omits status and remarks', () {
      final req = ApplicationUpdateRequestModel(
          applicationReferenceNumber: 'NEW-REF-999');
      final map = req.toJson();

      expect(map, {'application_reference_number': 'NEW-REF-999'});
    });

    test(
        'explicit reference number clearing transmits clear_reference_number: true and application_reference_number: null',
        () {
      final req = ApplicationUpdateRequestModel(clearReferenceNumber: true);
      final map = req.toJson();

      expect(map['clear_reference_number'], isTrue);
      expect(map['application_reference_number'], isNull);
      expect(map.containsKey('application_reference_number'), isTrue);
      expect(map.containsKey('status'), isFalse);
    });

    test('submission date update formats to UTC ISO string', () {
      final dt = DateTime.utc(2026, 10, 20, 11, 0, 0);
      final req = ApplicationUpdateRequestModel(submissionDate: dt);
      final map = req.toJson();

      expect(map, {'submission_date': '2026-10-20T11:00:00.000Z'});
    });

    test('empty update produces empty map', () {
      final req = ApplicationUpdateRequestModel();
      final map = req.toJson();

      expect(map, isEmpty);
    });
  });

  group('ApplicationStatusHistoryModel Unit Tests', () {
    test('deserializes INITIAL_REGISTRATION event from SYSTEM_MIGRATION source',
        () {
      final json = {
        'id': 'hist-1',
        'application_id': 'app-1',
        'previous_status': null,
        'new_status': 'Submitted',
        'event_type': 'INITIAL_REGISTRATION',
        'source': 'SYSTEM_MIGRATION',
        'remarks': null,
        'changed_by_user_id': null,
        'created_at': '2026-10-01T00:00:00.000Z',
      };

      final hist = ApplicationStatusHistoryModel.fromJson(json);

      expect(hist.id, 'hist-1');
      expect(hist.applicationId, 'app-1');
      expect(hist.previousStatus, isNull);
      expect(hist.newStatus, 'Submitted');
      expect(hist.eventType, HistoryEventType.initialRegistration);
      expect(hist.source, HistorySource.systemMigration);
      expect(hist.remarks, isNull);
      expect(hist.changedByUserId, isNull);
      expect(hist.createdAt, DateTime.parse('2026-10-01T00:00:00.000Z'));
    });

    test(
        'deserializes STATUS_UPDATE, REMARK_ADDED, and APPLICATION_DETAILS_UPDATED events',
        () {
      for (final event in [
        HistoryEventType.statusUpdate,
        HistoryEventType.remarkAdded,
        HistoryEventType.applicationDetailsUpdated,
      ]) {
        final json = {
          'id': 'hist-uuid',
          'application_id': 'app-uuid',
          'previous_status': 'Submitted',
          'new_status': 'Under Review',
          'event_type': event,
          'source': 'USER_REPORTED',
          'remarks': 'Status remark test',
          'changed_by_user_id': 'user-uuid',
          'created_at': '2026-10-15T12:00:00.000Z',
        };

        final model = ApplicationStatusHistoryModel.fromJson(json);
        expect(model.eventType, event);
        expect(model.source, HistorySource.userReported);
        expect(model.remarks, 'Status remark test');
        expect(model.changedByUserId, 'user-uuid');
      }
    });

    test(
        'ApplicationStatusHistoryListModel preserves exact legal disclaimer and total',
        () {
      final json = {
        'application_id': 'app-uuid',
        'current_status': 'Under Review',
        'total': 2,
        'disclaimer':
            'Status history entries reflect manual updates entered by the citizen. JanMitra Assist tracking records do not represent official government determinations.',
        'history': [
          {
            'id': 'h2',
            'application_id': 'app-uuid',
            'previous_status': 'Submitted',
            'new_status': 'Under Review',
            'event_type': 'STATUS_UPDATE',
            'source': 'USER_REPORTED',
            'remarks': 'Documents submitted at Tehsil',
            'changed_by_user_id': 'u1',
            'created_at': '2026-10-16T10:00:00.000Z',
          },
          {
            'id': 'h1',
            'application_id': 'app-uuid',
            'previous_status': null,
            'new_status': 'Submitted',
            'event_type': 'INITIAL_REGISTRATION',
            'source': 'USER_REPORTED',
            'remarks': null,
            'changed_by_user_id': 'u1',
            'created_at': '2026-10-15T10:00:00.000Z',
          },
        ],
      };

      final listModel = ApplicationStatusHistoryListModel.fromJson(json);

      expect(listModel.total, 2);
      expect(listModel.currentStatus, 'Under Review');
      expect(listModel.disclaimer,
          contains('do not represent official government determinations'));
      expect(listModel.history.length, 2);
      expect(listModel.history[0].newStatus, 'Under Review');
      expect(listModel.history[1].newStatus, 'Submitted');
    });
  });

  group('ReminderModel Unit Tests', () {
    test('deserializes complete reminder object with timestamps', () {
      final json = {
        'id': 'rem-1',
        'application_id': 'app-1',
        'user_id': 'user-1',
        'title': 'Submit physical land extract',
        'description': 'Carry original 7/12 copy to CSC',
        'reminder_date': '2026-11-10T09:00:00.000Z',
        'is_completed': false,
        'completed_at': null,
        'created_at': '2026-10-31T08:00:00.000Z',
        'updated_at': '2026-10-31T08:00:00.000Z',
      };

      final rem = ReminderModel.fromJson(json);

      expect(rem.id, 'rem-1');
      expect(rem.applicationId, 'app-1');
      expect(rem.userId, 'user-1');
      expect(rem.title, 'Submit physical land extract');
      expect(rem.description, 'Carry original 7/12 copy to CSC');
      expect(rem.reminderDate, DateTime.parse('2026-11-10T09:00:00.000Z'));
      expect(rem.isCompleted, isFalse);
      expect(rem.completedAt, isNull);

      final map = rem.toJson();
      expect(map['reminder_date'], '2026-11-10T09:00:00.000Z');
      expect(map['is_completed'], isFalse);
    });

    test('isOverdue and isDueToday helpers evaluate correctly', () {
      final pastDate = DateTime.now().subtract(const Duration(days: 3));
      final futureDate = DateTime.now().add(const Duration(days: 3));
      final todayDate = DateTime.now();

      final overdueReminder = ReminderModel(
        id: 'r1',
        applicationId: 'a1',
        userId: 'u1',
        title: 'Overdue task',
        reminderDate: pastDate,
        isCompleted: false,
        createdAt: pastDate,
        updatedAt: pastDate,
      );
      expect(overdueReminder.isOverdue, isTrue);

      // Completed reminder must NOT be overdue even if date is past
      final completedOverdueReminder = ReminderModel(
        id: 'r2',
        applicationId: 'a1',
        userId: 'u1',
        title: 'Completed past task',
        reminderDate: pastDate,
        isCompleted: true,
        completedAt: DateTime.now(),
        createdAt: pastDate,
        updatedAt: pastDate,
      );
      expect(completedOverdueReminder.isOverdue, isFalse);

      final futureReminder = ReminderModel(
        id: 'r3',
        applicationId: 'a1',
        userId: 'u1',
        title: 'Future task',
        reminderDate: futureDate,
        isCompleted: false,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );
      expect(futureReminder.isOverdue, isFalse);
      expect(futureReminder.isDueToday, isFalse);

      final todayReminder = ReminderModel(
        id: 'r4',
        applicationId: 'a1',
        userId: 'u1',
        title: 'Today task',
        reminderDate: todayDate,
        isCompleted: false,
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );
      expect(todayReminder.isDueToday, isTrue);

      final completedTodayReminder = ReminderModel(
        id: 'r5',
        applicationId: 'a1',
        userId: 'u1',
        title: 'Completed today task',
        reminderDate: todayDate,
        isCompleted: true,
        completedAt: DateTime.now(),
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      );
      expect(completedTodayReminder.isDueToday, isFalse);
    });
  });

  group('Reminder Request Models Unit Tests', () {
    test(
        'ReminderCreateRequestModel serializes title, UTC date, and description',
        () {
      final date = DateTime.utc(2026, 11, 5, 14, 30, 0);
      final req = ReminderCreateRequestModel(
        title: '  Biometrics verification  ',
        reminderDate: date,
        description: '  Bring Aadhaar OTP mobile  ',
      );

      final map = req.toJson();

      expect(map['title'], 'Biometrics verification');
      expect(map['reminder_date'], '2026-11-05T14:30:00.000Z');
      expect(map['description'], 'Bring Aadhaar OTP mobile');
    });

    test('ReminderCreateRequestModel omits description when null or empty', () {
      final date = DateTime.utc(2026, 11, 5, 14, 30, 0);
      final req = ReminderCreateRequestModel(
        title: 'Verification',
        reminderDate: date,
        description: null,
      );

      final map = req.toJson();

      expect(map.containsKey('description'), isFalse);
    });

    test('ReminderUpdateRequestModel serializes only supplied fields', () {
      final date = DateTime.utc(2026, 11, 8, 10, 0, 0);

      // Title and date update
      final req1 = ReminderUpdateRequestModel(
        title: 'Updated title',
        reminderDate: date,
      );
      final map1 = req1.toJson();
      expect(map1['title'], 'Updated title');
      expect(map1['reminder_date'], '2026-11-08T10:00:00.000Z');
      expect(map1.containsKey('is_completed'), isFalse);
      expect(map1.containsKey('description'), isFalse);

      // Completion toggle update
      final req2 = ReminderUpdateRequestModel(isCompleted: true);
      final map2 = req2.toJson();
      expect(map2, {'is_completed': true});
    });
  });

  group('ReminderListResponseModel & Delete Responses Unit Tests', () {
    test('ReminderListResponseModel deserializes total and list', () {
      final json = {
        'total': 1,
        'reminders': [
          {
            'id': 'rem-uuid',
            'application_id': 'app-uuid',
            'user_id': 'user-uuid',
            'title': 'Test Reminder',
            'reminder_date': '2026-11-12T00:00:00.000Z',
            'is_completed': false,
            'created_at': '2026-10-31T00:00:00.000Z',
            'updated_at': '2026-10-31T00:00:00.000Z',
          }
        ],
      };

      final listModel = ReminderListResponseModel.fromJson(json);

      expect(listModel.total, 1);
      expect(listModel.reminders.length, 1);
      expect(listModel.reminders.first.title, 'Test Reminder');
    });

    test(
        'ApplicationDeleteResponseModel and ReminderDeleteResponseModel deserialization',
        () {
      final appDel = ApplicationDeleteResponseModel.fromJson({
        'id': 'app-del-id',
        'message': 'Application tracking record deleted successfully.',
      });
      expect(appDel.id, 'app-del-id');
      expect(appDel.message, contains('deleted successfully'));

      final remDel = ReminderDeleteResponseModel.fromJson({
        'id': 'rem-del-id',
        'message': 'Reminder deleted successfully.',
      });
      expect(remDel.id, 'rem-del-id');
      expect(remDel.message, contains('Reminder deleted successfully'));
    });
  });
}
