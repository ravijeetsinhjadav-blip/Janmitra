class EligibilityConditionModel {
  final String conditionName;
  final String field;
  final String operator;
  final dynamic expectedValue;
  final String explanation;

  EligibilityConditionModel({
    required this.conditionName,
    required this.field,
    required this.operator,
    required this.expectedValue,
    required this.explanation,
  });

  factory EligibilityConditionModel.fromJson(Map<String, dynamic> json) {
    return EligibilityConditionModel(
      conditionName: json['condition_name'] as String? ?? 'Criterion',
      field: json['field'] as String? ?? '',
      operator: json['operator'] as String? ?? 'eq',
      expectedValue: json['expected_value'],
      explanation: json['explanation'] as String? ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
    'condition_name': conditionName,
    'field': field,
    'operator': operator,
    'expected_value': expectedValue,
    'explanation': explanation,
  };
}

class ConditionEvaluationModel {
  final String conditionName;
  final String field;
  final String operator;
  final dynamic expectedValue;
  final dynamic actualValue;
  final String status; // 'satisfied', 'not_satisfied', 'unknown'
  final String explanation;

  ConditionEvaluationModel({
    required this.conditionName,
    required this.field,
    required this.operator,
    required this.expectedValue,
    this.actualValue,
    required this.status,
    required this.explanation,
  });

  factory ConditionEvaluationModel.fromJson(Map<String, dynamic> json) {
    return ConditionEvaluationModel(
      conditionName: json['condition_name'] as String? ?? 'Criterion',
      field: json['field'] as String? ?? '',
      operator: json['operator'] as String? ?? 'eq',
      expectedValue: json['expected_value'],
      actualValue: json['actual_value'],
      status: json['status'] as String? ?? 'unknown',
      explanation: json['explanation'] as String? ?? '',
    );
  }
}

class SchemeModel {
  final String id;
  final String schemeName;
  final String? shortDescription;
  final String description;
  final String department;
  final String category;
  final String stateApplicability;
  final String eligibilitySummary;
  final List<String> benefits;
  final List<EligibilityConditionModel> eligibilityCriteria;
  final List<String> requiredProfileFields;
  final List<String> applicationProcess;
  final List<String> requiredDocuments;
  final String officialSourceUrl;
  final String officialApplicationUrl;
  final String? sourceLastVerifiedAt;
  final String sourceFreshnessStatus;
  final String? eligibilitySourceReference;
  final String? benefitsSourceReference;
  final String? sourceVerificationDetails;
  final String status;
  final bool isDemoData;

  SchemeModel({
    required this.id,
    required this.schemeName,
    this.shortDescription,
    required this.description,
    required this.department,
    required this.category,
    required this.stateApplicability,
    required this.eligibilitySummary,
    required this.benefits,
    required this.eligibilityCriteria,
    required this.requiredProfileFields,
    required this.applicationProcess,
    required this.requiredDocuments,
    required this.officialSourceUrl,
    required this.officialApplicationUrl,
    this.sourceLastVerifiedAt,
    this.sourceFreshnessStatus = 'Verified Official Source',
    this.eligibilitySourceReference,
    this.benefitsSourceReference,
    this.sourceVerificationDetails,
    required this.status,
    required this.isDemoData,
  });

  factory SchemeModel.fromJson(Map<String, dynamic> json) {
    return SchemeModel(
      id: json['id'] as String? ?? '',
      schemeName: json['scheme_name'] as String? ?? '',
      shortDescription: json['short_description'] as String?,
      description: json['description'] as String? ?? '',
      department: json['department'] as String? ?? '',
      category: json['category'] as String? ?? 'General',
      stateApplicability: json['state_applicability'] as String? ?? 'All India',
      eligibilitySummary: json['eligibility_summary'] as String? ?? '',
      benefits: (json['benefits'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      eligibilityCriteria: (json['eligibility_criteria'] as List<dynamic>?)
              ?.map((e) => EligibilityConditionModel.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      requiredProfileFields: (json['required_profile_fields'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      applicationProcess: (json['application_process'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      requiredDocuments: (json['required_documents'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      officialSourceUrl: json['official_source_url'] as String? ?? '',
      officialApplicationUrl: json['official_application_url'] as String? ?? '',
      sourceLastVerifiedAt: json['source_last_verified_at'] as String?,
      sourceFreshnessStatus: json['source_freshness_status'] as String? ?? 'Verified Official Source',
      eligibilitySourceReference: json['eligibility_source_reference'] as String?,
      benefitsSourceReference: json['benefits_source_reference'] as String?,
      sourceVerificationDetails: json['source_verification_details'] as String?,
      status: json['status'] as String? ?? 'active',
      isDemoData: json['is_demo_data'] as bool? ?? false,
    );
  }
}

class SchemeListResponseModel {
  final List<SchemeModel> items;
  final int total;
  final int page;
  final int pageSize;
  final int totalPages;

  SchemeListResponseModel({
    required this.items,
    required this.total,
    required this.page,
    required this.pageSize,
    required this.totalPages,
  });

  factory SchemeListResponseModel.fromJson(Map<String, dynamic> json) {
    return SchemeListResponseModel(
      items: (json['items'] as List<dynamic>?)
              ?.map((e) => SchemeModel.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      total: json['total'] as int? ?? 0,
      page: json['page'] as int? ?? 1,
      pageSize: json['page_size'] as int? ?? 20,
      totalPages: json['total_pages'] as int? ?? 1,
    );
  }
}

class SchemeCategoryModel {
  final String category;
  final int count;

  SchemeCategoryModel({required this.category, required this.count});

  factory SchemeCategoryModel.fromJson(Map<String, dynamic> json) {
    return SchemeCategoryModel(
      category: json['category'] as String? ?? '',
      count: json['count'] as int? ?? 0,
    );
  }
}

class SchemeRecommendationModel {
  final SchemeModel scheme;
  final String recommendationReason;
  final double criteriaMatchPercentage;
  final double matchScore;
  final int satisfiedCount;
  final int notSatisfiedCount;
  final int unknownCount;
  final String advisoryNotice;

  SchemeRecommendationModel({
    required this.scheme,
    required this.recommendationReason,
    required this.criteriaMatchPercentage,
    required this.matchScore,
    required this.satisfiedCount,
    required this.notSatisfiedCount,
    required this.unknownCount,
    required this.advisoryNotice,
  });

  factory SchemeRecommendationModel.fromJson(Map<String, dynamic> json) {
    final score = (json['criteria_match_percentage'] ?? json['match_score'] as num?)?.toDouble() ?? 0.0;
    return SchemeRecommendationModel(
      scheme: SchemeModel.fromJson(json['scheme'] as Map<String, dynamic>),
      recommendationReason: json['recommendation_reason'] as String? ?? '',
      criteriaMatchPercentage: score,
      matchScore: score,
      satisfiedCount: json['satisfied_count'] as int? ?? 0,
      notSatisfiedCount: json['not_satisfied_count'] as int? ?? 0,
      unknownCount: json['unknown_count'] as int? ?? 0,
      advisoryNotice: json['advisory_notice'] as String? ??
          'Recommendations are advisory suggestions based solely on your entered profile and do not guarantee eligibility or official government approval.',
    );
  }
}

class AssessmentResultModel {
  final String assessmentId;
  final String schemeId;
  final String schemeName;
  final String category;
  final String overallStatus;
  final double criteriaMatchPercentage;
  final double overallReadinessScore;
  final String scoreInterpretation;
  final List<ConditionEvaluationModel> conditionsBreakdown;
  final int satisfiedCount;
  final int notSatisfiedCount;
  final int unknownCount;
  final List<String> missingFields;
  final String officialSourceUrl;
  final String officialApplicationUrl;
  final String evaluatedAt;
  final String advisoryDisclaimer;

  AssessmentResultModel({
    required this.assessmentId,
    required this.schemeId,
    required this.schemeName,
    required this.category,
    required this.overallStatus,
    required this.criteriaMatchPercentage,
    required this.overallReadinessScore,
    required this.scoreInterpretation,
    required this.conditionsBreakdown,
    required this.satisfiedCount,
    required this.notSatisfiedCount,
    required this.unknownCount,
    required this.missingFields,
    required this.officialSourceUrl,
    required this.officialApplicationUrl,
    required this.evaluatedAt,
    required this.advisoryDisclaimer,
  });

  factory AssessmentResultModel.fromJson(Map<String, dynamic> json) {
    final score = (json['criteria_match_percentage'] ?? json['overall_readiness_score'] as num?)?.toDouble() ?? 0.0;
    return AssessmentResultModel(
      assessmentId: json['assessment_id'] as String? ?? '',
      schemeId: json['scheme_id'] as String? ?? '',
      schemeName: json['scheme_name'] as String? ?? '',
      category: json['category'] as String? ?? 'General',
      overallStatus: json['overall_status'] as String? ?? 'Unknown',
      criteriaMatchPercentage: score,
      overallReadinessScore: score,
      scoreInterpretation: json['score_interpretation'] as String? ??
          'Criteria Match Percentage reflects the proportion of predefined conditions verified as satisfied based on your profile. It does NOT represent government approval likelihood.',
      conditionsBreakdown: (json['conditions_breakdown'] as List<dynamic>?)
              ?.map((e) => ConditionEvaluationModel.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      satisfiedCount: json['satisfied_count'] as int? ?? 0,
      notSatisfiedCount: json['not_satisfied_count'] as int? ?? 0,
      unknownCount: json['unknown_count'] as int? ?? 0,
      missingFields: (json['missing_fields'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      officialSourceUrl: json['official_source_url'] as String? ?? '',
      officialApplicationUrl: json['official_application_url'] as String? ?? '',
      evaluatedAt: json['evaluated_at'] as String? ?? '',
      advisoryDisclaimer: json['advisory_disclaimer'] as String? ??
          'This assessment is strictly advisory and does not constitute official government approval or rejection.',
    );
  }
}

class AssessmentHistoryItemModel {
  final String assessmentId;
  final String? schemeId;
  final String schemeName;
  final String overallStatus;
  final double criteriaMatchPercentage;
  final double overallReadinessScore;
  final int satisfiedCount;
  final int notSatisfiedCount;
  final int unknownCount;
  final String createdAt;

  AssessmentHistoryItemModel({
    required this.assessmentId,
    this.schemeId,
    required this.schemeName,
    required this.overallStatus,
    required this.criteriaMatchPercentage,
    required this.overallReadinessScore,
    required this.satisfiedCount,
    required this.notSatisfiedCount,
    required this.unknownCount,
    required this.createdAt,
  });

  factory AssessmentHistoryItemModel.fromJson(Map<String, dynamic> json) {
    final score = (json['criteria_match_percentage'] ?? json['overall_readiness_score'] as num?)?.toDouble() ?? 0.0;
    return AssessmentHistoryItemModel(
      assessmentId: json['assessment_id'] as String? ?? '',
      schemeId: json['scheme_id'] as String?,
      schemeName: json['scheme_name'] as String? ?? '',
      overallStatus: json['overall_status'] as String? ?? '',
      criteriaMatchPercentage: score,
      overallReadinessScore: score,
      satisfiedCount: json['satisfied_count'] as int? ?? 0,
      notSatisfiedCount: json['not_satisfied_count'] as int? ?? 0,
      unknownCount: json['unknown_count'] as int? ?? 0,
      createdAt: json['created_at'] as String? ?? '',
    );
  }
}
