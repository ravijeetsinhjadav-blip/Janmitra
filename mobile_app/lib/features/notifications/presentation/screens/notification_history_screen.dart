import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';
import '../../models/notification_models.dart';
import '../../services/notification_service.dart';

class NotificationHistoryScreen extends StatefulWidget {
  final NotificationService? notificationService;

  const NotificationHistoryScreen({super.key, this.notificationService});

  @override
  State<NotificationHistoryScreen> createState() =>
      _NotificationHistoryScreenState();
}

class _NotificationHistoryScreenState extends State<NotificationHistoryScreen> {
  late final NotificationService _notificationService;

  bool _isLoading = false;
  String? _errorMessage;
  List<NotificationModel> _notifications = [];
  int _unreadCount = 0;

  @override
  void initState() {
    super.initState();
    _notificationService = widget.notificationService ?? NotificationService();
    _loadNotifications();
  }

  Future<void> _loadNotifications() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final res =
          await _notificationService.getNotifications(page: 1, pageSize: 50);
      if (mounted) {
        setState(() {
          _notifications = res.notifications;
          _unreadCount = res.unreadCount;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString().replaceFirst('Exception: ', '');
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _markRead(NotificationModel notif) async {
    if (notif.isRead) return;
    try {
      await _notificationService.markAsRead(notif.id);
      if (mounted) {
        setState(() {
          final idx = _notifications.indexWhere((n) => n.id == notif.id);
          if (idx != -1) {
            _notifications[idx] = NotificationModel(
              id: notif.id,
              userId: notif.userId,
              title: notif.title,
              message: notif.message,
              notificationType: notif.notificationType,
              scheduledAt: notif.scheduledAt,
              isRead: true,
              createdAt: notif.createdAt,
            );
            if (_unreadCount > 0) _unreadCount--;
          }
        });
      }
    } catch (_) {}
  }

  Future<void> _markAllRead() async {
    try {
      await _notificationService.markAllAsRead();
      if (mounted) {
        setState(() {
          _notifications = _notifications
              .map((n) => NotificationModel(
                    id: n.id,
                    userId: n.userId,
                    title: n.title,
                    message: n.message,
                    notificationType: n.notificationType,
                    scheduledAt: n.scheduledAt,
                    isRead: true,
                    createdAt: n.createdAt,
                  ))
              .toList();
          _unreadCount = 0;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('All notifications marked as read')),
        );
      }
    } catch (_) {}
  }

  IconData _getTypeIcon(String type) {
    switch (type) {
      case 'scheme_alert':
        return Icons.campaign_outlined;
      case 'document_reminder':
        return Icons.alarm_on_outlined;
      case 'status_update':
        return Icons.fact_check_outlined;
      default:
        return Icons.notifications_none;
    }
  }

  Color _getTypeColor(String type) {
    switch (type) {
      case 'scheme_alert':
        return Colors.blue.shade700;
      case 'document_reminder':
        return Colors.orange.shade800;
      case 'status_update':
        return Colors.green.shade800;
      default:
        return Colors.grey.shade700;
    }
  }

  String _formatDateTime(DateTime dt) {
    final local = dt.toLocal();
    final d = local.day.toString().padLeft(2, '0');
    final m = local.month.toString().padLeft(2, '0');
    final y = local.year.toString();
    final h = local.hour.toString().padLeft(2, '0');
    final min = local.minute.toString().padLeft(2, '0');
    return '$d/$m/$y at $h:$min';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifications'),
        actions: [
          if (_unreadCount > 0)
            TextButton.icon(
              key: const Key('mark_all_read_button'),
              icon: const Icon(Icons.done_all, size: 16),
              label: const Text('Mark all read'),
              style:
                  TextButton.styleFrom(foregroundColor: AppTheme.primaryBlue),
              onPressed: _markAllRead,
            ),
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh Notifications',
            onPressed: _loadNotifications,
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading && _notifications.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage != null && _notifications.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.error_outline, size: 48, color: Colors.red.shade600),
              const SizedBox(height: 12),
              Text(
                _errorMessage!,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 14),
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: _loadNotifications,
                child: const Text('Try Again'),
              ),
            ],
          ),
        ),
      );
    }

    if (_notifications.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.notifications_off_outlined,
                  size: 56, color: Colors.grey.shade400),
              const SizedBox(height: 16),
              const Text(
                'No Notifications Yet',
                style: TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.bold,
                  color: Colors.black87,
                ),
              ),
              const SizedBox(height: 6),
              const Text(
                'Scheme deadline alerts, status updates, and document verification reminders will appear here.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 13, color: Colors.black54),
              ),
            ],
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadNotifications,
      child: ListView.separated(
        padding: const EdgeInsets.symmetric(vertical: 8),
        itemCount: _notifications.length,
        separatorBuilder: (_, __) => const Divider(height: 1),
        itemBuilder: (context, index) {
          final notif = _notifications[index];
          final typeColor = _getTypeColor(notif.notificationType);

          return InkWell(
            key: Key('notification_item_${notif.id}'),
            onTap: () => _markRead(notif),
            child: Container(
              color: notif.isRead
                  ? Colors.white
                  : AppTheme.primaryBlue.withAlpha(12),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: typeColor.withAlpha(25),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(_getTypeIcon(notif.notificationType),
                        size: 20, color: typeColor),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                notif.title,
                                style: TextStyle(
                                  fontSize: 14,
                                  fontWeight: notif.isRead
                                      ? FontWeight.w600
                                      : FontWeight.bold,
                                  color: Colors.black87,
                                ),
                              ),
                            ),
                            if (!notif.isRead) ...[
                              const SizedBox(width: 8),
                              Container(
                                width: 8,
                                height: 8,
                                decoration: const BoxDecoration(
                                  color: AppTheme.primaryBlue,
                                  shape: BoxShape.circle,
                                ),
                              ),
                            ],
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          notif.message,
                          style: TextStyle(
                            fontSize: 13,
                            color: Colors.grey.shade700,
                            height: 1.3,
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          _formatDateTime(notif.createdAt),
                          style: TextStyle(
                            fontSize: 11,
                            color: Colors.grey.shade500,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
