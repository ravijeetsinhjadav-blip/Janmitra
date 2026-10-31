import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import '../services/secure_storage_service.dart';
import 'api_endpoints.dart';
import '../../features/auth/models/auth_models.dart';
import '../../features/profile/models/user_profile_model.dart';

class AuthService {
  static final AuthService _instance = AuthService._internal();
  factory AuthService() => _instance;
  AuthService._internal();

  final SecureStorageService _storage = SecureStorageService();

  Map<String, String> _buildHeaders({String? token}) {
    final headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (token != null) {
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  /// Request OTP for mobile authentication
  Future<SendOtpResponseModel> sendOtp(String mobileNumber) async {
    final url = Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.authSendOtp}');
    try {
      final response = await http.post(
        url,
        headers: _buildHeaders(),
        body: jsonEncode({'mobile_number': mobileNumber}),
      );

      final data = jsonDecode(response.body) as Map<String, dynamic>;
      if (response.statusCode == 200) {
        return SendOtpResponseModel.fromJson(data);
      } else {
        final message = data['detail'] ?? data['message'] ?? 'Failed to send OTP';
        throw Exception(message);
      }
    } on SocketException {
      throw Exception('Cannot connect to JanMitra backend server. Please verify network and backend status.');
    }
  }

  /// Verify OTP and store tokens in secure storage
  Future<TokenResponseModel> verifyOtp(
    String mobileNumber,
    String otp, {
    String? deviceInfo,
  }) async {
    final url = Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.authVerifyOtp}');
    try {
      final response = await http.post(
        url,
        headers: _buildHeaders(),
        body: jsonEncode({
          'mobile_number': mobileNumber,
          'otp': otp,
          'device_info': deviceInfo ?? 'JanMitra Mobile Client',
        }),
      );

      final data = jsonDecode(response.body) as Map<String, dynamic>;
      if (response.statusCode == 200) {
        final tokenResponse = TokenResponseModel.fromJson(data);
        await _storage.saveAuthSession(
          accessToken: tokenResponse.accessToken,
          refreshToken: tokenResponse.refreshToken,
          userId: tokenResponse.userId,
          mobileNumber: mobileNumber,
          role: tokenResponse.role,
          profileCompleted: tokenResponse.profileCompleted,
        );
        return tokenResponse;
      } else {
        final message = data['detail'] ?? data['message'] ?? 'OTP verification failed';
        throw Exception(message);
      }
    } on SocketException {
      throw Exception('Cannot connect to JanMitra backend server. Please verify backend status.');
    }
  }

  /// Refresh token with rotation
  Future<TokenResponseModel?> refreshToken() async {
    final rawRefreshToken = await _storage.getRefreshToken();
    if (rawRefreshToken == null) return null;

    final url = Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.authRefresh}');
    try {
      final response = await http.post(
        url,
        headers: _buildHeaders(),
        body: jsonEncode({'refresh_token': rawRefreshToken}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        final tokenResponse = TokenResponseModel.fromJson(data);
        await _storage.updateTokens(
          accessToken: tokenResponse.accessToken,
          refreshToken: tokenResponse.refreshToken,
        );
        return tokenResponse;
      } else {
        await _storage.clearSession();
        return null;
      }
    } catch (_) {
      return null;
    }
  }

  /// Get current user with automatic token refresh on 401
  Future<UserModel> getCurrentUser() async {
    String? token = await _storage.getAccessToken();
    final url = Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.authMe}');

    var response = await http.get(url, headers: _buildHeaders(token: token));

    if (response.statusCode == 401) {
      final refreshed = await refreshToken();
      if (refreshed != null) {
        token = refreshed.accessToken;
        response = await http.get(url, headers: _buildHeaders(token: token));
      } else {
        throw Exception('Session expired. Please log in again.');
      }
    }

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return UserModel.fromJson(data);
    } else {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      throw Exception(data['detail'] ?? 'Failed to fetch user details');
    }
  }

  /// Get user profile
  Future<UserProfileModel?> getUserProfile() async {
    String? token = await _storage.getAccessToken();
    final url = Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.userProfile}');

    var response = await http.get(url, headers: _buildHeaders(token: token));

    if (response.statusCode == 401) {
      final refreshed = await refreshToken();
      if (refreshed != null) {
        token = refreshed.accessToken;
        response = await http.get(url, headers: _buildHeaders(token: token));
      } else {
        throw Exception('Session expired. Please log in again.');
      }
    }

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return UserProfileModel.fromJson(data);
    } else if (response.statusCode == 404) {
      return null;
    } else {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      throw Exception(data['detail'] ?? 'Failed to load profile');
    }
  }

  /// Create or update citizen profile
  Future<UserProfileModel> saveUserProfile(UserProfileModel profile) async {
    String? token = await _storage.getAccessToken();
    final url = Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.userProfile}');

    var response = await http.put(
      url,
      headers: _buildHeaders(token: token),
      body: jsonEncode(profile.toJson()),
    );

    if (response.statusCode == 401) {
      final refreshed = await refreshToken();
      if (refreshed != null) {
        token = refreshed.accessToken;
        response = await http.put(
          url,
          headers: _buildHeaders(token: token),
          body: jsonEncode(profile.toJson()),
        );
      } else {
        throw Exception('Session expired. Please log in again.');
      }
    }

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      await _storage.setProfileCompleted(true);
      return UserProfileModel.fromJson(data);
    } else {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      final detail = data['detail'];
      if (detail is List && detail.isNotEmpty) {
        throw Exception(detail[0]['msg'] ?? 'Validation error');
      }
      throw Exception(detail?.toString() ?? 'Failed to save profile');
    }
  }

  /// Logout and revoke refresh session
  Future<void> logout({bool allSessions = false}) async {
    final token = await _storage.getAccessToken();
    final refreshToken = await _storage.getRefreshToken();

    if (token != null && refreshToken != null) {
      final url = Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.authLogout}');
      try {
        await http.post(
          url,
          headers: _buildHeaders(token: token),
          body: jsonEncode({
            'refresh_token': refreshToken,
            'all_sessions': allSessions,
          }),
        );
      } catch (_) {
        // Proceed with local cleanup regardless of server errors
      }
    }

    await _storage.clearSession();
  }

  /// Request account deletion with 30-day retention
  Future<Map<String, dynamic>> requestAccountDeletion({String? reason}) async {
    String? token = await _storage.getAccessToken();
    final url = Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.userDeleteRequest}');

    var response = await http.post(
      url,
      headers: _buildHeaders(token: token),
      body: jsonEncode({'reason': reason}),
    );

    if (response.statusCode == 401) {
      final refreshed = await refreshToken();
      if (refreshed != null) {
        token = refreshed.accessToken;
        response = await http.post(
          url,
          headers: _buildHeaders(token: token),
          body: jsonEncode({'reason': reason}),
        );
      } else {
        throw Exception('Session expired. Please log in again.');
      }
    }

    if (response.statusCode == 201) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      await _storage.clearSession();
      return data;
    } else {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      throw Exception(data['detail'] ?? 'Failed to submit deletion request');
    }
  }
}
