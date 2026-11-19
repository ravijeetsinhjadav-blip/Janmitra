import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:janmitra_assist/core/network/auth_service.dart';
import 'package:janmitra_assist/core/services/secure_storage_service.dart';
import 'package:janmitra_assist/features/auth/models/auth_models.dart';
import 'package:janmitra_assist/features/applications/models/application_models.dart';
import 'package:janmitra_assist/features/applications/services/application_service.dart';

class FakeSecureStorageService implements SecureStorageService {
  String? accessToken;
  String? refreshToken;

  FakeSecureStorageService({
    this.accessToken = 'test_access_token',
    this.refreshToken = 'test_refresh_token',
  });

  @override
  Future<String?> getAccessToken() async => accessToken;

  @override
  Future<String?> getRefreshToken() async => refreshToken;

  @override
  Future<void> updateTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class FakeAuthService implements AuthService {
  bool shouldSucceed;
  String newAccessToken;
  int refreshCallCount = 0;

  FakeAuthService({
    this.shouldSucceed = true,
    this.newAccessToken = 'refreshed_access_token',
  });

  @override
  Future<TokenResponseModel?> refreshToken() async {
    refreshCallCount++;
    if (shouldSucceed) {
      return TokenResponseModel(
        accessToken: newAccessToken,
        refreshToken: 'new_refresh_token',
        tokenType: 'bearer',
        expiresIn: 1800,
        isNewUser: false,
        userId: 'test_user_id',
        role: 'citizen',
        profileCompleted: true,
      );
    }
    return null;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  const sampleAppJson = {
    'id': '11111111-1111-1111-1111-111111111111',
    'user_id': '22222222-2222-2222-2222-222222222222',
    'scheme_id': '33333333-3333-3333-3333-333333333333',
    'scheme_name': 'PM-KISAN',
    'category': 'Agriculture',
    'department': 'Ministry of Agriculture',
    'official_application_url': 'https://pmkisan.gov.in',
    'application_reference_number': 'PMK-2026-001',
    'submission_date': '2026-10-25T10:00:00.000Z',
    'status': 'Submitted',
    'created_at': '2026-10-25T10:05:00.000Z',
    'updated_at': '2026-10-25T10:05:00.000Z',
  };

  const sampleReminderJson = {
    'id': 'rem-1111-1111',
    'application_id': '11111111-1111-1111-1111-111111111111',
    'user_id': '22222222-2222-2222-2222-222222222222',
    'title': 'Submit biometric verification',
    'description': 'Carry Aadhaar and OTP phone',
    'reminder_date': '2026-11-15T09:00:00.000Z',
    'is_completed': false,
    'completed_at': null,
    'created_at': '2026-10-31T00:00:00.000Z',
    'updated_at': '2026-10-31T00:00:00.000Z',
  };

  group('ApplicationService Operations Tests', () {
    test(
        'createApplication sends POST and parses ApplicationModel without user_id in body',
        () async {
      late http.Request capturedRequest;
      final mockClient = MockClient((request) async {
        capturedRequest = request;
        return http.Response(jsonEncode(sampleAppJson), 201);
      });

      final storage = FakeSecureStorageService();
      final service = ApplicationService(client: mockClient, storage: storage);

      final req = ApplicationCreateRequestModel(
        schemeId: '33333333-3333-3333-3333-333333333333',
        submissionDate: DateTime.utc(2026, 10, 25, 10, 0, 0),
        applicationReferenceNumber: 'PMK-2026-001',
      );

      final result = await service.createApplication(req);

      expect(capturedRequest.method, 'POST');
      expect(capturedRequest.url.path, '/api/v1/applications');
      expect(
          capturedRequest.headers['Authorization'], 'Bearer test_access_token');

      final bodyMap = jsonDecode(capturedRequest.body) as Map<String, dynamic>;
      expect(bodyMap.containsKey('user_id'), isFalse);
      expect(bodyMap['scheme_id'], '33333333-3333-3333-3333-333333333333');
      expect(bodyMap['application_reference_number'], 'PMK-2026-001');

      expect(result.id, '11111111-1111-1111-1111-111111111111');
      expect(result.schemeName, 'PM-KISAN');
    });

    test('getApplications formats query parameters and parses list', () async {
      late http.Request capturedRequest;
      final mockClient = MockClient((request) async {
        capturedRequest = request;
        return http.Response(
          jsonEncode({
            'total': 1,
            'page': 2,
            'page_size': 10,
            'total_pages': 1,
            'applications': [sampleAppJson],
          }),
          200,
        );
      });

      final service = ApplicationService(
        client: mockClient,
        storage: FakeSecureStorageService(),
      );

      final result = await service.getApplications(
        status: 'Under Review',
        schemeId: 'scheme-uuid',
        page: 2,
        pageSize: 10,
      );

      expect(capturedRequest.method, 'GET');
      expect(capturedRequest.url.path, '/api/v1/applications');
      expect(capturedRequest.url.queryParameters['status'], 'Under Review');
      expect(capturedRequest.url.queryParameters['scheme_id'], 'scheme-uuid');
      expect(capturedRequest.url.queryParameters['page'], '2');
      expect(capturedRequest.url.queryParameters['page_size'], '10');

      expect(result.total, 1);
      expect(result.page, 2);
      expect(result.applications.length, 1);
    });

    test('getApplicationById fetches single application detail', () async {
      late http.Request capturedRequest;
      final mockClient = MockClient((request) async {
        capturedRequest = request;
        return http.Response(jsonEncode(sampleAppJson), 200);
      });

      final service = ApplicationService(
        client: mockClient,
        storage: FakeSecureStorageService(),
      );

      final result = await service
          .getApplicationById('11111111-1111-1111-1111-111111111111');

      expect(capturedRequest.method, 'GET');
      expect(capturedRequest.url.path,
          '/api/v1/applications/11111111-1111-1111-1111-111111111111');
      expect(result.id, '11111111-1111-1111-1111-111111111111');
    });

    test('updateApplication sends PATCH with updated fields', () async {
      late http.Request capturedRequest;
      final mockClient = MockClient((request) async {
        capturedRequest = request;
        final updatedJson = Map<String, dynamic>.from(sampleAppJson);
        updatedJson['status'] = 'Approved';
        return http.Response(jsonEncode(updatedJson), 200);
      });

      final service = ApplicationService(
        client: mockClient,
        storage: FakeSecureStorageService(),
      );

      final req = ApplicationUpdateRequestModel(status: 'Approved');
      final result = await service.updateApplication(
          '11111111-1111-1111-1111-111111111111', req);

      expect(capturedRequest.method, 'PATCH');
      expect(capturedRequest.url.path,
          '/api/v1/applications/11111111-1111-1111-1111-111111111111');
      expect(jsonDecode(capturedRequest.body), {'status': 'Approved'});
      expect(result.status, 'Approved');
    });

    test('deleteApplication sends DELETE and returns confirmation message',
        () async {
      late http.Request capturedRequest;
      final mockClient = MockClient((request) async {
        capturedRequest = request;
        return http.Response(
          jsonEncode({
            'id': '11111111-1111-1111-1111-111111111111',
            'message': 'Local tracking entry deleted successfully.',
          }),
          200,
        );
      });

      final service = ApplicationService(
        client: mockClient,
        storage: FakeSecureStorageService(),
      );

      final result = await service
          .deleteApplication('11111111-1111-1111-1111-111111111111');

      expect(capturedRequest.method, 'DELETE');
      expect(capturedRequest.url.path,
          '/api/v1/applications/11111111-1111-1111-1111-111111111111');
      expect(result.id, '11111111-1111-1111-1111-111111111111');
      expect(result.message, contains('deleted successfully'));
    });

    test('getApplicationHistory parses timeline records and legal disclaimer',
        () async {
      late http.Request capturedRequest;
      final mockClient = MockClient((request) async {
        capturedRequest = request;
        return http.Response(
          jsonEncode({
            'application_id': '11111111-1111-1111-1111-111111111111',
            'current_status': 'Submitted',
            'total': 1,
            'disclaimer':
                'Status history entries reflect manual updates entered by the citizen. JanMitra Assist tracking records do not represent official government determinations.',
            'history': [
              {
                'id': 'hist-1',
                'application_id': '11111111-1111-1111-1111-111111111111',
                'previous_status': null,
                'new_status': 'Submitted',
                'event_type': 'INITIAL_REGISTRATION',
                'source': 'USER_REPORTED',
                'remarks': 'Initial filing',
                'changed_by_user_id': '22222222-2222-2222-2222-222222222222',
                'created_at': '2026-10-25T10:05:00.000Z',
              }
            ],
          }),
          200,
        );
      });

      final service = ApplicationService(
        client: mockClient,
        storage: FakeSecureStorageService(),
      );

      final result = await service
          .getApplicationHistory('11111111-1111-1111-1111-111111111111');

      expect(capturedRequest.method, 'GET');
      expect(capturedRequest.url.path,
          '/api/v1/applications/11111111-1111-1111-1111-111111111111/history');
      expect(result.total, 1);
      expect(result.disclaimer,
          contains('do not represent official government determinations'));
      expect(result.history.first.eventType, 'INITIAL_REGISTRATION');
      expect(result.history.first.source, 'USER_REPORTED');
    });

    test('getUpcomingReminders queries global upcoming route', () async {
      late http.Request capturedRequest;
      final mockClient = MockClient((request) async {
        capturedRequest = request;
        return http.Response(
          jsonEncode({
            'total': 1,
            'reminders': [sampleReminderJson],
          }),
          200,
        );
      });

      final service = ApplicationService(
        client: mockClient,
        storage: FakeSecureStorageService(),
      );

      final result = await service.getUpcomingReminders();

      expect(capturedRequest.method, 'GET');
      expect(
          capturedRequest.url.path, '/api/v1/applications/reminders/upcoming');
      expect(result.total, 1);
      expect(result.reminders.first.title, 'Submit biometric verification');
    });

    test(
        'createReminder sends POST to application subresource without user_id in body',
        () async {
      late http.Request capturedRequest;
      final mockClient = MockClient((request) async {
        capturedRequest = request;
        return http.Response(jsonEncode(sampleReminderJson), 201);
      });

      final service = ApplicationService(
        client: mockClient,
        storage: FakeSecureStorageService(),
      );

      final req = ReminderCreateRequestModel(
        title: 'Submit biometric verification',
        reminderDate: DateTime.utc(2026, 11, 15, 9, 0, 0),
        description: 'Carry Aadhaar and OTP phone',
      );

      final result = await service.createReminder(
          '11111111-1111-1111-1111-111111111111', req);

      expect(capturedRequest.method, 'POST');
      expect(capturedRequest.url.path,
          '/api/v1/applications/11111111-1111-1111-1111-111111111111/reminders');
      final body = jsonDecode(capturedRequest.body) as Map<String, dynamic>;
      expect(body.containsKey('user_id'), isFalse);
      expect(body['title'], 'Submit biometric verification');
      expect(result.title, 'Submit biometric verification');
    });

    test(
        'getApplicationReminders includes is_completed query parameter when specified',
        () async {
      late http.Request capturedRequest;
      final mockClient = MockClient((request) async {
        capturedRequest = request;
        return http.Response(
          jsonEncode({
            'total': 1,
            'reminders': [sampleReminderJson],
          }),
          200,
        );
      });

      final service = ApplicationService(
        client: mockClient,
        storage: FakeSecureStorageService(),
      );

      final result = await service.getApplicationReminders(
        '11111111-1111-1111-1111-111111111111',
        isCompleted: false,
      );

      expect(capturedRequest.method, 'GET');
      expect(capturedRequest.url.path,
          '/api/v1/applications/11111111-1111-1111-1111-111111111111/reminders');
      expect(capturedRequest.url.queryParameters['is_completed'], 'false');
      expect(result.total, 1);
    });

    test('getReminderById fetches individual reminder subresource', () async {
      late http.Request capturedRequest;
      final mockClient = MockClient((request) async {
        capturedRequest = request;
        return http.Response(jsonEncode(sampleReminderJson), 200);
      });

      final service = ApplicationService(
        client: mockClient,
        storage: FakeSecureStorageService(),
      );

      final result = await service.getReminderById(
        '11111111-1111-1111-1111-111111111111',
        'rem-1111-1111',
      );

      expect(capturedRequest.method, 'GET');
      expect(
        capturedRequest.url.path,
        '/api/v1/applications/11111111-1111-1111-1111-111111111111/reminders/rem-1111-1111',
      );
      expect(result.id, 'rem-1111-1111');
    });

    test('updateReminder sends PATCH to toggle reminder completion', () async {
      late http.Request capturedRequest;
      final mockClient = MockClient((request) async {
        capturedRequest = request;
        final updatedJson = Map<String, dynamic>.from(sampleReminderJson);
        updatedJson['is_completed'] = true;
        updatedJson['completed_at'] = '2026-11-15T12:00:00.000Z';
        return http.Response(jsonEncode(updatedJson), 200);
      });

      final service = ApplicationService(
        client: mockClient,
        storage: FakeSecureStorageService(),
      );

      final req = ReminderUpdateRequestModel(isCompleted: true);
      final result = await service.updateReminder(
        '11111111-1111-1111-1111-111111111111',
        'rem-1111-1111',
        req,
      );

      expect(capturedRequest.method, 'PATCH');
      expect(
        capturedRequest.url.path,
        '/api/v1/applications/11111111-1111-1111-1111-111111111111/reminders/rem-1111-1111',
      );
      expect(jsonDecode(capturedRequest.body), {'is_completed': true});
      expect(result.isCompleted, isTrue);
    });

    test('deleteReminder sends DELETE and returns confirmation message',
        () async {
      late http.Request capturedRequest;
      final mockClient = MockClient((request) async {
        capturedRequest = request;
        return http.Response(
          jsonEncode({
            'id': 'rem-1111-1111',
            'message': 'Reminder deleted successfully.',
          }),
          200,
        );
      });

      final service = ApplicationService(
        client: mockClient,
        storage: FakeSecureStorageService(),
      );

      final result = await service.deleteReminder(
        '11111111-1111-1111-1111-111111111111',
        'rem-1111-1111',
      );

      expect(capturedRequest.method, 'DELETE');
      expect(
        capturedRequest.url.path,
        '/api/v1/applications/11111111-1111-1111-1111-111111111111/reminders/rem-1111-1111',
      );
      expect(result.id, 'rem-1111-1111');
      expect(result.message, contains('deleted successfully'));
    });
  });

  group('Authentication 401 Refresh & Retry Tests', () {
    test('retries authenticated request once after successful token refresh',
        () async {
      int requestCount = 0;
      final mockClient = MockClient((request) async {
        requestCount++;
        if (requestCount == 1) {
          expect(request.headers['Authorization'], 'Bearer test_access_token');
          return http.Response('{"detail": "Token expired"}', 401);
        } else {
          expect(request.headers['Authorization'],
              'Bearer refreshed_access_token');
          return http.Response(jsonEncode(sampleAppJson), 200);
        }
      });

      final storage =
          FakeSecureStorageService(accessToken: 'test_access_token');
      final authService = FakeAuthService(
        shouldSucceed: true,
        newAccessToken: 'refreshed_access_token',
      );

      final service = ApplicationService(
        client: mockClient,
        storage: storage,
        authService: authService,
      );

      final result = await service
          .getApplicationById('11111111-1111-1111-1111-111111111111');

      expect(requestCount, 2);
      expect(authService.refreshCallCount, 1);
      expect(result.id, '11111111-1111-1111-1111-111111111111');
    });

    test('throws Session expired when refresh fails without infinite loop',
        () async {
      int requestCount = 0;
      final mockClient = MockClient((request) async {
        requestCount++;
        return http.Response('{"detail": "Invalid credentials"}', 401);
      });

      final storage = FakeSecureStorageService();
      final authService = FakeAuthService(shouldSucceed: false);

      final service = ApplicationService(
        client: mockClient,
        storage: storage,
        authService: authService,
      );

      await expectLater(
        service.getApplicationById('11111111-1111-1111-1111-111111111111'),
        throwsA(predicate(
            (e) => e is Exception && e.toString().contains('Session expired'))),
      );

      expect(requestCount, 1);
      expect(authService.refreshCallCount, 1);
    });

    test('throws Session expired when retried request returns 401 again',
        () async {
      int requestCount = 0;
      final mockClient = MockClient((request) async {
        requestCount++;
        return http.Response('{"detail": "Token revoked"}', 401);
      });

      final storage = FakeSecureStorageService();
      final authService = FakeAuthService(shouldSucceed: true);

      final service = ApplicationService(
        client: mockClient,
        storage: storage,
        authService: authService,
      );

      await expectLater(
        service.getApplicationById('11111111-1111-1111-1111-111111111111'),
        throwsA(predicate(
            (e) => e is Exception && e.toString().contains('Session expired'))),
      );

      expect(requestCount, 2);
      expect(authService.refreshCallCount, 1);
    });
  });

  group('Error Handling & Network Resilience Tests', () {
    test('parses 404 string detail error message', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode({'detail': 'Application tracking record not found.'}),
          404,
        );
      });

      final service = ApplicationService(
        client: mockClient,
        storage: FakeSecureStorageService(),
      );

      await expectLater(
        service.getApplicationById('invalid-id'),
        throwsA(predicate((e) =>
            e is Exception &&
            e.toString().contains('Application tracking record not found.'))),
      );
    });

