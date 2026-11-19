import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:janmitra_assist/features/notifications/models/notification_models.dart';
import 'package:janmitra_assist/features/notifications/presentation/screens/notification_history_screen.dart';
import 'package:janmitra_assist/features/notifications/services/notification_service.dart';

class FakeNotificationService implements NotificationService {
  final Future<NotificationListResponseModel> Function(
      {int page, int pageSize, bool? isRead})? onGetNotifications;
  final Future<void> Function(String)? onMarkAsRead;
  final Future<void> Function()? onMarkAllAsRead;
  final Future<int> Function()? onGetUnreadCount;

  FakeNotificationService({
    this.onGetNotifications,
    this.onMarkAsRead,
    this.onMarkAllAsRead,
    this.onGetUnreadCount,
  });

  @override
  Future<NotificationListResponseModel> getNotifications({
    int page = 1,
    int pageSize = 20,
    bool? isRead,
  }) async {
    if (onGetNotifications != null) {
      return onGetNotifications!(
          page: page, pageSize: pageSize, isRead: isRead);
    }
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
  Future<void> markAsRead(String notificationId) async {
    if (onMarkAsRead != null) return onMarkAsRead!(notificationId);
  }

  @override
  Future<void> markAllAsRead() async {
    if (onMarkAllAsRead != null) return onMarkAllAsRead!();
  }

  @override
  Future<int> getUnreadCount() async {
    if (onGetUnreadCount != null) return onGetUnreadCount!();
    return 0;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  final sampleNotif1 = NotificationModel(
    id: 'notif-1',
    userId: 'user-1',
    title: 'Scheme Alert: PM-KISAN',
    message: '17th installment of PM-KISAN released.',
    notificationType: 'scheme_alert',
    isRead: false,
    createdAt: DateTime.utc(2026, 10, 20, 10, 0),
  );

  final sampleNotif2 = NotificationModel(
    id: 'notif-2',
    userId: 'user-1',
    title: 'Biometrics Scheduled',
    message: 'Visit Tahsil center before 25th October.',
    notificationType: 'document_reminder',
    isRead: true,
    createdAt: DateTime.utc(2026, 10, 18, 14, 30),
  );

  group('NotificationHistoryScreen Widget Tests', () {
    testWidgets('renders empty state when no notifications present',
        (tester) async {
      final fakeService = FakeNotificationService(
        onGetNotifications: ({page = 1, pageSize = 20, isRead}) async {
          return NotificationListResponseModel(
            total: 0,
            unreadCount: 0,
            page: 1,
            pageSize: 20,
            totalPages: 0,
            notifications: [],
          );
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: NotificationHistoryScreen(notificationService: fakeService),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('No Notifications Yet'), findsOneWidget);
      expect(find.byIcon(Icons.notifications_off_outlined), findsOneWidget);
    });

    testWidgets('renders notifications list with unread markers',
        (tester) async {
      final fakeService = FakeNotificationService(
        onGetNotifications: ({page = 1, pageSize = 20, isRead}) async {
          return NotificationListResponseModel(
            total: 2,
            unreadCount: 1,
            page: 1,
            pageSize: 20,
            totalPages: 1,
            notifications: [sampleNotif1, sampleNotif2],
          );
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: NotificationHistoryScreen(notificationService: fakeService),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Scheme Alert: PM-KISAN'), findsOneWidget);
      expect(
          find.text('17th installment of PM-KISAN released.'), findsOneWidget);
      expect(find.text('Biometrics Scheduled'), findsOneWidget);
      expect(find.byKey(const Key('mark_all_read_button')), findsOneWidget);
    });

    testWidgets('tapping notification calls markAsRead', (tester) async {
      String? markedId;

      final fakeService = FakeNotificationService(
        onGetNotifications: ({page = 1, pageSize = 20, isRead}) async {
          return NotificationListResponseModel(
            total: 1,
            unreadCount: 1,
            page: 1,
            pageSize: 20,
            totalPages: 1,
            notifications: [sampleNotif1],
          );
        },
        onMarkAsRead: (id) async {
          markedId = id;
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: NotificationHistoryScreen(notificationService: fakeService),
        ),
      );

      await tester.pumpAndSettle();

      // Tap the unread notification
      await tester.tap(find.byKey(const Key('notification_item_notif-1')));
      await tester.pumpAndSettle();

      expect(markedId, 'notif-1');
    });

    testWidgets('mark all as read button updates notifications',
        (tester) async {
      bool allMarked = false;

      final fakeService = FakeNotificationService(
        onGetNotifications: ({page = 1, pageSize = 20, isRead}) async {
          return NotificationListResponseModel(
            total: 1,
            unreadCount: 1,
            page: 1,
            pageSize: 20,
            totalPages: 1,
            notifications: [sampleNotif1],
          );
        },
        onMarkAllAsRead: () async {
          allMarked = true;
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: NotificationHistoryScreen(notificationService: fakeService),
        ),
      );

      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('mark_all_read_button')));
      await tester.pumpAndSettle();

      expect(allMarked, isTrue);
    });
  });
}
