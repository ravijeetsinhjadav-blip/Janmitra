class ApplicationStatus {
  static const String submitted = 'Submitted';
  static const String underReview = 'Under Review';
  static const String pending = 'Pending';
  static const String documentVerification = 'Document Verification';
  static const String approved = 'Approved';
  static const String rejected = 'Rejected';
  static const String completed = 'Completed';

  static const List<String> all = [
    submitted,
    underReview,
    pending,
    documentVerification,
    approved,
    rejected,
    completed,
  ];
}

class HistoryEventType {
  static const String initialRegistration = 'INITIAL_REGISTRATION';
  static const String statusUpdate = 'STATUS_UPDATE';
  static const String remarkAdded = 'REMARK_ADDED';
  static const String applicationDetailsUpdated = 'APPLICATION_DETAILS_UPDATED';

  static const List<String> all = [
    initialRegistration,
    statusUpdate,
    remarkAdded,
    applicationDetailsUpdated,
  ];
}

class HistorySource {
  static const String userReported = 'USER_REPORTED';
  static const String systemMigration = 'SYSTEM_MIGRATION';
}

/// Response object representing a citizen's tracked application with scheme metadata.
class ApplicationModel {
  final String id;
  final String userId;
  final String schemeId;
  final String schemeName;
  final String? category;
  final String? department;
  final String? officialApplicationUrl;
  final String? applicationReferenceNumber;
  final DateTime? submissionDate;
  final String status;
  final DateTime createdAt;
  final DateTime updatedAt;

  ApplicationModel({
    required this.id,
    required this.userId,
    required this.schemeId,
    required this.schemeName,
    this.category,
    this.department,
    this.officialApplicationUrl,
    this.applicationReferenceNumber,
    this.submissionDate,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
  });

  bool get hasReferenceNumber =>
      applicationReferenceNumber != null &&
      applicationReferenceNumber!.trim().isNotEmpty;

  String get displayReferenceNumber =>
      hasReferenceNumber ? applicationReferenceNumber! : 'Not Issued';

  factory ApplicationModel.fromJson(Map<String, dynamic> json) {
    return ApplicationModel(
      id: json['id'] as String? ?? '',
      userId: json['user_id'] as String? ?? '',
      schemeId: json['scheme_id'] as String? ?? '',
      schemeName: json['scheme_name'] as String? ?? '',
      category: json['category'] as String?,
      department: json['department'] as String?,
      officialApplicationUrl: json['official_application_url'] as String?,
      applicationReferenceNumber:
          json['application_reference_number'] as String?,
      submissionDate: json['submission_date'] != null
          ? DateTime.tryParse(json['submission_date'] as String)
          : null,
      status: json['status'] as String? ?? ApplicationStatus.submitted,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'] as String) ?? DateTime.now()
          : DateTime.now(),
      updatedAt: json['updated_at'] != null
          ? DateTime.tryParse(json['updated_at'] as String) ?? DateTime.now()
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'user_id': userId,
        'scheme_id': schemeId,
        'scheme_name': schemeName,
        'category': category,
        'department': department,
        'official_application_url': officialApplicationUrl,
        'application_reference_number': applicationReferenceNumber,
        'submission_date': submissionDate?.toUtc().toIso8601String(),
        'status': status,
        'created_at': createdAt.toUtc().toIso8601String(),
        'updated_at': updatedAt.toUtc().toIso8601String(),
      };
}

/// Paginated collection of citizen application tracking records.
class ApplicationListResponseModel {
  final int total;
  final int page;
  final int pageSize;
  final int totalPages;
  final List<ApplicationModel> applications;

  ApplicationListResponseModel({
    required this.total,
    required this.page,
    required this.pageSize,
    required this.totalPages,
    required this.applications,
  });

