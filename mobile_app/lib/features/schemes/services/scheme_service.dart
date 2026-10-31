import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import '../../../core/network/api_endpoints.dart';
import '../../../core/services/secure_storage_service.dart';
import '../models/scheme_models.dart';

class SchemeService {
  static final SchemeService _instance = SchemeService._internal();
  factory SchemeService() => _instance;
  SchemeService._internal();

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

  /// Discover schemes with optional query, category, state filters and pagination
  Future<SchemeListResponseModel> getSchemes({
    String? query,
    String? category,
    String? state,
    int page = 1,
    int pageSize = 20,
  }) async {
    final queryParams = <String, String>{
      'page': page.toString(),
      'page_size': pageSize.toString(),
    };
    if (query != null && query.trim().isNotEmpty) {
      queryParams['q'] = query.trim();
    }
    if (category != null && category.trim().isNotEmpty && category != 'All') {
      queryParams['category'] = category.trim();
    }
    if (state != null && state.trim().isNotEmpty && state != 'All') {
      queryParams['state'] = state.trim();
    }

    final uri = Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.schemes}')
        .replace(queryParameters: queryParams);

    try {
      final headers = await _buildHeaders();
      final response = await http.get(uri, headers: headers);
      final data = jsonDecode(response.body) as Map<String, dynamic>;

      if (response.statusCode == 200) {
        return SchemeListResponseModel.fromJson(data);
      } else {
        final message = data['detail'] ?? 'Failed to load schemes';
        throw Exception(message);
      }
    } on SocketException {
      throw Exception('Cannot connect to JanMitra server. Check your network or backend service.');
    }
  }

  /// Get aggregated scheme categories
  Future<List<SchemeCategoryModel>> getCategories() async {
    final uri = Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.schemeCategories}');
    try {
      final headers = await _buildHeaders();
      final response = await http.get(uri, headers: headers);
      if (response.statusCode == 200) {
        final list = jsonDecode(response.body) as List<dynamic>;
        return list.map((e) => SchemeCategoryModel.fromJson(e as Map<String, dynamic>)).toList();
      } else {
        throw Exception('Failed to load scheme categories');
      }
    } on SocketException {
      throw Exception('Cannot connect to JanMitra server.');
    }
  }

  /// Get complete details of a single scheme
  Future<SchemeModel> getSchemeById(String schemeId) async {
    final uri = Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.schemeDetail(schemeId)}');
    try {
      final headers = await _buildHeaders();
      final response = await http.get(uri, headers: headers);
      final data = jsonDecode(response.body) as Map<String, dynamic>;

      if (response.statusCode == 200) {
        return SchemeModel.fromJson(data);
      } else {
        final message = data['detail'] ?? 'Government scheme not found.';
        throw Exception(message);
      }
    } on SocketException {
      throw Exception('Cannot connect to JanMitra server.');
    }
  }

  /// Fetch tailored scheme recommendations based on citizen profile
  Future<List<SchemeRecommendationModel>> getRecommendations() async {
    final uri = Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.schemeRecommendations}');
    try {
      final headers = await _buildHeaders();
      final response = await http.get(uri, headers: headers);

      if (response.statusCode == 200) {
        final list = jsonDecode(response.body) as List<dynamic>;
        return list.map((e) => SchemeRecommendationModel.fromJson(e as Map<String, dynamic>)).toList();
      } else {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        throw Exception(data['detail'] ?? 'Failed to load recommendations.');
      }
    } on SocketException {
      throw Exception('Cannot connect to JanMitra server.');
    }
  }

  /// Run deterministic eligibility assessment for authenticated citizen
  Future<AssessmentResultModel> runAssessment(String schemeId) async {
    final uri = Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.schemeAssess(schemeId)}');
    try {
      final headers = await _buildHeaders();
      final response = await http.post(uri, headers: headers);
      final data = jsonDecode(response.body) as Map<String, dynamic>;

      if (response.statusCode == 200 || response.statusCode == 201) {
        return AssessmentResultModel.fromJson(data);
      } else {
        final message = data['detail'] ?? 'Failed to execute eligibility assessment.';
        throw Exception(message);
      }
    } on SocketException {
      throw Exception('Cannot connect to JanMitra server.');
    }
  }

  /// Retrieve citizen's past assessment history
  Future<List<AssessmentHistoryItemModel>> getAssessmentHistory({
    int page = 1,
    int pageSize = 20,
  }) async {
    final queryParams = {
      'page': page.toString(),
      'page_size': pageSize.toString(),
    };
    final uri = Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.schemeAssessmentsHistory}')
        .replace(queryParameters: queryParams);

    try {
      final headers = await _buildHeaders();
      final response = await http.get(uri, headers: headers);

      if (response.statusCode == 200) {
        final list = jsonDecode(response.body) as List<dynamic>;
        return list.map((e) => AssessmentHistoryItemModel.fromJson(e as Map<String, dynamic>)).toList();
      } else {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        throw Exception(data['detail'] ?? 'Failed to load assessment history.');
      }
    } on SocketException {
      throw Exception('Cannot connect to JanMitra server.');
    }
  }

  /// Retrieve detailed past assessment result
  Future<AssessmentResultModel> getAssessmentDetail(String assessmentId) async {
    final uri = Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.schemeAssessmentDetail(assessmentId)}');
    try {
      final headers = await _buildHeaders();
      final response = await http.get(uri, headers: headers);
      final data = jsonDecode(response.body) as Map<String, dynamic>;

      if (response.statusCode == 200) {
        return AssessmentResultModel.fromJson(data);
      } else {
        throw Exception(data['detail'] ?? 'Assessment not found.');
      }
    } on SocketException {
      throw Exception('Cannot connect to JanMitra server.');
    }
  }
}

