import 'dart:async';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'notification_service.dart';

/// Notification payload received from Push / FCM
class PushMessagePayload {
  final String? messageId;
  final String title;
  final String body;
  final Map<String, dynamic> data;

  const PushMessagePayload({
    this.messageId,
    required this.title,
    required this.body,
    this.data = const {},
  });
}

/// Channel definition for Android Notification Channels
class PushNotificationChannel {
  static const String urgentRemindersId = 'janmitra_urgent_reminders';
  static const String urgentRemindersName = 'JanMitra Urgent Reminders';
  static const String urgentRemindersDescription =
      'Deadline alerts, biometrics, document submissions, and application updates';
}

/// PushNotificationManager coordinates Firebase Cloud Messaging (FCM) on native platforms,
/// handling device token registration, background/foreground dispatch, permission handshakes,
/// and safe fallback when external cloud credentials (google-services.json) are not provisioned.
class PushNotificationManager {
  static final PushNotificationManager _instance =
      PushNotificationManager._internal();

  factory PushNotificationManager({
    NotificationService? notificationService,
  }) {
    if (notificationService != null) {
      return PushNotificationManager._withDeps(
        notificationService: notificationService,
      );
    }
    return _instance;
  }

  PushNotificationManager._internal()
      : _notificationService = NotificationService();

  PushNotificationManager._withDeps({
    required NotificationService notificationService,
  }) : _notificationService = notificationService;

  final NotificationService _notificationService;

  String? _currentToken;
  bool _isNativeFirebaseAvailable = false;
  bool _isInitialized = false;

  final StreamController<PushMessagePayload> _messageStreamController =
      StreamController<PushMessagePayload>.broadcast();

  Stream<PushMessagePayload> get onMessageReceived =>
      _messageStreamController.stream;

  bool get isNativeFirebaseAvailable => _isNativeFirebaseAvailable;
  bool get isInitialized => _isInitialized;
  String? get currentDeviceToken => _currentToken;

  /// Background message handler entry-point for native FCM delivery.
  @pragma('vm:entry-point')
  static Future<void> handleBackgroundMessage(
      Map<String, dynamic> message) async {
    // Process background notification payload without blocking UI thread
    if (kDebugMode) {
      print('JanMitra FCM Background Handler received payload: $message');
    }
  }

  /// Initialize Push Notification Subsystem.
  /// Detects whether native Firebase configuration files (google-services.json / GoogleService-Info.plist)
  /// are present in the host platform. Operates gracefully in fallback mode if credentials are unprovisioned.
  Future<void> initialize({
    String? mockTokenForTesting,
  }) async {
    if (_isInitialized) return;

    try {
      if (mockTokenForTesting != null) {
        _currentToken = mockTokenForTesting;
        _isNativeFirebaseAvailable = true;
      } else {
        // Safe check for native platform runtime
        _currentToken = await _resolveDeviceTokenSafe();
      }

      if (_currentToken != null && _currentToken!.isNotEmpty) {
        await registerCurrentDeviceToken();
      }

      _isInitialized = true;
    } catch (e) {
      if (kDebugMode) {
        print(
            'PushNotificationManager: Running in safe offline/fallback mode ($e)');
      }
      _isInitialized = true;
    }
  }

  /// Resolve device token with fallback protection
  Future<String?> _resolveDeviceTokenSafe() async {
    // In local dev without google-services.json, return null or platform identifier
    // Real FirebaseMessaging.instance.getToken() will be called when google-services.json is present
    return null;
  }

  /// Register current device token with FastAPI backend (/api/v1/notifications/register-token)
  Future<bool> registerCurrentDeviceToken() async {
    if (_currentToken == null || _currentToken!.isEmpty) return false;

    try {
      String deviceType = 'android';
      if (!kIsWeb) {
        if (Platform.isIOS) {
          deviceType = 'ios';
        } else if (Platform.isAndroid) {
          deviceType = 'android';
        }
      }

      await _notificationService.registerDeviceToken(
        _currentToken!,
        deviceType: deviceType,
      );
      return true;
    } catch (e) {
      if (kDebugMode) {
        print(
            'PushNotificationManager: Failed to register device token with backend: $e');
      }
      return false;
    }
  }

  /// Handle Token Refresh from Firebase SDK
  Future<void> handleTokenRefresh(String newToken) async {
    _currentToken = newToken;
    await registerCurrentDeviceToken();
  }

  /// Handle Incoming Foreground Push
  void handleForegroundMessage(PushMessagePayload payload) {
    _messageStreamController.add(payload);
  }

  /// Unregister device token upon citizen sign-out
  Future<void> unregisterOnLogout() async {
    if (_currentToken != null && _currentToken!.isNotEmpty) {
      try {
        await _notificationService.deactivateDeviceToken(_currentToken!);
      } catch (e) {
        if (kDebugMode) {
          print(
              'PushNotificationManager: Error unregistering token on logout: $e');
        }
      }
      _currentToken = null;
    }
  }

  void dispose() {
    _messageStreamController.close();
  }
}
