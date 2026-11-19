class NotificationModel {
  final String id;
  final String userId;
  final String title;
  final String message;
  final String notificationType;
  final DateTime? scheduledAt;
  final bool isRead;
  final DateTime createdAt;

  NotificationModel({
    required this.id,
    required this.userId,
    required this.title,
    required this.message,
    required this.notificationType,
    this.scheduledAt,
    this.isRead = false,
    required this.createdAt,
  });

  factory NotificationModel.fromJson(Map<String, dynamic> json) {
    return NotificationModel(
      id: json['id'] as String? ?? '',
      userId: json['user_id'] as String? ?? '',
      title: json['title'] as String? ?? '',
      message: json['message'] as String? ?? '',
      notificationType: json['notification_type'] as String? ?? 'system',
      scheduledAt: json['scheduled_at'] != null
          ? DateTime.tryParse(json['scheduled_at'] as String)
          : null,
      isRead: json['is_read'] as bool? ?? false,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'] as String) ?? DateTime.now()
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'user_id': userId,
        'title': title,
        'message': message,
        'notification_type': notificationType,
        'scheduled_at': scheduledAt?.toUtc().toIso8601String(),
        'is_read': isRead,
        'created_at': createdAt.toUtc().toIso8601String(),
      };
}

class NotificationListResponseModel {
  final int total;
  final int unreadCount;
  final int page;
  final int pageSize;
  final int totalPages;
  final List<NotificationModel> notifications;

  NotificationListResponseModel({
    required this.total,
    required this.unreadCount,
    required this.page,
    required this.pageSize,
    required this.totalPages,
    required this.notifications,
  });

  factory NotificationListResponseModel.fromJson(Map<String, dynamic> json) {
    return NotificationListResponseModel(
      total: (json['total'] as num?)?.toInt() ?? 0,
      unreadCount: (json['unread_count'] as num?)?.toInt() ?? 0,
      page: (json['page'] as num?)?.toInt() ?? 1,
      pageSize: (json['page_size'] as num?)?.toInt() ?? 20,
      totalPages: (json['total_pages'] as num?)?.toInt() ?? 1,
      notifications: (json['notifications'] as List<dynamic>? ?? [])
          .map((item) =>
              NotificationModel.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }

  Map<String, dynamic> toJson() => {
        'total': total,
        'unread_count': unreadCount,
        'page': page,
        'page_size': pageSize,
        'total_pages': totalPages,
        'notifications': notifications.map((n) => n.toJson()).toList(),
      };
}

class UnreadCountResponseModel {
  final int unreadCount;

  UnreadCountResponseModel({required this.unreadCount});

  factory UnreadCountResponseModel.fromJson(Map<String, dynamic> json) {
    return UnreadCountResponseModel(
      unreadCount: (json['unread_count'] as num?)?.toInt() ?? 0,
    );
  }
}