    test('parses 422 validation error array message', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'detail': [
              {
                'loc': ['body', 'status'],
                'msg': "Invalid status 'Pending Review'."
              }
            ]
          }),
          422,
        );
      });

      final service = ApplicationService(
        client: mockClient,
        storage: FakeSecureStorageService(),
      );

      await expectLater(
        service.updateApplication(
          '11111111-1111-1111-1111-111111111111',
          ApplicationUpdateRequestModel(status: 'Pending Review'),
        ),
        throwsA(predicate((e) =>
            e is Exception &&
            e.toString().contains("Invalid status 'Pending Review'."))),
      );
    });

    test('parses 500 server error', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode({'detail': 'Internal server error occurred.'}),
          500,
        );
      });

      final service = ApplicationService(
        client: mockClient,
        storage: FakeSecureStorageService(),
      );

      await expectLater(
        service.getApplicationById('11111111-1111-1111-1111-111111111111'),
        throwsA(predicate((e) =>
            e is Exception &&
            e.toString().contains('Internal server error occurred.'))),
      );
    });

    test('handles malformed non-JSON response gracefully', () async {
      final mockClient = MockClient((request) async {
        return http.Response('<html><body>502 Bad Gateway</body></html>', 502);
      });

      final service = ApplicationService(
        client: mockClient,
        storage: FakeSecureStorageService(),
      );

      await expectLater(
        service.getApplicationById('11111111-1111-1111-1111-111111111111'),
        throwsA(predicate((e) =>
            e is Exception &&
            e.toString().contains('Server returned error status 502'))),
      );
    });

    test('handles SocketException with user-friendly message', () async {
      final mockClient = MockClient((request) async {
        throw const SocketException('Host lookup failed');
      });

      final service = ApplicationService(
        client: mockClient,
        storage: FakeSecureStorageService(),
      );

      await expectLater(
        service.getApplicationById('11111111-1111-1111-1111-111111111111'),
        throwsA(predicate((e) =>
            e is Exception &&
            e.toString().contains('Cannot connect to JanMitra server'))),
      );
    });

    test('handles http.ClientException with network error message', () async {
      final mockClient = MockClient((request) async {
        throw http.ClientException('Connection closed abruptly');
      });

      final service = ApplicationService(
        client: mockClient,
        storage: FakeSecureStorageService(),
      );

      await expectLater(
        service.getApplicationById('11111111-1111-1111-1111-111111111111'),
        throwsA(predicate((e) =>
            e is Exception &&
            e.toString().contains('Network connection error'))),
      );
    });
  });
}
