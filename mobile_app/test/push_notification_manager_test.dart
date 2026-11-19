import 'package:flutter_test/flutter_test.dart';
import 'package:janmitra_assist/features/notifications/models/notification_models.dart';
import 'package:janmitra_assist/features/notifications/services/notification_service.dart';
import 'package:janmitra_assist/features/notifications/services/push_notification_manager.dart';

class FakeNotificationService implements NotificationService {
  String? registeredToken;
  String? registeredDeviceType;
  String? deactivatedToken;

  @override
  Future<void> registerDeviceToken(String deviceToken,
      {String deviceType = 'android'}) async {
    registeredToken = deviceToken;
    registeredDeviceType = deviceType;
  }

  @override
  Future<void> deactivateDeviceToken(String deviceToken) async {
    deactivatedToken = deviceToken;
  }

  @override
  Future<NotificationListResponseModel> getNotifications(
      {int page = 1, int pageSize = 20, bool? isRead}) async {
    return NotificationListResponseModel(
      total: 0,
      unreadCount: 0,
      page: 1,
      pageSize: 20,
      totalPages: 0,
      notifications: [],
    );
  }

  @override
  Future<int> getUnreadCount() async => 0;

  @override
  Future<void> markAllAsRead() async {}

  @override
  Future<void> markAsRead(String notificationId) async {}

  @override
  void dispose() {}

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  group('PushNotificationManager Tests', () {
    late FakeNotificationService fakeService;
    late PushNotificationManager manager;

    setUp(() {
      fakeService = FakeNotificationService();
      manager = PushNotificationManager(notificationService: fakeService);
    });

    tearDown(() {
      manager.dispose();
    });

    test(
        'initializes safely in fallback mode when native Firebase is unprovisioned',
        () async {
      await manager.initialize();
      expect(manager.isInitialized, isTrue);
      expect(manager.currentDeviceToken, isNull);
    });

    test('registers device token with backend when token is available',
        () async {
      const testToken = 'fcm-mock-token-abc-123';
      await manager.initialize(mockTokenForTesting: testToken);

      expect(manager.isInitialized, isTrue);
      expect(manager.currentDeviceToken, testToken);
      expect(fakeService.registeredToken, testToken);
      expect(fakeService.registeredDeviceType, isNotNull);
    });

    test('handles token refresh and re-registers with backend', () async {
      await manager.initialize(mockTokenForTesting: 'old-token');
      expect(fakeService.registeredToken, 'old-token');

      await manager.handleTokenRefresh('new-refreshed-token-xyz');
      expect(manager.currentDeviceToken, 'new-refreshed-token-xyz');
      expect(fakeService.registeredToken, 'new-refreshed-token-xyz');
    });

    test('emits foreground push notification to onMessageReceived stream',
        () async {
      const payload = PushMessagePayload(
        messageId: 'msg-001',
        title: 'Application Under Review',
        body: 'PM Kisan department is reviewing your document.',
        data: {'application_id': 'app-123'},
      );

      final expectation = expectLater(
        manager.onMessageReceived,
        emits(predicate<PushMessagePayload>((msg) {
          return msg.messageId == 'msg-001' &&
              msg.title == 'Application Under Review' &&
              msg.data['application_id'] == 'app-123';
        })),
      );

      manager.handleForegroundMessage(payload);
      await expectation;
    });

    test('deactivates token upon citizen sign-out', () async {
      await manager.initialize(mockTokenForTesting: 'logout-token-123');
      expect(manager.currentDeviceToken, 'logout-token-123');

      await manager.unregisterOnLogout();
      expect(fakeService.deactivatedToken, 'logout-token-123');
      expect(manager.currentDeviceToken, isNull);
    });
  });
}
