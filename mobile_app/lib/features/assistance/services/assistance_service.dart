import 'dart:convert';
import 'package:http/http.dart' as http;
import '../../../core/network/api_endpoints.dart';
import '../../../core/services/secure_storage_service.dart';
import '../models/assistance_models.dart';

class AssistanceService {
  static final AssistanceService _instance = AssistanceService._internal();
  factory AssistanceService() => _instance;
  AssistanceService._internal();

  final SecureStorageService _storage = SecureStorageService();

  Future<Map<String, String>> _buildHeaders() async {
    final token = await _storage.getAccessToken();
    final headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (token != null) {
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  /// Generate or retrieve personalized application preparation assistance for a scheme
  Future<ApplicationAssistanceModel> prepareApplication(
    String schemeId, {
    String language = 'en',
  }) async {
    final uri = Uri.parse(
      '${ApiEndpoints.baseUrl}${ApiEndpoints.schemeAssistancePrepare(schemeId)}',
    );
    final headers = await _buildHeaders();
    final body = jsonEncode({'language': language});

    final response = await http.post(uri, headers: headers, body: body);
    final data = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode == 200 || response.statusCode == 201) {
      return ApplicationAssistanceModel.fromJson(data);
    } else {
      final msg = data['detail'] ?? 'Failed to prepare application assistance';
      throw Exception(msg);
    }
  }

  /// Toggle preparation checklist item completion state and persist to assessment
  Future<ChecklistUpdateResponseModel> toggleChecklistItem({
    required String schemeId,
    required String itemId,
    required bool isCompleted,
  }) async {
    final uri = Uri.parse(
      '${ApiEndpoints.baseUrl}${ApiEndpoints.schemeAssistanceChecklistToggle(schemeId, itemId)}',
    );
    final headers = await _buildHeaders();
    final body = jsonEncode({'is_completed': isCompleted});

    final response = await http.patch(uri, headers: headers, body: body);
    final data = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode == 200) {
      return ChecklistUpdateResponseModel.fromJson(data);
    } else {
      final msg = data['detail'] ?? 'Failed to update checklist item';
      throw Exception(msg);
    }
  }

  /// Retrieve general information guide for a scheme
  Future<ApplicationInfoGuideModel> getSchemeGuide(
    String schemeId, {
    String language = 'en',
  }) async {
    final uri = Uri.parse(
      '${ApiEndpoints.baseUrl}${ApiEndpoints.schemeAssistanceGuide(schemeId)}?language=$language',
    );
    final headers = await _buildHeaders();

    final response = await http.get(uri, headers: headers);
    final data = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode == 200) {
      return ApplicationInfoGuideModel.fromJson(data);
    } else {
      final msg = data['detail'] ?? 'Failed to load scheme application guide';
      throw Exception(msg);
    }
  }
}

