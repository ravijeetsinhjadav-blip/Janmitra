import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

import '../../../../core/network/api_endpoints.dart';
import '../../../../core/network/auth_service.dart';
import '../../../../core/services/secure_storage_service.dart';
import '../models/application_models.dart';

/// Network service for JanMitra Application Tracking, Status History, and Reminders.
/// Connects citizen mobile client to FastAPI backend endpoints with automatic
/// single-pass 401 token refresh retry and strict caller user isolation.
class ApplicationService {
  static final ApplicationService _instance = ApplicationService._internal();

  factory ApplicationService({
    http.Client? client,
    SecureStorageService? storage,
    AuthService? authService,
  }) {
    if (client != null || storage != null || authService != null) {
      return ApplicationService._withDeps(
        client: client ?? http.Client(),
        storage: storage ?? SecureStorageService(),
        authService: authService ?? AuthService(),
      );
    }
    return _instance;
  }

  ApplicationService._internal()
      : _client = http.Client(),
        _storage = SecureStorageService(),
        _authService = AuthService(),
        _isClientOwned = true;

  ApplicationService._withDeps({
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

  /// Dispose client when owned by service instance
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

  String _parseErrorMessage(http.Response response) {
    try {
      final body = jsonDecode(response.body);
      if (body is Map<String, dynamic>) {
        final detail = body['detail'];
        if (detail is String && detail.trim().isNotEmpty) {
          return detail.trim();
        } else if (detail is List && detail.isNotEmpty) {
          final messages = detail
              .map((err) {
                if (err is Map<String, dynamic> && err['msg'] != null) {
                  return err['msg'].toString();
                }
                return err.toString();
              })
              .where((m) => m.isNotEmpty)
              .toList();
          if (messages.isNotEmpty) {
            return messages.join('; ');
          }
        }
        final message = body['message'];
        if (message is String && message.trim().isNotEmpty) {
          return message.trim();
        }
      }
    } catch (_) {
      // Malformed or non-JSON body (e.g. HTML 502/504)
    }
    return 'Server returned error status ${response.statusCode}';
  }

  Future<http.Response> _executeHttp(
    String method,
    Uri uri,
    Map<String, String> headers,
    Map<String, dynamic>? body,
  ) async {
    final encodedBody = body != null ? jsonEncode(body) : null;
    switch (method.toUpperCase()) {
      case 'GET':
        return await _client.get(uri, headers: headers);
      case 'POST':
        return await _client.post(uri, headers: headers, body: encodedBody);
      case 'PATCH':
        return await _client.patch(uri, headers: headers, body: encodedBody);
      case 'DELETE':
        return await _client.delete(uri, headers: headers);
      default:
        throw UnsupportedError('Unsupported HTTP method: $method');
    }
  }

  /// Sends HTTP request with automatic 401 token refresh and single-pass retry.
  Future<http.Response> _sendRequest(
    String method,
    Uri uri, {
    Map<String, dynamic>? body,
  }) async {
    String? token = await _storage.getAccessToken();
    var headers = _buildHeaders(token: token);

    http.Response response;
    try {
      response = await _executeHttp(method, uri, headers, body)
          .timeout(const Duration(seconds: 15));
    } on SocketException {
      throw Exception(
          'Cannot connect to JanMitra server. Please verify your connection.');
    } on http.ClientException {
      throw Exception('Network connection error. Please try again.');
    } on TimeoutException {
      throw Exception('Request timed out while connecting to JanMitra server.');
    }

    if (response.statusCode == 401) {
      final refreshed = await _authService.refreshToken();
      if (refreshed != null) {
        token = refreshed.accessToken;
        headers = _buildHeaders(token: token);
        try {
          response = await _executeHttp(method, uri, headers, body)
              .timeout(const Duration(seconds: 15));
        } on SocketException {
          throw Exception(
              'Cannot connect to JanMitra server. Please verify your connection.');
        } on http.ClientException {
          throw Exception('Network connection error. Please try again.');
        } on TimeoutException {
          throw Exception(
              'Request timed out while connecting to JanMitra server.');
        }

        if (response.statusCode == 401) {
          throw Exception('Session expired. Please log in again.');
        }
      } else {
        throw Exception('Session expired. Please log in again.');
      }
    }

    return response;
  }

  // ---------------------------------------------------------------------------
  // 1. Applications Collection & Detail Operations
  // ---------------------------------------------------------------------------

  /// Register an application already submitted on an official government portal.
  /// Backend assigns citizen ownership and initializes status to 'Submitted'.
  Future<ApplicationModel> createApplication(
    ApplicationCreateRequestModel request,
  ) async {
    final uri =
        Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.applications}');
    final response = await _sendRequest('POST', uri, body: request.toJson());

    if (response.statusCode == 201) {
      try {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return ApplicationModel.fromJson(data);
      } catch (e) {
        throw Exception('Malformed response received from server.');
      }
    } else {
      throw Exception(_parseErrorMessage(response));
    }
  }

  /// List citizen's tracked applications with optional status filter and pagination.
  Future<ApplicationListResponseModel> getApplications({
    String? status,
    String? schemeId,
    int page = 1,
    int pageSize = 20,
  }) async {
    final queryParams = <String, String>{
      'page': page.toString(),
      'page_size': pageSize.toString(),
    };
    if (status != null && status.trim().isNotEmpty && status != 'All') {
      queryParams['status'] = status.trim();
    }
    if (schemeId != null && schemeId.trim().isNotEmpty) {
      queryParams['scheme_id'] = schemeId.trim();
    }

    final baseUri =
        Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.applications}');
    final uri = baseUri.replace(queryParameters: queryParams);

    final response = await _sendRequest('GET', uri);

    if (response.statusCode == 200) {
      try {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return ApplicationListResponseModel.fromJson(data);
      } catch (e) {
        throw Exception('Malformed response received from server.');
      }
    } else {
      throw Exception(_parseErrorMessage(response));
    }
  }

