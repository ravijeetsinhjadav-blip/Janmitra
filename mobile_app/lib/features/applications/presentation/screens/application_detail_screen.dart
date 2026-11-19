import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../../core/theme/app_theme.dart';
import '../../models/application_models.dart';
import '../../services/application_service.dart';
import '../widgets/application_disclaimer_card.dart';
import '../widgets/application_status_badge.dart';

/// Full tracking detail view for a citizen application.
/// Displays qualified citizen-reported status, official portal link,
/// immutable status audit history, and personal reminders.
class ApplicationDetailScreen extends StatefulWidget {
  final String applicationId;
  final ApplicationModel? initialApplication;
  final ApplicationService? applicationService;

  const ApplicationDetailScreen({
    super.key,
    required this.applicationId,
    this.initialApplication,
    this.applicationService,
  });

  @override
  State<ApplicationDetailScreen> createState() =>
      _ApplicationDetailScreenState();
}

class _ApplicationDetailScreenState extends State<ApplicationDetailScreen> {
  late final ApplicationService _applicationService;

  ApplicationModel? _application;
  List<ApplicationStatusHistoryModel> _history = [];
  List<ReminderModel> _reminders = [];

  bool _isLoading = false;
  bool _isLoadingHistory = false;
  bool _isLoadingReminders = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _applicationService = widget.applicationService ?? ApplicationService();
    _application = widget.initialApplication;
    _loadAll();
  }

  Future<void> _loadAll() async {
    await Future.wait([
      _loadApplicationDetail(),
      _loadHistory(),
      _loadReminders(),
    ]);
  }

  Future<void> _loadApplicationDetail() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final app =
          await _applicationService.getApplicationById(widget.applicationId);
      if (mounted) {
        setState(() {
          _application = app;
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

  Future<void> _loadHistory() async {
    setState(() {
      _isLoadingHistory = true;
    });

    try {
      final res =
          await _applicationService.getApplicationHistory(widget.applicationId);
      if (mounted) {
        setState(() {
          _history = res.history;
          _isLoadingHistory = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _isLoadingHistory = false;
        });
      }
    }
  }

  Future<void> _loadReminders() async {
    setState(() {
      _isLoadingReminders = true;
    });

    try {
      final res = await _applicationService
          .getApplicationReminders(widget.applicationId);
      if (mounted) {
        setState(() {
          _reminders = res.reminders;
          _isLoadingReminders = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _isLoadingReminders = false;
        });
      }
    }
  }

  String _formatDate(DateTime? dt) {
    if (dt == null) return 'Not Available';
    final local = dt.toLocal();
    final d = local.day.toString().padLeft(2, '0');
    final m = local.month.toString().padLeft(2, '0');
    final y = local.year.toString();
    return '$d/$m/$y';
  }

  String _formatDateTime(DateTime? dt) {
    if (dt == null) return 'Not Available';
    final local = dt.toLocal();
    final d = local.day.toString().padLeft(2, '0');
    final m = local.month.toString().padLeft(2, '0');
    final y = local.year.toString();
    final h = local.hour.toString().padLeft(2, '0');
    final min = local.minute.toString().padLeft(2, '0');
    return '$d/$m/$y at $h:$min';
  }

  void _copyToClipboard(String text, String label) {
    Clipboard.setData(ClipboardData(text: text));
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('$label copied to clipboard'),
        duration: const Duration(seconds: 2),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Status Update Bottom Sheet
  // ---------------------------------------------------------------------------
  Future<void> _showStatusUpdateSheet() async {
    if (_application == null) return;

    final currentStatus = _application!.status;
    String selectedStatus = currentStatus;
    final remarksController = TextEditingController();
    final refController = TextEditingController(
      text: _application!.applicationReferenceNumber ?? '',
    );
    bool isUpdating = false;
    String? updateError;

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (sheetContext, setSheetState) {
            return Padding(
              padding: EdgeInsets.only(
                top: 20,
                left: 20,
                right: 20,
                bottom: MediaQuery.of(sheetContext).viewInsets.bottom + 20,
              ),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text(
                          'Update Application Progress',
                          style: TextStyle(
                            fontSize: 17,
                            fontWeight: FontWeight.bold,
                            color: Colors.black87,
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.close),
                          onPressed: () => Navigator.of(sheetContext).pop(),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: Colors.amber.shade50,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: Colors.amber.shade300),
                      ),
                      child: Text(
                        'Updates logged here reflect your personal citizen reporting. They do not officially submit documents or communicate with government portals.',
                        style: TextStyle(
                            fontSize: 12, color: Colors.amber.shade900),
                      ),
                    ),
                    const SizedBox(height: 16),
                    if (updateError != null) ...[
                      Text(
                        updateError!,
                        style:
                            TextStyle(color: Colors.red.shade800, fontSize: 13),
                      ),
                      const SizedBox(height: 8),
                    ],
                    const Text(
                      'Reported Status *',
                      style:
                          TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    DropdownButtonFormField<String>(
                      key: const Key('status_dropdown'),
                      initialValue: selectedStatus,
                      decoration: InputDecoration(
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                        contentPadding: const EdgeInsets.symmetric(
                            horizontal: 12, vertical: 12),
                      ),
                      items: const [
                        DropdownMenuItem(
                            value: 'Submitted', child: Text('Submitted')),
                        DropdownMenuItem(
                            value: 'Under Review', child: Text('Under Review')),
                        DropdownMenuItem(
                            value: 'Pending', child: Text('Pending')),
                        DropdownMenuItem(
                            value: 'Document Verification',
                            child: Text('Document Verification')),
                        DropdownMenuItem(
                            value: 'Approved',
                            child: Text('Approved (Citizen Reported)')),
                        DropdownMenuItem(
                            value: 'Rejected',
                            child: Text('Rejected (Citizen Reported)')),
                        DropdownMenuItem(
                            value: 'Completed', child: Text('Completed')),
                      ],
                      onChanged: isUpdating
                          ? null
                          : (val) {
                              if (val != null) {
                                setSheetState(() {
                                  selectedStatus = val;
                                });
                              }
                            },
                    ),
                    const SizedBox(height: 16),
                    const Text(
                      'Progress Remarks / Notes (Optional)',
                      style:
                          TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                      key: const Key('update_remarks_input'),
                      controller: remarksController,
                      maxLines: 2,
                      enabled: !isUpdating,
                      decoration: InputDecoration(
                        hintText: 'e.g. Completed biometrics at Tahsil office',
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    const Text(
                      'Reference Number (Update if issued)',
                      style:
                          TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                      key: const Key('update_ref_input'),
                      controller: refController,
                      enabled: !isUpdating,
                      decoration: InputDecoration(
                        hintText: 'e.g. MH/2026/PMAY/98231',
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                      ),
                    ),
                    const SizedBox(height: 20),
                    ElevatedButton(
                      key: const Key('save_status_update_button'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: AppTheme.primaryBlue,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                      ),
                      onPressed: isUpdating
                          ? null
                          : () async {
                              setSheetState(() {
                                isUpdating = true;
                                updateError = null;
                              });

                              try {
                                final newRef = refController.text.trim();
                                final req = ApplicationUpdateRequestModel(
                                  status: selectedStatus != currentStatus
                                      ? selectedStatus
                                      : null,
                                  remarks:
                                      remarksController.text.trim().isNotEmpty
                                          ? remarksController.text.trim()
                                          : null,
                                  applicationReferenceNumber: newRef
                                              .isNotEmpty &&
                                          newRef !=
                                              _application!
                                                  .applicationReferenceNumber
                                      ? newRef
                                      : null,
                                );

                                if (req.toJson().isEmpty) {
                                  setSheetState(() {
                                    updateError =
                                        'Please make a change before saving.';
                                    isUpdating = false;
                                  });
                                  return;
                                }

                                final updated =
                                    await _applicationService.updateApplication(
                                        widget.applicationId, req);

                                if (mounted) {
                                  setState(() {
                                    _application = updated;
                                  });
                                  if (sheetContext.mounted) {
                                    Navigator.of(sheetContext).pop();
                                  }
                                  _loadHistory();
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(
                                      content: Text('Status update recorded.'),
                                      backgroundColor: Colors.green,
                                    ),
                                  );
                                }
                              } catch (e) {
                                setSheetState(() {
                                  updateError = e
                                      .toString()
                                      .replaceFirst('Exception: ', '');
                                  isUpdating = false;
                                });
                              }
                            },
                      child: isUpdating
                          ? const SizedBox(
                              width: 18,
                              height: 18,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: Colors.white,
                              ),
                            )
                          : const Text('Save Status Update'),
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  // ---------------------------------------------------------------------------
  // Add Reminder Dialog
  // ---------------------------------------------------------------------------
  Future<void> _showAddReminderDialog() async {
    final titleController = TextEditingController();
    final descController = TextEditingController();
    DateTime reminderDate = DateTime.now().add(const Duration(days: 3));
    bool isSaving = false;
    String? dialogError;

    await showDialog<void>(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (dialogCtx, setDialogState) {
            return AlertDialog(
              title: const Text('Add Application Reminder'),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (dialogError != null) ...[
                      Text(
                        dialogError!,
                        style:
                            TextStyle(color: Colors.red.shade800, fontSize: 13),
                      ),
                      const SizedBox(height: 8),
                    ],
                    TextField(
                      key: const Key('reminder_title_input'),
                      controller: titleController,
                      enabled: !isSaving,
                      decoration: const InputDecoration(
                        labelText: 'Reminder Task *',
                        hintText: 'e.g. Submit original passbook at bank',
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      key: const Key('reminder_description_input'),
                      controller: descController,
                      enabled: !isSaving,
                      maxLines: 2,
                      decoration: const InputDecoration(
                        labelText: 'Instructions / Notes (Optional)',
                        hintText: 'e.g. Bring 2 passport size photos',
                      ),
                    ),
                    const SizedBox(height: 16),
                    ListTile(
                      key: const Key('reminder_date_picker_tile'),
                      contentPadding: EdgeInsets.zero,
                      leading:
                          const Icon(Icons.event, color: AppTheme.primaryBlue),
                      title: const Text('Scheduled Date'),
                      subtitle: Text(_formatDate(reminderDate)),
                      trailing: const Text('Change',
                          style: TextStyle(color: AppTheme.primaryBlue)),
                      onTap: isSaving
                          ? null
                          : () async {
                              final picked = await showDatePicker(
                                context: context,
                                initialDate: reminderDate,
                                firstDate: DateTime.now(),
                                lastDate: DateTime.now()
                                    .add(const Duration(days: 730)),
                              );
                              if (picked != null) {
                                setDialogState(() {
                                  reminderDate = DateTime(
                                    picked.year,
                                    picked.month,
                                    picked.day,
                                    10,
                                    0,
                                  );
                                });
                              }
                            },
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed:
                      isSaving ? null : () => Navigator.of(dialogCtx).pop(),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  key: const Key('save_reminder_button'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primaryBlue,
                    foregroundColor: Colors.white,
                  ),
                  onPressed: isSaving
                      ? null
                      : () async {
                          final title = titleController.text.trim();
                          if (title.isEmpty) {
                            setDialogState(() {
                              dialogError = 'Please enter a reminder task.';
                            });
                            return;
                          }

                          setDialogState(() {
                            isSaving = true;
                            dialogError = null;
                          });

                          try {
                            final req = ReminderCreateRequestModel(
                              title: title,
                              description: descController.text.trim().isNotEmpty
                                  ? descController.text.trim()
                                  : null,
                              reminderDate: reminderDate.toUtc(),
                            );
                            await _applicationService.createReminder(
                              widget.applicationId,
                              req,
                            );

                            if (mounted) {
                              if (dialogCtx.mounted) {
                                Navigator.of(dialogCtx).pop();
                              }
                              _loadReminders();
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(
                                  content: Text('Reminder added.'),
                                  backgroundColor: Colors.green,
                                ),
                              );
                            }
                          } catch (e) {
                            setDialogState(() {
                              dialogError =
                                  e.toString().replaceFirst('Exception: ', '');
                              isSaving = false;
                            });
                          }
                        },
                  child: isSaving
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Text('Add Reminder'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  // ---------------------------------------------------------------------------
  // Edit Reminder Dialog
  // ---------------------------------------------------------------------------
  Future<void> _showEditReminderDialog(ReminderModel reminder) async {
    final titleController = TextEditingController(text: reminder.title);
    final descController =
        TextEditingController(text: reminder.description ?? '');
    DateTime reminderDate = reminder.reminderDate;
    bool isSaving = false;
    String? dialogError;

    await showDialog<void>(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (dialogCtx, setDialogState) {
            return AlertDialog(
              title: const Text('Edit Application Reminder'),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (dialogError != null) ...[
                      Text(
                        dialogError!,
                        style:
                            TextStyle(color: Colors.red.shade800, fontSize: 13),
                      ),
                      const SizedBox(height: 8),
                    ],
                    TextField(
                      key: const Key('edit_reminder_title_input'),
                      controller: titleController,
                      enabled: !isSaving,
                      decoration: const InputDecoration(
                        labelText: 'Reminder Task *',
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      key: const Key('edit_reminder_description_input'),
                      controller: descController,
                      enabled: !isSaving,
                      maxLines: 2,
                      decoration: const InputDecoration(
                        labelText: 'Instructions / Notes (Optional)',
                      ),
                    ),
                    const SizedBox(height: 16),
                    ListTile(
                      contentPadding: EdgeInsets.zero,
                      leading:
                          const Icon(Icons.event, color: AppTheme.primaryBlue),
                      title: const Text('Scheduled Date'),
                      subtitle: Text(_formatDate(reminderDate)),
                      trailing: const Text('Change',
                          style: TextStyle(color: AppTheme.primaryBlue)),
                      onTap: isSaving
                          ? null
                          : () async {
                              final picked = await showDatePicker(
                                context: dialogCtx,
                                initialDate: reminderDate,
                                firstDate: DateTime.now()
                                    .subtract(const Duration(days: 30)),
                                lastDate: DateTime.now()
                                    .add(const Duration(days: 730)),
                              );
                              if (picked != null) {
                                setDialogState(() {
                                  reminderDate = DateTime(
                                    picked.year,
                                    picked.month,
                                    picked.day,
                                    10,
                                    0,
                                  );
                                });
                              }
                            },
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed:
                      isSaving ? null : () => Navigator.of(dialogCtx).pop(),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  key: const Key('update_reminder_button'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primaryBlue,
                    foregroundColor: Colors.white,
                  ),
                  onPressed: isSaving
                      ? null
                      : () async {
                          final title = titleController.text.trim();
                          if (title.isEmpty) {
                            setDialogState(() {
                              dialogError = 'Please enter a reminder task.';
                            });
                            return;
                          }

                          setDialogState(() {
                            isSaving = true;
                            dialogError = null;
                          });

                          try {
                            final req = ReminderUpdateRequestModel(
                              title: title,
                              description: descController.text.trim().isNotEmpty
                                  ? descController.text.trim()
                                  : null,
                              reminderDate: reminderDate.toUtc(),
                            );
                            final updated =
                                await _applicationService.updateReminder(
                              widget.applicationId,
                              reminder.id,
                              req,
                            );

                            if (mounted) {
                              setState(() {
                                final idx = _reminders
                                    .indexWhere((r) => r.id == reminder.id);
                                if (idx != -1) {
                                  _reminders[idx] = updated;
                                }
                              });
                              if (dialogCtx.mounted) {
                                Navigator.of(dialogCtx).pop();
                              }
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(
                                  content: Text('Reminder updated.'),
                                  backgroundColor: Colors.green,
                                ),
                              );
                            }
                          } catch (e) {
                            setDialogState(() {
                              dialogError =
                                  e.toString().replaceFirst('Exception: ', '');
                              isSaving = false;
                            });
                          }
                        },
                  child: isSaving
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Text('Save Changes'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  // ---------------------------------------------------------------------------
  // Toggle Reminder Completion
  // ---------------------------------------------------------------------------
  Future<void> _toggleReminder(ReminderModel reminder) async {
    try {
      final updated = await _applicationService.updateReminder(
        widget.applicationId,
        reminder.id,
        ReminderUpdateRequestModel(
          isCompleted: !reminder.isCompleted,
        ),
      );
      if (mounted) {
        setState(() {
          final idx = _reminders.indexWhere((r) => r.id == reminder.id);
          if (idx != -1) {
            _reminders[idx] = updated;
          }
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Could not update reminder: ${e.toString().replaceFirst("Exception: ", "")}',
            ),
            backgroundColor: Colors.red.shade800,
          ),
        );
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Delete Reminder Confirmation
  // ---------------------------------------------------------------------------
  Future<void> _deleteReminder(ReminderModel reminder) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Reminder?'),
        content: Text('Remove "${reminder.title}" from your reminders?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
            ),
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await _applicationService.deleteReminder(
            widget.applicationId, reminder.id);
        if (mounted) {
          setState(() {
            _reminders.removeWhere((r) => r.id == reminder.id);
          });
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Reminder deleted')),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                'Failed to delete: ${e.toString().replaceFirst("Exception: ", "")}',
              ),
              backgroundColor: Colors.red.shade800,
            ),
          );
        }
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Delete Tracking Record Confirmation
  // ---------------------------------------------------------------------------
  Future<void> _deleteApplication() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Remove from JanMitra?'),
        content: const Text(
          'This removes this tracking record, history, and reminders from your local JanMitra Assist account.\n\n'
          'IMPORTANT: This action does NOT cancel or withdraw your official application on the government portal.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            key: const Key('confirm_delete_application_button'),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red,
              foregroundColor: Colors.white,
            ),
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Delete Tracking Record'),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      try {
        await _applicationService.deleteApplication(widget.applicationId);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Application tracking record removed.'),
            ),
          );
          Navigator.of(context).pop(true);
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                'Delete failed: ${e.toString().replaceFirst("Exception: ", "")}',
              ),
              backgroundColor: Colors.red.shade800,
            ),
          );
        }
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Official Portal Departure Confirmation Dialog
  // ---------------------------------------------------------------------------
  Future<void> _openOfficialPortal(String portalUrl) async {
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.open_in_new, color: AppTheme.primaryBlue, size: 22),
            SizedBox(width: 8),
            Text('Official Portal Departure'),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'You are leaving JanMitra Assist to open the official government portal:',
              style: TextStyle(fontSize: 13, height: 1.4),
            ),
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.grey.shade100,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: Colors.grey.shade300),
              ),
              child: SelectableText(
                portalUrl,
                style: const TextStyle(
                  fontSize: 12,
                  fontFamily: 'monospace',
                  color: AppTheme.primaryBlue,
                ),
              ),
            ),
            const SizedBox(height: 12),
            const Text(
              'Government application processing, verification, and final approval are conducted solely by the respective department.',
              style: TextStyle(fontSize: 11, color: Colors.black54),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Close'),
          ),
          ElevatedButton.icon(
            icon: const Icon(Icons.copy, size: 16),
            label: const Text('Copy Portal Link'),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.primaryBlue,
              foregroundColor: Colors.white,
            ),
            onPressed: () {
              Navigator.of(ctx).pop();
              _copyToClipboard(portalUrl, 'Official portal link');
            },
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading && _application == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Application Details')),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    if (_errorMessage != null && _application == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Application Details')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.error_outline, size: 48, color: Colors.red.shade600),
                const SizedBox(height: 16),
                Text(
                  _errorMessage!,
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 15, color: Colors.black87),
                ),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: _loadAll,
                  child: const Text('Try Again'),
                ),
              ],
            ),
          ),
        ),
      );
    }

    final app = _application!;

    return Scaffold(
      appBar: AppBar(
        title: Text(app.schemeName),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh Application Details',
            onPressed: _loadAll,
          ),
          IconButton(
            key: const Key('delete_application_menu_button'),
            icon: const Icon(Icons.delete_outline),
            tooltip: 'Remove Tracking Record',
            onPressed: _deleteApplication,
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadAll,
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // 1. Disclaimer Card
              const ApplicationDisclaimerCard(),
              const SizedBox(height: 16),

              // 2. Scheme & Status Overview Card
              Card(
                elevation: 2,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  app.schemeName,
                                  style: const TextStyle(
                                    fontSize: 18,
                                    fontWeight: FontWeight.bold,
                                    color: Colors.black87,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  app.department ?? 'Department Not Specified',
                                  style: TextStyle(
                                    fontSize: 13,
                                    color: Colors.grey.shade600,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(width: 8),
                          ApplicationStatusBadge(
                            status: app.status,
                            showCitizenReportedTag: true,
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: AppTheme.primaryBlue.withAlpha(20),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              app.category ?? 'General',
                              style: const TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                                color: AppTheme.primaryBlue,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const Divider(height: 24),

                      // Reference Number Row
                      Row(
                        children: [
                          const Icon(Icons.tag,
                              size: 18, color: Colors.black54),
                          const SizedBox(width: 8),
                          const Text(
                            'Ref No:',
                            style: TextStyle(
                                fontSize: 13, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              app.hasReferenceNumber
                                  ? app.applicationReferenceNumber!
                                  : 'Not yet issued by portal',
                              key: const Key('detail_reference_number'),
                              style: TextStyle(
                                fontSize: 13,
                                color: app.hasReferenceNumber
                                    ? Colors.black87
                                    : Colors.orange.shade800,
                                fontStyle: app.hasReferenceNumber
                                    ? FontStyle.normal
                                    : FontStyle.italic,
                              ),
                            ),
                          ),
                          if (app.hasReferenceNumber)
                            IconButton(
                              key: const Key('copy_ref_button'),
                              icon: const Icon(Icons.copy, size: 16),
                              tooltip: 'Copy Reference Number',
                              onPressed: () => _copyToClipboard(
                                app.applicationReferenceNumber!,
                                'Reference number',
                              ),
                            ),
                        ],
                      ),

                      // Submission Date Row
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          const Icon(Icons.calendar_today,
                              size: 18, color: Colors.black54),
                          const SizedBox(width: 8),
                          const Text(
                            'Submitted On:',
                            style: TextStyle(
                                fontSize: 13, fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            _formatDate(app.submissionDate),
                            key: const Key('detail_submission_date'),
                            style: const TextStyle(fontSize: 13),
                          ),
                        ],
                      ),

                      // Latest citizen remark from history if present
                      if (_history.any((h) =>
                          h.remarks != null &&
                          h.remarks!.trim().isNotEmpty)) ...[
                        const SizedBox(height: 12),
                        Container(
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: Colors.grey.shade50,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: Colors.grey.shade200),
                          ),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Icon(Icons.comment_outlined,
                                  size: 16, color: Colors.black54),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  _history
                                      .firstWhere((h) =>
                                          h.remarks != null &&
                                          h.remarks!.trim().isNotEmpty)
                                      .remarks!,
                                  key: const Key('detail_remarks'),
                                  style: const TextStyle(
                                      fontSize: 12, color: Colors.black87),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],

                      const SizedBox(height: 16),

                      // Action Buttons: Update Status & Official Portal
                      Row(
                        children: [
                          Expanded(
                            child: ElevatedButton.icon(
                              key: const Key('update_status_button'),
                              icon: const Icon(Icons.edit_note, size: 18),
                              label: const Text('Update Status'),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: AppTheme.primaryBlue,
                                foregroundColor: Colors.white,
                              ),
                              onPressed: _showStatusUpdateSheet,
                            ),
                          ),
                          if (app.officialApplicationUrl != null &&
                              app.officialApplicationUrl!.isNotEmpty) ...[
                            const SizedBox(width: 10),
                            Expanded(
                              child: OutlinedButton.icon(
                                key: const Key('official_portal_button'),
                                icon: const Icon(Icons.open_in_new, size: 16),
                                label: const Text('Official Portal'),
                                onPressed: () => _openOfficialPortal(
                                    app.officialApplicationUrl!),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 20),

              // 3. Reminders Section
              Card(
                elevation: 1,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Row(
                            children: [
                              const Icon(Icons.notifications_active_outlined,
                                  color: AppTheme.primaryBlue, size: 20),
                              const SizedBox(width: 8),
                              const Text(
                                'Personal Reminders',
                                style: TextStyle(
                                  fontSize: 15,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.black87,
                                ),
                              ),
                              const SizedBox(width: 6),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: AppTheme.primaryBlue.withAlpha(20),
                                  borderRadius: BorderRadius.circular(10),
                                ),
                                child: Text(
                                  '${_reminders.length}',
                                  style: const TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold,
                                    color: AppTheme.primaryBlue,
                                  ),
                                ),
                              ),
                            ],
                          ),
                          TextButton.icon(
                            key: const Key('add_reminder_button'),
                            icon: const Icon(Icons.add, size: 16),
                            label: const Text('Add'),
                            onPressed: _showAddReminderDialog,
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      if (_isLoadingReminders)
                        const Center(
                          child: Padding(
                            padding: EdgeInsets.all(12.0),
                            child: SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            ),
                          ),
                        )
                      else if (_reminders.isEmpty)
                        Container(
                          padding: const EdgeInsets.all(14),
                          decoration: BoxDecoration(
                            color: Colors.grey.shade50,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: const Row(
                            children: [
                              Icon(Icons.info_outline,
                                  color: Colors.grey, size: 18),
                              SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  'No reminders scheduled. Add deadline alerts for biometrics, document submissions, or follow-ups.',
                                  style: TextStyle(
                                      fontSize: 12, color: Colors.black54),
                                ),
                              ),
                            ],
                          ),
                        )
                      else
                        ListView.separated(
                          shrinkWrap: true,
                          physics: const NeverScrollableScrollPhysics(),
                          itemCount: _reminders.length,
                          separatorBuilder: (_, __) => const Divider(height: 1),
                          itemBuilder: (context, idx) {
                            final rem = _reminders[idx];
                            return ListTile(
                              contentPadding: EdgeInsets.zero,
                              onTap: () => _showEditReminderDialog(rem),
                              leading: Checkbox(
                                key: Key('reminder_checkbox_${rem.id}'),
                                value: rem.isCompleted,
                                onChanged: (_) => _toggleReminder(rem),
                              ),
                              title: Text(
                                rem.title,
                                style: TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w600,
                                  decoration: rem.isCompleted
                                      ? TextDecoration.lineThrough
                                      : null,
                                  color: rem.isCompleted
                                      ? Colors.grey
                                      : Colors.black87,
                                ),
                              ),
                              subtitle: Text(
                                'Due ${_formatDate(rem.reminderDate)}${rem.description != null ? " • ${rem.description}" : ""}',
                                style: TextStyle(
                                  fontSize: 11,
                                  color: rem.isCompleted
                                      ? Colors.grey
                                      : Colors.black54,
                                ),
                              ),
                              trailing: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  IconButton(
                                    key: Key('edit_reminder_${rem.id}'),
                                    icon: const Icon(Icons.edit_outlined,
                                        size: 18, color: Colors.black54),
                                    onPressed: () =>
                                        _showEditReminderDialog(rem),
                                    tooltip: 'Edit Reminder',
                                  ),
                                  IconButton(
                                    key: Key('delete_reminder_${rem.id}'),
                                    icon: const Icon(Icons.delete_outline,
                                        size: 18, color: Colors.grey),
                                    onPressed: () => _deleteReminder(rem),
                                    tooltip: 'Delete Reminder',
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 20),

              // 4. Status History & Audit Timeline Card
              Card(
                elevation: 1,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.history,
                              color: AppTheme.primaryBlue, size: 20),
                          const SizedBox(width: 8),
                          const Text(
                            'Status History & Audit Trail',
                            style: TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.bold,
                              color: Colors.black87,
                            ),
                          ),
                          const SizedBox(width: 6),
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: Colors.grey.shade200,
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Text(
                              '${_history.length}',
                              style: const TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(
                        'Chronological log of manual updates entered for this application.',
                        style: TextStyle(
                            fontSize: 11, color: Colors.grey.shade600),
                      ),
                      const SizedBox(height: 12),
                      if (_isLoadingHistory)
                        const Center(
                          child: Padding(
                            padding: EdgeInsets.all(12.0),
                            child: SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            ),
                          ),
                        )
                      else if (_history.isEmpty)
                        Container(
                          padding: const EdgeInsets.all(14),
                          decoration: BoxDecoration(
                            color: Colors.grey.shade50,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: const Text(
                            'No status updates recorded yet.',
                            style:
                                TextStyle(fontSize: 12, color: Colors.black54),
                          ),
                        )
                      else
                        ListView.builder(
                          shrinkWrap: true,
                          physics: const NeverScrollableScrollPhysics(),
                          itemCount: _history.length,
                          itemBuilder: (context, idx) {
                            final h = _history[idx];
                            return Container(
                              margin: const EdgeInsets.only(bottom: 12),
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: Colors.grey.shade50,
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: Colors.grey.shade200),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    mainAxisAlignment:
                                        MainAxisAlignment.spaceBetween,
                                    children: [
                                      ApplicationStatusBadge(
                                        status: h.newStatus,
                                        isCompact: true,
                                        showCitizenReportedTag: true,
                                      ),
                                      Text(
                                        _formatDateTime(h.createdAt),
                                        style: TextStyle(
                                          fontSize: 11,
                                          color: Colors.grey.shade600,
                                        ),
                                      ),
                                    ],
                                  ),
                                  if (h.previousStatus != null) ...[
                                    const SizedBox(height: 6),
                                    Text(
                                      'Previous: ${h.previousStatus}',
                                      style: TextStyle(
                                        fontSize: 11,
                                        color: Colors.grey.shade600,
                                      ),
                                    ),
                                  ],
                                  if (h.remarks != null &&
                                      h.remarks!.isNotEmpty) ...[
                                    const SizedBox(height: 6),
                                    Text(
                                      h.remarks!,
                                      style: const TextStyle(
                                        fontSize: 12,
                                        color: Colors.black87,
                                      ),
                                    ),
                                  ],
                                  const SizedBox(height: 4),
                                  Row(
                                    children: [
                                      Icon(
                                        h.source == HistorySource.userReported
                                            ? Icons.person_outline
                                            : Icons.settings_suggest_outlined,
                                        size: 13,
                                        color: Colors.grey.shade500,
                                      ),
                                      const SizedBox(width: 4),
                                      Text(
                                        h.source,
                                        style: TextStyle(
                                          fontSize: 10,
                                          fontWeight: FontWeight.w500,
                                          color: Colors.grey.shade500,
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 32),
            ],
          ),
        ),
      ),
    );
  }
}
