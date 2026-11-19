class SchemeCategoryRuleModel {
  final String id;
  final String schemeId;
  final String category;
  final String conditionName;
  final String field;
  final String operator;
  final dynamic expectedValue;
  final String? specialConditions;
  final String? exceptions;
  final String? officialSourceReference;

  SchemeCategoryRuleModel({
    required this.id,
    required this.schemeId,
    required this.category,
    required this.conditionName,
    required this.field,
    required this.operator,
    required this.expectedValue,
    this.specialConditions,
    this.exceptions,
    this.officialSourceReference,
  });

  factory SchemeCategoryRuleModel.fromJson(Map<String, dynamic> json) {
    return SchemeCategoryRuleModel(
      id: json['id'] as String? ?? '',
      schemeId: json['scheme_id'] as String? ?? '',
      category: json['category'] as String? ?? 'All',
      conditionName: json['condition_name'] as String? ?? '',
      field: json['field'] as String? ?? '',
      operator: json['operator'] as String? ?? 'lte',
      expectedValue: json['expected_value'],
      specialConditions: json['special_conditions'] as String?,
      exceptions: json['exceptions'] as String?,
      officialSourceReference: json['official_source_reference'] as String?,
    );
  }
}

class SchemeCategoryDocumentModel {
  final String id;
  final String schemeId;
  final String category;
  final String documentName;
  final String documentType;
  final bool isMandatory;
  final String? conditionsDescription;
  final String issuingAuthority;
  final String acceptedFormats;
  final String? validityRules;
  final bool hasGuide;

  SchemeCategoryDocumentModel({
    required this.id,
    required this.schemeId,
    required this.category,
    required this.documentName,
    required this.documentType,
    required this.isMandatory,
    this.conditionsDescription,
    required this.issuingAuthority,
    required this.acceptedFormats,
    this.validityRules,
    this.hasGuide = true,
  });

  factory SchemeCategoryDocumentModel.fromJson(Map<String, dynamic> json) {
    return SchemeCategoryDocumentModel(
      id: json['id'] as String? ?? '',
      schemeId: json['scheme_id'] as String? ?? '',
      category: json['category'] as String? ?? 'All',
      documentName: json['document_name'] as String? ?? '',
      documentType: json['document_type'] as String? ?? '',
      isMandatory: json['is_mandatory'] as bool? ?? true,
      conditionsDescription: json['conditions_description'] as String?,
      issuingAuthority: json['issuing_authority'] as String? ?? 'Competent Authority',
      acceptedFormats: json['accepted_formats'] as String? ?? 'PDF, JPG, PNG',
      validityRules: json['validity_rules'] as String?,
      hasGuide: json['has_guide'] as bool? ?? true,
    );
  }
}

class DocumentGuideModel {
  final String id;
  final String documentType;
  final String documentName;
  final String description;
  final String issuingDepartment;
  final Map<String, String> stateSpecificAuthority;
  final List<String> requiredSupportingDocuments;
  final Map<String, List<String>> onlineSteps;
  final Map<String, List<String>> offlineSteps;
  final Map<String, dynamic> feesAndTimelines;
  final Map<String, String> officialLinks;
  final List<String> languagesSupported;

  DocumentGuideModel({
    required this.id,
    required this.documentType,
    required this.documentName,
    required this.description,
    required this.issuingDepartment,
    required this.stateSpecificAuthority,
    required this.requiredSupportingDocuments,
    required this.onlineSteps,
    required this.offlineSteps,
    required this.feesAndTimelines,
    required this.officialLinks,
    required this.languagesSupported,
  });