  factory ApplicationListResponseModel.fromJson(Map<String, dynamic> json) {
    return ApplicationListResponseModel(
      total: (json['total'] as num?)?.toInt() ?? 0,
      page: (json['page'] as num?)?.toInt() ?? 1,
      pageSize: (json['page_size'] as num?)?.toInt() ?? 20,
      totalPages: (json['total_pages'] as num?)?.toInt() ?? 0,
      applications: (json['applications'] as List<dynamic>? ?? [])
          .map(
              (item) => ApplicationModel.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() => {
        'total': total,
        'page': page,
        'page_size': pageSize,
        'total_pages': totalPages,
        'applications': applications.map((a) => a.toJson()).toList(),
      };
}

/// Citizen request payload to register an application already submitted on an official portal.
class ApplicationCreateRequestModel {
  final String schemeId;
  final DateTime submissionDate;
  final String? applicationReferenceNumber;
  final bool referenceNumberNotIssued;
  final String? remarks;

  ApplicationCreateRequestModel({
    required this.schemeId,
    required this.submissionDate,
    this.applicationReferenceNumber,
    this.referenceNumberNotIssued = false,
    this.remarks,
  });

  Map<String, dynamic> toJson() {
    final map = <String, dynamic>{
      'scheme_id': schemeId,
      'submission_date': submissionDate.toUtc().toIso8601String(),
      'reference_number_not_issued': referenceNumberNotIssued,
    };
    if (applicationReferenceNumber != null &&
        applicationReferenceNumber!.trim().isNotEmpty) {
      map['application_reference_number'] = applicationReferenceNumber!.trim();
    }
    if (remarks != null && remarks!.trim().isNotEmpty) {
      map['remarks'] = remarks!.trim();
    }
    return map;
  }
}

/// Citizen request payload to update an existing application tracking record.
class ApplicationUpdateRequestModel {
  final String? status;
  final String? applicationReferenceNumber;
  final bool clearReferenceNumber;
  final DateTime? submissionDate;
  final String? remarks;

  ApplicationUpdateRequestModel({
    this.status,
    this.applicationReferenceNumber,
    this.clearReferenceNumber = false,
    this.submissionDate,
    this.remarks,
  });

  Map<String, dynamic> toJson() {
    final map = <String, dynamic>{};
    if (status != null && status!.trim().isNotEmpty) {
      map['status'] = status!.trim();
    }
    if (clearReferenceNumber) {
      map['clear_reference_number'] = true;
      map['application_reference_number'] = null;
    } else if (applicationReferenceNumber != null &&
        applicationReferenceNumber!.trim().isNotEmpty) {
      map['application_reference_number'] = applicationReferenceNumber!.trim();
    }
    if (submissionDate != null) {
      map['submission_date'] = submissionDate!.toUtc().toIso8601String();
    }
    if (remarks != null && remarks!.trim().isNotEmpty) {
      map['remarks'] = remarks!.trim();
    }
    return map;
  }
}

/// Confirmation response upon removing a local tracking record.
class ApplicationDeleteResponseModel {
  final String id;
  final String message;

  ApplicationDeleteResponseModel({
    required this.id,
    required this.message,
  });

  factory ApplicationDeleteResponseModel.fromJson(Map<String, dynamic> json) {
    return ApplicationDeleteResponseModel(
      id: json['id'] as String? ?? '',
      message: json['message'] as String? ??
          'Application tracking record deleted successfully.',
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'message': message,
      };
}

/// Immutable audit record representing a status update, remark, or detail change.
class ApplicationStatusHistoryModel {
  final String id;
  final String applicationId;
  final String? previousStatus;
  final String newStatus;
  final String eventType;
  final String source;
  final String? remarks;
  final String? changedByUserId;
  final DateTime createdAt;

  ApplicationStatusHistoryModel({
    required this.id,
    required this.applicationId,
    this.previousStatus,
    required this.newStatus,
    required this.eventType,
    required this.source,
    this.remarks,
    this.changedByUserId,
    required this.createdAt,
  });

  factory ApplicationStatusHistoryModel.fromJson(Map<String, dynamic> json) {
    return ApplicationStatusHistoryModel(
      id: json['id'] as String? ?? '',
      applicationId: json['application_id'] as String? ?? '',
      previousStatus: json['previous_status'] as String?,
      newStatus: json['new_status'] as String? ?? ApplicationStatus.submitted,
      eventType: json['event_type'] as String? ?? HistoryEventType.statusUpdate,
      source: json['source'] as String? ?? HistorySource.userReported,
      remarks: json['remarks'] as String?,
      changedByUserId: json['changed_by_user_id'] as String?,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'] as String) ?? DateTime.now()
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'application_id': applicationId,
        'previous_status': previousStatus,
        'new_status': newStatus,
        'event_type': eventType,
        'source': source,
        'remarks': remarks,
        'changed_by_user_id': changedByUserId,
        'created_at': createdAt.toUtc().toIso8601String(),
      };
}

/// Collection of chronological status updates with clear user-reported disclaimer.
class ApplicationStatusHistoryListModel {
  final String applicationId;
  final String currentStatus;
  final int total;
  final String disclaimer;
  final List<ApplicationStatusHistoryModel> history;

  ApplicationStatusHistoryListModel({
    required this.applicationId,
    required this.currentStatus,
    required this.total,
    this.disclaimer =
        'Status history entries reflect manual updates entered by the citizen. '
            'JanMitra Assist tracking records do not represent official government determinations.',
    required this.history,
  });

  factory ApplicationStatusHistoryListModel.fromJson(
      Map<String, dynamic> json) {
    return ApplicationStatusHistoryListModel(
      applicationId: json['application_id'] as String? ?? '',
      currentStatus:
          json['current_status'] as String? ?? ApplicationStatus.submitted,
      total: (json['total'] as num?)?.toInt() ?? 0,
      disclaimer: json['disclaimer'] as String? ??
          'Status history entries reflect manual updates entered by the citizen. '
              'JanMitra Assist tracking records do not represent official government determinations.',
      history: (json['history'] as List<dynamic>? ?? [])
          .map((item) => ApplicationStatusHistoryModel.fromJson(
              item as Map<String, dynamic>))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() => {
        'application_id': applicationId,
        'current_status': currentStatus,
        'total': total,
        'disclaimer': disclaimer,
        'history': history.map((h) => h.toJson()).toList(),
      };
}

/// Citizen reminder/task associated with a tracked application.
class ReminderModel {
  final String id;
  final String applicationId;
  final String userId;
  final String title;
  final String? description;
  final DateTime reminderDate;
  final bool isCompleted;
  final DateTime? completedAt;
  final DateTime createdAt;
  final DateTime updatedAt;

  ReminderModel({
    required this.id,
    required this.applicationId,
    required this.userId,
    required this.title,
    this.description,
    required this.reminderDate,
    this.isCompleted = false,
    this.completedAt,
    required this.createdAt,
    required this.updatedAt,
  });

  bool get isOverdue => !isCompleted && reminderDate.isBefore(DateTime.now());

  bool get isDueToday {
    if (isCompleted) return false;
    final now = DateTime.now();
    return reminderDate.year == now.year &&
        reminderDate.month == now.month &&
        reminderDate.day == now.day;
  }

  factory ReminderModel.fromJson(Map<String, dynamic> json) {
    return ReminderModel(
      id: json['id'] as String? ?? '',
      applicationId: json['application_id'] as String? ?? '',
      userId: json['user_id'] as String? ?? '',
      title: json['title'] as String? ?? '',
      description: json['description'] as String?,
      reminderDate: json['reminder_date'] != null
          ? DateTime.tryParse(json['reminder_date'] as String) ?? DateTime.now()
          : DateTime.now(),
      isCompleted: json['is_completed'] as bool? ?? false,
      completedAt: json['completed_at'] != null
          ? DateTime.tryParse(json['completed_at'] as String)
          : null,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'] as String) ?? DateTime.now()
          : DateTime.now(),
      updatedAt: json['updated_at'] != null
          ? DateTime.tryParse(json['updated_at'] as String) ?? DateTime.now()
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'application_id': applicationId,
        'user_id': userId,
        'title': title,
        'description': description,
        'reminder_date': reminderDate.toUtc().toIso8601String(),
        'is_completed': isCompleted,
        'completed_at': completedAt?.toUtc().toIso8601String(),
        'created_at': createdAt.toUtc().toIso8601String(),
        'updated_at': updatedAt.toUtc().toIso8601String(),
      };
}

/// Collection of reminders.
class ReminderListResponseModel {
  final int total;
  final List<ReminderModel> reminders;

  ReminderListResponseModel({
    required this.total,
    required this.reminders,
  });

  factory ReminderListResponseModel.fromJson(Map<String, dynamic> json) {
    return ReminderListResponseModel(
      total: (json['total'] as num?)?.toInt() ?? 0,
      reminders: (json['reminders'] as List<dynamic>? ?? [])
          .map((item) => ReminderModel.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() => {
        'total': total,
        'reminders': reminders.map((r) => r.toJson()).toList(),
      };
}

/// Citizen request payload to create a reminder for an application.
class ReminderCreateRequestModel {
  final String title;
  final DateTime reminderDate;
  final String? description;

  ReminderCreateRequestModel({
    required this.title,
    required this.reminderDate,
    this.description,
  });

  Map<String, dynamic> toJson() {
    final map = <String, dynamic>{
      'title': title.trim(),
      'reminder_date': reminderDate.toUtc().toIso8601String(),
    };
    if (description != null && description!.trim().isNotEmpty) {
      map['description'] = description!.trim();
    }
    return map;
  }
}

/// Citizen request payload to update reminder details or toggle completion.
class ReminderUpdateRequestModel {
  final String? title;
  final DateTime? reminderDate;
  final String? description;
  final bool? isCompleted;

  ReminderUpdateRequestModel({
    this.title,
    this.reminderDate,
    this.description,
    this.isCompleted,
  });

  Map<String, dynamic> toJson() {
    final map = <String, dynamic>{};
    if (title != null && title!.trim().isNotEmpty) {
      map['title'] = title!.trim();
    }
    if (reminderDate != null) {
      map['reminder_date'] = reminderDate!.toUtc().toIso8601String();
    }
    if (description != null) {
      map['description'] = description!.trim();
    }
    if (isCompleted != null) {
      map['is_completed'] = isCompleted;
    }
    return map;
  }
}

/// Confirmation of reminder deletion.
class ReminderDeleteResponseModel {
  final String id;
  final String message;

  ReminderDeleteResponseModel({
    required this.id,
    required this.message,
  });

  factory ReminderDeleteResponseModel.fromJson(Map<String, dynamic> json) {
    return ReminderDeleteResponseModel(
      id: json['id'] as String? ?? '',
      message: json['message'] as String? ?? 'Reminder deleted successfully.',
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'message': message,
      };
}
