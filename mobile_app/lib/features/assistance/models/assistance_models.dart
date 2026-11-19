class DocumentPreparationStatusModel {
  final String documentName;
  final String status;
  final String notes;
  final String? matchingDocumentId;

  DocumentPreparationStatusModel({
    required this.documentName,
    required this.status,
    required this.notes,
    this.matchingDocumentId,
  });

  factory DocumentPreparationStatusModel.fromJson(Map<String, dynamic> json) {
    return DocumentPreparationStatusModel(
      documentName: json['document_name'] as String? ?? 'Required Document',
      status: json['status'] as String? ?? 'Missing',
      notes: json['notes'] as String? ?? '',
      matchingDocumentId: json['matching_document_id'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'document_name': documentName,
        'status': status,
        'notes': notes,
        'matching_document_id': matchingDocumentId,
      };
}

class ChecklistItemModel {
  final String itemId;
  final String category;
  final String title;
  final String description;
  final bool isMandatory;
  bool isCompleted;

  ChecklistItemModel({
    required this.itemId,
    required this.category,
    required this.title,
    required this.description,
    this.isMandatory = true,
    this.isCompleted = false,
  });

  factory ChecklistItemModel.fromJson(Map<String, dynamic> json) {
    return ChecklistItemModel(
      itemId: json['item_id'] as String? ?? '',
      category: json['category'] as String? ?? 'general',
      title: json['title'] as String? ?? 'Checklist Item',
      description: json['description'] as String? ?? '',
      isMandatory: json['is_mandatory'] as bool? ?? true,
      isCompleted: json['is_completed'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() => {
        'item_id': itemId,
        'category': category,
        'title': title,
        'description': description,
        'is_mandatory': isMandatory,
        'is_completed': isCompleted,
      };
}

class ApplicantInfoRequirementModel {
  final String fieldName;
  final String description;
  final String importance;

  ApplicantInfoRequirementModel({
    required this.fieldName,
    required this.description,
    this.importance = 'Mandatory',
  });

  factory ApplicantInfoRequirementModel.fromJson(Map<String, dynamic> json) {
    return ApplicantInfoRequirementModel(
      fieldName: json['field_name'] as String? ?? 'Field',
      description: json['description'] as String? ?? '',
      importance: json['importance'] as String? ?? 'Mandatory',
    );
  }

  Map<String, dynamic> toJson() => {
        'field_name': fieldName,
        'description': description,
        'importance': importance,
      };
}

class SupportingDocumentSpecModel {
  final String documentType;
  final String specifications;
  final String issuingAuthority;

  SupportingDocumentSpecModel({
    required this.documentType,
    required this.specifications,
    required this.issuingAuthority,
  });

  factory SupportingDocumentSpecModel.fromJson(Map<String, dynamic> json) {
    return SupportingDocumentSpecModel(
      documentType: json['document_type'] as String? ?? 'Document',
      specifications: json['specifications'] as String? ?? '',
      issuingAuthority: json['issuing_authority'] as String? ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
        'document_type': documentType,
        'specifications': specifications,
        'issuing_authority': issuingAuthority,
      };
}

class PortalStepInstructionModel {
  final int stepNumber;
  final String title;
  final String instruction;

  PortalStepInstructionModel({
    required this.stepNumber,
    required this.title,
    required this.instruction,
  });

  factory PortalStepInstructionModel.fromJson(Map<String, dynamic> json) {
    return PortalStepInstructionModel(
      stepNumber: json['step_number'] as int? ?? 1,
      title: json['title'] as String? ?? 'Step',
      instruction: json['instruction'] as String? ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
        'step_number': stepNumber,
        'title': title,
        'instruction': instruction,
      };
}

class ApplicationInfoGuideModel {
  final List<ApplicantInfoRequirementModel> applicantInfoRequired;
  final List<SupportingDocumentSpecModel> supportingDocumentsSpecs;
  final List<String> importantDeclarations;
  final List<String> commonMistakesToAvoid;
  final List<String> submissionPrecautions;
  final List<PortalStepInstructionModel> portalSteps;
  final String language;
  final String disclaimer;

  ApplicationInfoGuideModel({
    required this.applicantInfoRequired,
    required this.supportingDocumentsSpecs,
    required this.importantDeclarations,
    required this.commonMistakesToAvoid,
    required this.submissionPrecautions,
    required this.portalSteps,
    this.language = 'en',
    this.disclaimer =
        'AI-assisted guidance does not constitute an official government determination or guarantee application approval.',
  });

  factory ApplicationInfoGuideModel.fromJson(Map<String, dynamic> json) {
    return ApplicationInfoGuideModel(
      applicantInfoRequired: (json['applicant_info_required'] as List<dynamic>?)
              ?.map(
                (e) => ApplicantInfoRequirementModel.fromJson(
                  e as Map<String, dynamic>,
                ),
              )
              .toList() ??
          [],
      supportingDocumentsSpecs:
          (json['supporting_documents_specs'] as List<dynamic>?)
                  ?.map(
                    (e) => SupportingDocumentSpecModel.fromJson(
                      e as Map<String, dynamic>,
                    ),
                  )
                  .toList() ??
              [],
      importantDeclarations: (json['important_declarations'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      commonMistakesToAvoid:
          (json['common_mistakes_to_avoid'] as List<dynamic>?)
                  ?.map((e) => e.toString())
                  .toList() ??
              [],
      submissionPrecautions: (json['submission_precautions'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      portalSteps: (json['portal_steps'] as List<dynamic>?)
              ?.map(
                (e) => PortalStepInstructionModel.fromJson(
                  e as Map<String, dynamic>,
                ),
              )
              .toList() ??
          [],
      language: json['language'] as String? ?? 'en',
      disclaimer: json['disclaimer'] as String? ??
          'AI-assisted guidance does not constitute an official government determination.',
    );
  }
}

class ChecklistUpdateResponseModel {
  final String itemId;
  final bool isCompleted;
  final int completedCount;
  final int totalCount;
  final double completionPercentage;
  final String message;

  ChecklistUpdateResponseModel({
    required this.itemId,
    required this.isCompleted,
    required this.completedCount,
    required this.totalCount,
    required this.completionPercentage,
    required this.message,
  });

  factory ChecklistUpdateResponseModel.fromJson(Map<String, dynamic> json) {
    return ChecklistUpdateResponseModel(
      itemId: json['item_id'] as String? ?? '',
      isCompleted: json['is_completed'] as bool? ?? false,
      completedCount: json['completed_count'] as int? ?? 0,
      totalCount: json['total_count'] as int? ?? 0,
      completionPercentage:
          (json['completion_percentage'] as num?)?.toDouble() ?? 0.0,
      message: json['message'] as String? ?? '',
    );
  }
}

class ApplicationAssistanceModel {
  final String schemeId;
  final String schemeName;
  final String category;
  final String department;
  final String? assessmentId;
  final String overallStatus;
  final double criteriaMatchPercentage;
  final double overallReadinessScore;
  final String readinessInterpretation;
  final List<DocumentPreparationStatusModel> documentPreparationStatuses;
  List<ChecklistItemModel> checklist;
  int checklistCompletedCount;
  int checklistTotalCount;
  double checklistCompletionPercentage;
  final ApplicationInfoGuideModel guide;
  final String officialApplicationUrl;
  final String officialSourceUrl;
  final bool isDemoData;
  final String language;
  final DateTime evaluatedAt;
  final String disclaimer;

  ApplicationAssistanceModel({
    required this.schemeId,
    required this.schemeName,
    required this.category,
    required this.department,
    this.assessmentId,
    required this.overallStatus,
    required this.criteriaMatchPercentage,
    required this.overallReadinessScore,
    required this.readinessInterpretation,
    required this.documentPreparationStatuses,
    required this.checklist,
    required this.checklistCompletedCount,
    required this.checklistTotalCount,
    required this.checklistCompletionPercentage,
    required this.guide,
    required this.officialApplicationUrl,
    required this.officialSourceUrl,
    this.isDemoData = true,
    this.language = 'en',
    required this.evaluatedAt,
    required this.disclaimer,
  });

  factory ApplicationAssistanceModel.fromJson(Map<String, dynamic> json) {
    return ApplicationAssistanceModel(
      schemeId: json['scheme_id'] as String? ?? '',
      schemeName: json['scheme_name'] as String? ?? 'Scheme Assistance',
      category: json['category'] as String? ?? 'General',
      department: json['department'] as String? ?? 'Government of India',
      assessmentId: json['assessment_id'] as String?,
      overallStatus: json['overall_status'] as String? ?? 'Pending Assessment',
      criteriaMatchPercentage:
          (json['criteria_match_percentage'] as num?)?.toDouble() ?? 0.0,
      overallReadinessScore:
          (json['overall_readiness_score'] as num?)?.toDouble() ?? 0.0,
      readinessInterpretation:
          json['readiness_interpretation'] as String? ?? 'Guidance Pending',
      documentPreparationStatuses:
          (json['document_preparation_statuses'] as List<dynamic>?)
                  ?.map(
                    (e) => DocumentPreparationStatusModel.fromJson(
                      e as Map<String, dynamic>,
                    ),
                  )
                  .toList() ??
              [],
      checklist: (json['checklist'] as List<dynamic>?)
              ?.map(
                (e) => ChecklistItemModel.fromJson(e as Map<String, dynamic>),
              )
              .toList() ??
          [],
      checklistCompletedCount: json['checklist_completed_count'] as int? ?? 0,
      checklistTotalCount: json['checklist_total_count'] as int? ?? 0,
      checklistCompletionPercentage:
          (json['checklist_completion_percentage'] as num?)?.toDouble() ?? 0.0,
      guide: ApplicationInfoGuideModel.fromJson(
        json['guide'] as Map<String, dynamic>? ?? {},
      ),
      officialApplicationUrl: json['official_application_url'] as String? ??
          'https://myscheme.gov.in/',
      officialSourceUrl:
          json['official_source_url'] as String? ?? 'https://myscheme.gov.in/',
      isDemoData: json['is_demo_data'] as bool? ?? true,
      language: json['language'] as String? ?? 'en',
      evaluatedAt: json['evaluated_at'] != null
          ? DateTime.tryParse(json['evaluated_at'] as String) ?? DateTime.now()
          : DateTime.now(),
      disclaimer: json['disclaimer'] as String? ??
          'Advisory Notice: JanMitra Assist is an application preparation assistant. '
              'It does NOT replace official government portals or submit applications on your behalf.',
    );
  }
}