  factory DocumentGuideModel.fromJson(Map<String, dynamic> json) {
    final rawAuthority = json['state_specific_authority'] as Map<String, dynamic>? ?? {};
    final rawSupporting = json['required_supporting_documents'] as List<dynamic>? ?? [];
    final rawOnline = json['online_steps'] as Map<String, dynamic>? ?? {};
    final rawOffline = json['offline_steps'] as Map<String, dynamic>? ?? {};
    final rawFees = json['fees_and_timelines'] as Map<String, dynamic>? ?? {};
    final rawLinks = json['official_links'] as Map<String, dynamic>? ?? {};
    final rawLangs = json['languages_supported'] as List<dynamic>? ?? ['en', 'hi', 'gu'];

    return DocumentGuideModel(
      id: json['id'] as String? ?? '',
      documentType: json['document_type'] as String? ?? '',
      documentName: json['document_name'] as String? ?? '',
      description: json['description'] as String? ?? '',
      issuingDepartment: json['issuing_department'] as String? ?? '',
      stateSpecificAuthority: rawAuthority.map((k, v) => MapEntry(k, v.toString())),
      requiredSupportingDocuments: rawSupporting.map((e) => e.toString()).toList(),
      onlineSteps: rawOnline.map((k, v) => MapEntry(
            k,
            (v as List<dynamic>? ?? []).map((e) => e.toString()).toList(),
          )),
      offlineSteps: rawOffline.map((k, v) => MapEntry(
            k,
            (v as List<dynamic>? ?? []).map((e) => e.toString()).toList(),
          )),
      feesAndTimelines: rawFees,
      officialLinks: rawLinks.map((k, v) => MapEntry(k, v.toString())),
      languagesSupported: rawLangs.map((e) => e.toString()).toList(),
    );
  }
}

class SchemeAnalyticsBreakdownModel {
  final String id;
  final String dimension;
  final String categoryName;
  final int metricValue;
  final double? percentage;
  final String? notes;

  SchemeAnalyticsBreakdownModel({
    required this.id,
    required this.dimension,
    required this.categoryName,
    required this.metricValue,
    this.percentage,
    this.notes,
  });

  factory SchemeAnalyticsBreakdownModel.fromJson(Map<String, dynamic> json) {
    return SchemeAnalyticsBreakdownModel(
      id: json['id'] as String? ?? '',
      dimension: json['dimension'] as String? ?? '',
      categoryName: json['category_name'] as String? ?? '',
      metricValue: json['metric_value'] as int? ?? 0,
      percentage: (json['percentage'] as num?)?.toDouble(),
      notes: json['notes'] as String?,
    );
  }
}

class SchemeAnalyticsDatasetModel {
  final String id;
  final String schemeId;
  final String sourceName;
  final String? reportTitle;
  final String sourceUrl;
  final String reportingPeriod;
  final String geographicScope;
  final String metricType;
  final String? metricDefinition;
  final int totalBeneficiaries;
  final int datasetVersion;
  final String verificationStatus;
  final bool isPublished;
  final String? notes;
  final String civicDisclaimer;
  final List<SchemeAnalyticsBreakdownModel> breakdowns;

  SchemeAnalyticsDatasetModel({
    required this.id,
    required this.schemeId,
    required this.sourceName,
    this.reportTitle,
    required this.sourceUrl,
    required this.reportingPeriod,
    this.geographicScope = 'National',
    required this.metricType,
    this.metricDefinition,
    required this.totalBeneficiaries,
    required this.datasetVersion,
    required this.verificationStatus,
    required this.isPublished,
    this.notes,
    required this.civicDisclaimer,
    required this.breakdowns,
  });

  factory SchemeAnalyticsDatasetModel.fromJson(Map<String, dynamic> json) {
    final rawBreakdowns = json['breakdowns'] as List<dynamic>? ?? [];
    return SchemeAnalyticsDatasetModel(
      id: json['id'] as String? ?? '',
      schemeId: json['scheme_id'] as String? ?? '',
      sourceName: json['source_name'] as String? ?? '',
      reportTitle: json['report_title'] as String?,
      sourceUrl: json['source_url'] as String? ?? '',
      reportingPeriod: json['reporting_period'] as String? ?? '',
      geographicScope: json['geographic_scope'] as String? ?? 'National',
      metricType: json['metric_type'] as String? ?? 'unique_beneficiaries',
      metricDefinition: json['metric_definition'] as String?,
      totalBeneficiaries: json['total_beneficiaries'] as int? ?? 0,
      datasetVersion: json['dataset_version'] as int? ?? 1,
      verificationStatus: json['verification_status'] as String? ?? 'Pending Verification',
      isPublished: json['is_published'] as bool? ?? false,
      notes: json['notes'] as String?,
      civicDisclaimer: json['civic_disclaimer'] as String? ??
          'Official Government Aggregate Data. Sourced exclusively from official government reports.',
      breakdowns: rawBreakdowns
          .map((b) => SchemeAnalyticsBreakdownModel.fromJson(b as Map<String, dynamic>))
          .toList(),
    );
  }
}