  /// Fetch full details of an individual application tracking record.
  Future<ApplicationModel> getApplicationById(String applicationId) async {
    final uri = Uri.parse(
      '${ApiEndpoints.baseUrl}${ApiEndpoints.applicationDetail(applicationId)}',
    );
    final response = await _sendRequest('GET', uri);

    if (response.statusCode == 200) {
      try {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return ApplicationModel.fromJson(data);
      } catch (e) {
        throw Exception('Malformed response received from server.');
      }
    } else {
      throw Exception(_parseErrorMessage(response));
    }
  }

  /// Atomically update status, remarks, reference number, or submission date.
  Future<ApplicationModel> updateApplication(
    String applicationId,
    ApplicationUpdateRequestModel request,
  ) async {
    final uri = Uri.parse(
      '${ApiEndpoints.baseUrl}${ApiEndpoints.applicationDetail(applicationId)}',
    );
    final response = await _sendRequest('PATCH', uri, body: request.toJson());

    if (response.statusCode == 200) {
      try {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return ApplicationModel.fromJson(data);
      } catch (e) {
        throw Exception('Malformed response received from server.');
      }
    } else {
      throw Exception(_parseErrorMessage(response));
    }
  }

  /// Delete local tracking entry (does not cancel official government application).
  Future<ApplicationDeleteResponseModel> deleteApplication(
    String applicationId,
  ) async {
    final uri = Uri.parse(
      '${ApiEndpoints.baseUrl}${ApiEndpoints.applicationDetail(applicationId)}',
    );
    final response = await _sendRequest('DELETE', uri);

    if (response.statusCode == 200) {
      try {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return ApplicationDeleteResponseModel.fromJson(data);
      } catch (e) {
        throw Exception('Malformed response received from server.');
      }
    } else {
      throw Exception(_parseErrorMessage(response));
    }
  }

  // ---------------------------------------------------------------------------
  // 2. Status History & Audit Ledger Operations
  // ---------------------------------------------------------------------------

  /// Retrieve chronological immutable audit trail of manual status updates and remarks.
  Future<ApplicationStatusHistoryListModel> getApplicationHistory(
    String applicationId,
  ) async {
    final uri = Uri.parse(
      '${ApiEndpoints.baseUrl}${ApiEndpoints.applicationHistory(applicationId)}',
    );
    final response = await _sendRequest('GET', uri);

    if (response.statusCode == 200) {
      try {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return ApplicationStatusHistoryListModel.fromJson(data);
      } catch (e) {
        throw Exception('Malformed response received from server.');
      }
    } else {
      throw Exception(_parseErrorMessage(response));
    }
  }

