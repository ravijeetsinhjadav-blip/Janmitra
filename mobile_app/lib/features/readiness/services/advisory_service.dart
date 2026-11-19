import 'dart:convert';
import 'package:http/http.dart' as http;
import '../../../core/network/api_endpoints.dart';
import '../../../core/services/secure_storage_service.dart';
import '../models/advisory_models.dart';

class AdvisoryService {
  static final AdvisoryService _instance = AdvisoryService._internal();
  factory AdvisoryService() => _instance;
  AdvisoryService._internal();

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

  /// Run deterministic eligibility evaluation, readiness scoring, and AI advisory generation
  Future<AdvisoryAssessmentModel> assessAndAdvise(
    String schemeId, {
    String language = 'en',
  }) async {
    final uri = Uri.parse(
      '${ApiEndpoints.baseUrl}${ApiEndpoints.schemeAssessAndAdvise(schemeId)}',
    );
    final headers = await _buildHeaders();
    final body = jsonEncode({'language': language});

    final response = await http.post(uri, headers: headers, body: body);
    final data = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode == 200 || response.statusCode == 201) {
      return AdvisoryAssessmentModel.fromJson(data);
    } else {
      final msg = data['detail'] ?? 'Failed to generate advisory evaluation';
      throw Exception(msg);
    }
  }

  /// Retrieve existing AI advisory and readiness report by assessment ID
  Future<AdvisoryAssessmentModel> getAssessmentAdvisory(
      String assessmentId) async {
    final uri = Uri.parse(
      '${ApiEndpoints.baseUrl}${ApiEndpoints.assessmentAdvisory(assessmentId)}',
    );
    final headers = await _buildHeaders();

    final response = await http.get(uri, headers: headers);
    final data = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode == 200) {
      return AdvisoryAssessmentModel.fromJson(data);
    } else {
      final msg = data['detail'] ?? 'Failed to load advisory report';
      throw Exception(msg);
    }
  }

  /// Regenerate guidance in an alternative language (English, Hindi, Gujarati)
  Future<AdvisoryAssessmentModel> regenerateAdvisory(
    String assessmentId, {
    required String language,
  }) async {
    final uri = Uri.parse(
      '${ApiEndpoints.baseUrl}${ApiEndpoints.assessmentRegenerate(assessmentId)}',
    );
    final headers = await _buildHeaders();
    final body = jsonEncode({'language': language});

    final response = await http.post(uri, headers: headers, body: body);
    final data = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode == 200) {
      return AdvisoryAssessmentModel.fromJson(data);
    } else {
      final msg = data['detail'] ?? 'Failed to regenerate advisory report';
      throw Exception(msg);
    }
  }
}
