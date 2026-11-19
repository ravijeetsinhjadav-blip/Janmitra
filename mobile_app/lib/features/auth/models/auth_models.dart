import '../../profile/models/user_profile_model.dart';

class TokenResponseModel {
  final String accessToken;
  final String refreshToken;
  final String tokenType;
  final int expiresIn;
  final bool isNewUser;
  final String userId;
  final String? email;
  final String role;
  final bool profileCompleted;

  TokenResponseModel({
    required this.accessToken,
    required this.refreshToken,
    required this.tokenType,
    required this.expiresIn,
    required this.isNewUser,
    required this.userId,
    this.email,
    required this.role,
    required this.profileCompleted,
  });

  factory TokenResponseModel.fromJson(Map<String, dynamic> json) {
    return TokenResponseModel(
      accessToken: json['access_token'] as String,
      refreshToken: json['refresh_token'] as String,
      tokenType: json['token_type'] as String? ?? 'bearer',
      expiresIn: json['expires_in'] as int? ?? 1800,
      isNewUser: json['is_new_user'] as bool? ?? false,
      userId: json['user_id'] as String,
      email: json['email'] as String?,
      role: json['role'] as String? ?? 'citizen',
      profileCompleted: json['profile_completed'] as bool? ?? false,
    );
  }
}

class UserModel {
  final String id;
  final String? mobileNumber;
  final String? email;
  final bool hasPassword;
  final String role;
  final bool isActive;
  final UserProfileModel? profile;

  UserModel({
    required this.id,
    this.mobileNumber,
    this.email,
    this.hasPassword = false,
    required this.role,
    required this.isActive,
    this.profile,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['id'] as String,
      mobileNumber: json['mobile_number'] as String?,
      email: json['email'] as String?,
      hasPassword: json['has_password'] as bool? ?? false,
      role: json['role'] as String? ?? 'citizen',
      isActive: json['is_active'] as bool? ?? true,
      profile: json['profile'] != null
          ? UserProfileModel.fromJson(json['profile'] as Map<String, dynamic>)
          : null,
    );
  }
}
