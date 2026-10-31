class UserProfileModel {
  final String? id;
  final String? userId;
  final String fullName;
  final String dateOfBirth; // YYYY-MM-DD
  final String state;
  final String district;
  final String residenceType; // 'rural' or 'urban'
  final double? annualFamilyIncome;
  final String? occupation;
  final String? educationLevel;
  final String? createdAt;
  final String? updatedAt;

  UserProfileModel({
    this.id,
    this.userId,
    required this.fullName,
    required this.dateOfBirth,
    required this.state,
    required this.district,
    required this.residenceType,
    this.annualFamilyIncome,
    this.occupation,
    this.educationLevel,
    this.createdAt,
    this.updatedAt,
  });

  factory UserProfileModel.fromJson(Map<String, dynamic> json) {
    return UserProfileModel(
      id: json['id'] as String?,
      userId: json['user_id'] as String?,
      fullName: json['full_name'] as String? ?? '',
      dateOfBirth: json['date_of_birth'] as String? ?? '',
      state: json['state'] as String? ?? '',
      district: json['district'] as String? ?? '',
      residenceType: json['residence_type'] as String? ?? 'rural',
      annualFamilyIncome: json['annual_family_income'] != null
          ? (json['annual_family_income'] as num).toDouble()
          : null,
      occupation: json['occupation'] as String?,
      educationLevel: json['education_level'] as String?,
      createdAt: json['created_at'] as String?,
      updatedAt: json['updated_at'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'full_name': fullName,
      'date_of_birth': dateOfBirth,
      'state': state,
      'district': district,
      'residence_type': residenceType,
      if (annualFamilyIncome != null) 'annual_family_income': annualFamilyIncome,
      if (occupation != null && occupation!.isNotEmpty) 'occupation': occupation,
      if (educationLevel != null && educationLevel!.isNotEmpty) 'education_level': educationLevel,
    };
  }
}

