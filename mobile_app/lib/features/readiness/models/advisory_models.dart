class ConditionAnalysisModel {
  final String condition;
  final String status;
  final String note;

  ConditionAnalysisModel({
    required this.condition,
    required this.status,
    required this.note,
  });

  factory ConditionAnalysisModel.fromJson(Map<String, dynamic> json) {
    return ConditionAnalysisModel(
      condition: json['condition'] as String? ?? 'Condition',
      status: json['status'] as String? ?? 'unknown',
      note: json['note'] as String? ?? '',
    );
  }
}

class CitationModel {
  final String title;
  final String sourceTitle;
  final String? sourceReference;
  final String sourceUrl;
  final String sourceFreshnessStatus;
  final bool isDemoData;

  CitationModel({
    required this.title,
    required this.sourceTitle,
    this.sourceReference,
    required this.sourceUrl,
    required this.sourceFreshnessStatus,
    this.isDemoData = true,
  });

  factory CitationModel.fromJson(Map<String, dynamic> json) {
    return CitationModel(
      title: json['title'] as String? ?? 'Official Guideline',
      sourceTitle: json['source_title'] as String? ?? 'Scheme Guidelines',
      sourceReference: json['source_reference'] as String?,
      sourceUrl: json['source_url'] as String? ?? 'https://myscheme.gov.in/',
      sourceFreshnessStatus: json['source_freshness_status'] as String? ??
          'Verified Official Source',
      isDemoData: json['is_demo_data'] as bool? ?? true,
    );
  }
}

class ReadinessBreakdownModel {
  final double overallReadinessScore;
  final double criteriaMatchPercentage;
  final double documentCoveragePercentage;
  final double informationCompletenessPercentage;
  final double consistencyScore;
  final String consistencyStatus;
  final String scoreInterpretation;
  final List<String> uploadedDocumentTypes;
  final List<String> missingDocumentTypes;
  final List<String> discrepancies;
  final List<String> lowConfidenceDocuments;

  ReadinessBreakdownModel({
    required this.overallReadinessScore,
    required this.criteriaMatchPercentage,
    required this.documentCoveragePercentage,
    required this.informationCompletenessPercentage,
    required this.consistencyScore,
    required this.consistencyStatus,
    required this.scoreInterpretation,
    required this.uploadedDocumentTypes,
    required this.missingDocumentTypes,
    required this.discrepancies,
    required this.lowConfidenceDocuments,
  });

  factory ReadinessBreakdownModel.fromJson(Map<String, dynamic> json) {
    return ReadinessBreakdownModel(
      overallReadinessScore:
          (json['overall_readiness_score'] as num?)?.toDouble() ?? 0.0,
      criteriaMatchPercentage:
          (json['criteria_match_percentage'] as num?)?.toDouble() ?? 0.0,
      documentCoveragePercentage:
          (json['document_coverage_percentage'] as num?)?.toDouble() ?? 0.0,
      informationCompletenessPercentage:
          (json['information_completeness_percentage'] as num?)?.toDouble() ??
              0.0,
      consistencyScore:
          (json['consistency_score'] as num?)?.toDouble() ?? 100.0,
      consistencyStatus: json['consistency_status'] as String? ?? 'Consistent',
      scoreInterpretation: json['score_interpretation'] as String? ?? '',
      uploadedDocumentTypes: (json['uploaded_document_types'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      missingDocumentTypes: (json['missing_document_types'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      discrepancies: (json['discrepancies'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      lowConfidenceDocuments:
          (json['low_confidence_documents'] as List<dynamic>?)
                  ?.map((e) => e.toString())
                  .toList() ??
              [],
    );
  }
}

class AIAdvisoryGuidanceModel {
  final String summary;
  final String assessmentExplanation;
  final List<ConditionAnalysisModel> criteriaAnalysis;
  final String documentAnalysis;
  final List<String> potentialInconsistencies;
  final List<String> nextSteps;
  final String officialPortalGuidance;
  final List<CitationModel> citations;
  final String language;
  final bool isMock;
  final String disclaimer;

  AIAdvisoryGuidanceModel({
    required this.summary,
    required this.assessmentExplanation,
    required this.criteriaAnalysis,
    required this.documentAnalysis,
    required this.potentialInconsistencies,
    required this.nextSteps,
    required this.officialPortalGuidance,
    required this.citations,
    required this.language,
    required this.isMock,
    required this.disclaimer,
  });

  factory AIAdvisoryGuidanceModel.fromJson(Map<String, dynamic> json) {
    return AIAdvisoryGuidanceModel(
      summary: json['summary'] as String? ?? '',
      assessmentExplanation: json['assessment_explanation'] as String? ?? '',
      criteriaAnalysis: (json['criteria_analysis'] as List<dynamic>?)
              ?.map((e) =>
                  ConditionAnalysisModel.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      documentAnalysis: json['document_analysis'] as String? ?? '',
      potentialInconsistencies:
          (json['potential_inconsistencies'] as List<dynamic>?)
                  ?.map((e) => e.toString())
                  .toList() ??
              [],
      nextSteps: (json['next_steps'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      officialPortalGuidance: json['official_portal_guidance'] as String? ?? '',
      citations: (json['citations'] as List<dynamic>?)
              ?.map((e) => CitationModel.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      language: json['language'] as String? ?? 'en',
      isMock: json['is_mock'] as bool? ?? false,
      disclaimer: json['disclaimer'] as String? ??
          'Advisory Notice: This guidance is AI-assisted and does not replace official determinations.',
    );
  }
}

class AdvisoryAssessmentModel {
  final String assessmentId;
  final String schemeId;
  final String schemeName;
  final String category;
  final String overallStatus;
  final ReadinessBreakdownModel readiness;
  final AIAdvisoryGuidanceModel advisory;
  final DateTime evaluatedAt;
  final String officialSourceUrl;
  final String officialApplicationUrl;

  AdvisoryAssessmentModel({
    required this.assessmentId,
    required this.schemeId,
    required this.schemeName,
    required this.category,
    required this.overallStatus,
    required this.readiness,
    required this.advisory,
    required this.evaluatedAt,
    required this.officialSourceUrl,
    required this.officialApplicationUrl,
  });

  factory AdvisoryAssessmentModel.fromJson(Map<String, dynamic> json) {
    return AdvisoryAssessmentModel(
      assessmentId: json['assessment_id'] as String? ?? '',
      schemeId: json['scheme_id'] as String? ?? '',
      schemeName: json['scheme_name'] as String? ?? 'Government Scheme',
      category: json['category'] as String? ?? 'General',
      overallStatus:
          json['overall_status'] as String? ?? 'Insufficient Information',
      readiness: ReadinessBreakdownModel.fromJson(
          json['readiness'] as Map<String, dynamic>? ?? {}),
      advisory: AIAdvisoryGuidanceModel.fromJson(
          json['advisory'] as Map<String, dynamic>? ?? {}),
      evaluatedAt: json['evaluated_at'] != null
          ? DateTime.parse(json['evaluated_at'] as String)
          : DateTime.now(),
      officialSourceUrl:
          json['official_source_url'] as String? ?? 'https://myscheme.gov.in/',
      officialApplicationUrl: json['official_application_url'] as String? ??
          'https://www.india.gov.in/',
    );
  }
}
