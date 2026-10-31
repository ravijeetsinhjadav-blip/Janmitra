import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Secure token and session persistence using FlutterSecureStorage.
/// Strictly enforces security requirement: access and refresh tokens are
/// NEVER stored in SharedPreferences.
class SecureStorageService {
  static const _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
    iOptions: IOSOptions(accessibility: KeychainAccessibility.first_unlock),
  );

  static const String _keyAccessToken = 'janmitra_access_token';
  static const String _keyRefreshToken = 'janmitra_refresh_token';
  static const String _keyUserId = 'janmitra_user_id';
  static const String _keyMobileNumber = 'janmitra_mobile_number';
  static const String _keyUserRole = 'janmitra_user_role';
  static const String _keyProfileCompleted = 'janmitra_profile_completed';

  // Singleton instance
  static final SecureStorageService _instance = SecureStorageService._internal();
  factory SecureStorageService() => _instance;
  SecureStorageService._internal();

  /// Save tokens and auth metadata after OTP verification or token refresh
  Future<void> saveAuthSession({
    required String accessToken,
    required String refreshToken,
    String? userId,
    String? mobileNumber,
    String? role,
    bool? profileCompleted,
  }) async {
    await _storage.write(key: _keyAccessToken, value: accessToken);
    await _storage.write(key: _keyRefreshToken, value: refreshToken);
    if (userId != null) {
      await _storage.write(key: _keyUserId, value: userId);
    }
    if (mobileNumber != null) {
      await _storage.write(key: _keyMobileNumber, value: mobileNumber);
    }
    if (role != null) {
      await _storage.write(key: _keyUserRole, value: role);
    }
    if (profileCompleted != null) {
      await _storage.write(
        key: _keyProfileCompleted,
        value: profileCompleted ? 'true' : 'false',
      );
    }
  }

  /// Update only access token (e.g. after refresh)
  Future<void> updateTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    await _storage.write(key: _keyAccessToken, value: accessToken);
    await _storage.write(key: _keyRefreshToken, value: refreshToken);
  }

  /// Mark profile completion status
  Future<void> setProfileCompleted(bool completed) async {
    await _storage.write(
      key: _keyProfileCompleted,
      value: completed ? 'true' : 'false',
    );
  }

  Future<String?> getAccessToken() async => await _storage.read(key: _keyAccessToken);
  Future<String?> getRefreshToken() async => await _storage.read(key: _keyRefreshToken);
  Future<String?> getUserId() async => await _storage.read(key: _keyUserId);
  Future<String?> getMobileNumber() async => await _storage.read(key: _keyMobileNumber);
  Future<String?> getUserRole() async => await _storage.read(key: _keyUserRole);

  Future<bool> isProfileCompleted() async {
    final value = await _storage.read(key: _keyProfileCompleted);
    return value == 'true';
  }

  Future<bool> hasValidSession() async {
    final refreshToken = await getRefreshToken();
    return refreshToken != null && refreshToken.isNotEmpty;
  }

  /// Clear all stored tokens and session data on logout or account deletion
  Future<void> clearSession() async {
    await _storage.delete(key: _keyAccessToken);
    await _storage.delete(key: _keyRefreshToken);
    await _storage.delete(key: _keyUserId);
    await _storage.delete(key: _keyMobileNumber);
    await _storage.delete(key: _keyUserRole);
    await _storage.delete(key: _keyProfileCompleted);
  }
}

