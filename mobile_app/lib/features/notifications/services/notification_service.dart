import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

import '../../../../core/network/api_endpoints.dart';
import '../../../../core/network/auth_service.dart';
import '../../../../core/services/secure_storage_service.dart';
import '../models/notification_models.dart';

class NotificationService {
  static final NotificationService _instance = NotificationService._internal();

  factory NotificationService({
    http.Client? client,
    SecureStorageService? storage,
    AuthService? authService,
  }) {
    if (client != null || storage != null || authService != null) {
      return NotificationService._withDeps(
        client: client ?? http.Client(),
        storage: storage ?? SecureStorageService(),
        authService: authService ?? AuthService(),
      );
    }
    return _instance;
  }

  NotificationService._internal()
      : _client = http.Client(),
        _storage = SecureStorageService(),
        _authService = AuthService(),
        _isClientOwned = true;

  NotificationService._withDeps({
    required http.Client client,
    required SecureStorageService storage,
    required AuthService authService,
  })  : _client = client,
        _storage = storage,
        _authService = authService,
        _isClientOwned = false;

  final http.Client _client;
  final SecureStorageService _storage;
  final AuthService _authService;
  final bool _isClientOwned;

  void dispose() {
    if (_isClientOwned) {
      _client.close();
    }
  }

  Map<String, String> _buildHeaders({String? token}) {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  Future<http.Response> _sendRequest(
    String method,
    Uri uri, {
    Map<String, dynamic>? body,
  }) async {
    String? token = await _storage.getAccessToken();
    var headers = _buildHeaders(token: token);

    http.Response response;
    final encodedBody = body != null ? jsonEncode(body) : null;

    try {
      switch (method.toUpperCase()) {
        case 'GET':
          response = await _client.get(uri, headers: headers);
          break;
        case 'POST':
          response =
              await _client.post(uri, headers: headers, body: encodedBody);
          break;
        case 'PATCH':
          response =
              await _client.patch(uri, headers: headers, body: encodedBody);
          break;
        case 'DELETE':
          response = await _client.delete(uri, headers: headers);
          break;
        default:
          throw UnsupportedError('Unsupported HTTP method: $method');
      }
    } on SocketException {
      throw Exception('Cannot connect to JanMitra server.');
    } on http.ClientException {
      throw Exception('Network connection error.');
    }

    if (response.statusCode == 401) {
      final refreshed = await _authService.refreshToken();
      if (refreshed != null) {
        token = refreshed.accessToken;
        headers = _buildHeaders(token: token);
        switch (method.toUpperCase()) {
          case 'GET':
            response = await _client.get(uri, headers: headers);
            break;
          case 'POST':
            response =
                await _client.post(uri, headers: headers, body: encodedBody);
            break;
          case 'PATCH':
            response =
                await _client.patch(uri, headers: headers, body: encodedBody);
            break;
          case 'DELETE':
            response = await _client.delete(uri, headers: headers);
            break;
        }
      }
    }

    return response;
  }

  Future<void> registerDeviceToken(String deviceToken,
      {String deviceType = 'android'}) async {
    final uri =
        Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.notificationDevices}');
    await _sendRequest('POST', uri, body: {
      'device_token': deviceToken,
      'device_type': deviceType,
    });
  }

  Future<void> deactivateDeviceToken(String deviceToken) async {
    final uri = Uri.parse(
        '${ApiEndpoints.baseUrl}${ApiEndpoints.notificationDeviceDetail(deviceToken)}');
    await _sendRequest('DELETE', uri);
  }

  Future<NotificationListResponseModel> getNotifications({
    int page = 1,
    int pageSize = 20,
    bool? isRead,
  }) async {
    final queryParams = <String, String>{
      'page': page.toString(),
      'page_size': pageSize.toString(),
    };
    if (isRead != null) {
      queryParams['is_read'] = isRead ? 'true' : 'false';
    }

    final baseUri =
        Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.notifications}');
    final uri = baseUri.replace(queryParameters: queryParams);

    final response = await _sendRequest('GET', uri);
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return NotificationListResponseModel.fromJson(data);
    } else {
      throw Exception('Failed to load notifications: ${response.statusCode}');
    }
  }

  Future<void> markAsRead(String notificationId) async {
    final uri = Uri.parse(
        '${ApiEndpoints.baseUrl}${ApiEndpoints.notificationRead(notificationId)}');
    await _sendRequest('PATCH', uri);
  }

  Future<void> markAllAsRead() async {
    final uri = Uri.parse(
        '${ApiEndpoints.baseUrl}${ApiEndpoints.notificationsReadAll}');
    await _sendRequest('POST', uri);
  }

  Future<int> getUnreadCount() async {
    try {
      final uri = Uri.parse(
          '${ApiEndpoints.baseUrl}${ApiEndpoints.notificationsUnreadCount}');
      final response = await _sendRequest('GET', uri);
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return (data['unread_count'] as num?)?.toInt() ?? 0;
      }
    } catch (_) {}
    return 0;
  }
}