  // ---------------------------------------------------------------------------
  // 3. Reminders Operations
  // ---------------------------------------------------------------------------

  /// Retrieve all active uncompleted reminders across all applications for citizen.
  Future<ReminderListResponseModel> getUpcomingReminders() async {
    final uri = Uri.parse(
      '${ApiEndpoints.baseUrl}${ApiEndpoints.applicationUpcomingReminders}',
    );
    final response = await _sendRequest('GET', uri);

    if (response.statusCode == 200) {
      try {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return ReminderListResponseModel.fromJson(data);
      } catch (e) {
        throw Exception('Malformed response received from server.');
      }
    } else {
      throw Exception(_parseErrorMessage(response));
    }
  }

  /// Create a task or deadline reminder associated with an owned application.
  Future<ReminderModel> createReminder(
    String applicationId,
    ReminderCreateRequestModel request,
  ) async {
    final uri = Uri.parse(
      '${ApiEndpoints.baseUrl}${ApiEndpoints.applicationReminders(applicationId)}',
    );
    final response = await _sendRequest('POST', uri, body: request.toJson());

    if (response.statusCode == 201) {
      try {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return ReminderModel.fromJson(data);
      } catch (e) {
        throw Exception('Malformed response received from server.');
      }
    } else {
      throw Exception(_parseErrorMessage(response));
    }
  }

  /// List reminders associated with a specific application.
  Future<ReminderListResponseModel> getApplicationReminders(
    String applicationId, {
    bool? isCompleted,
  }) async {
    final baseUri = Uri.parse(
      '${ApiEndpoints.baseUrl}${ApiEndpoints.applicationReminders(applicationId)}',
    );
    final queryParams = <String, String>{};
    if (isCompleted != null) {
      queryParams['is_completed'] = isCompleted ? 'true' : 'false';
    }
    final uri = queryParams.isNotEmpty
        ? baseUri.replace(queryParameters: queryParams)
        : baseUri;

    final response = await _sendRequest('GET', uri);

    if (response.statusCode == 200) {
      try {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return ReminderListResponseModel.fromJson(data);
      } catch (e) {
        throw Exception('Malformed response received from server.');
      }
    } else {
      throw Exception(_parseErrorMessage(response));
    }
  }

  /// Retrieve specific reminder details validating application and user ownership.
  Future<ReminderModel> getReminderById(
    String applicationId,
    String reminderId,
  ) async {
    final uri = Uri.parse(
      '${ApiEndpoints.baseUrl}${ApiEndpoints.applicationReminderDetail(applicationId, reminderId)}',
    );
    final response = await _sendRequest('GET', uri);

    if (response.statusCode == 200) {
      try {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return ReminderModel.fromJson(data);
      } catch (e) {
        throw Exception('Malformed response received from server.');
      }
    } else {
      throw Exception(_parseErrorMessage(response));
    }
  }

  /// Update reminder details or toggle completion status.
  Future<ReminderModel> updateReminder(
    String applicationId,
    String reminderId,
    ReminderUpdateRequestModel request,
  ) async {
    final uri = Uri.parse(
      '${ApiEndpoints.baseUrl}${ApiEndpoints.applicationReminderDetail(applicationId, reminderId)}',
    );
    final response = await _sendRequest('PATCH', uri, body: request.toJson());

    if (response.statusCode == 200) {
      try {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return ReminderModel.fromJson(data);
      } catch (e) {
        throw Exception('Malformed response received from server.');
      }
    } else {
      throw Exception(_parseErrorMessage(response));
    }
  }

  /// Permanently delete an application reminder.
  Future<ReminderDeleteResponseModel> deleteReminder(
    String applicationId,
    String reminderId,
  ) async {
    final uri = Uri.parse(
      '${ApiEndpoints.baseUrl}${ApiEndpoints.applicationReminderDetail(applicationId, reminderId)}',
    );
    final response = await _sendRequest('DELETE', uri);

    if (response.statusCode == 200) {
      try {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return ReminderDeleteResponseModel.fromJson(data);
      } catch (e) {
        throw Exception('Malformed response received from server.');
      }
    } else {
      throw Exception(_parseErrorMessage(response));
    }
  }
}
