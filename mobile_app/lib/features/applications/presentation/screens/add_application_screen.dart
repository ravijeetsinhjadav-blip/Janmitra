import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../schemes/models/scheme_models.dart';
import '../../../schemes/services/scheme_service.dart';
import '../../models/application_models.dart';
import '../../services/application_service.dart';
import '../widgets/application_disclaimer_card.dart';
import '../widgets/scheme_picker_bottom_sheet.dart';

/// Screen allowing citizens to record a formally submitted government application
/// for local tracking, status logging, and deadline reminders.
class AddApplicationScreen extends StatefulWidget {
  final SchemeModel? initialScheme;
  final ApplicationService? applicationService;
  final SchemeService? schemeService;

  const AddApplicationScreen({
    super.key,
    this.initialScheme,
    this.applicationService,
    this.schemeService,
  });

  @override
  State<AddApplicationScreen> createState() => _AddApplicationScreenState();
}

class _AddApplicationScreenState extends State<AddApplicationScreen> {
  final _formKey = GlobalKey<FormState>();

  late final ApplicationService _applicationService;
  late final SchemeService _schemeService;

  SchemeModel? _selectedScheme;
  late final TextEditingController _refNumberController;
  late final TextEditingController _remarksController;

  bool _refNumberNotIssued = false;
  DateTime _submissionDate = DateTime.now();
  bool _isSubmitting = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _applicationService = widget.applicationService ?? ApplicationService();
    _schemeService = widget.schemeService ?? SchemeService();
    _selectedScheme = widget.initialScheme;
    _refNumberController = TextEditingController();
    _remarksController = TextEditingController();
  }

  @override
  void dispose() {
    _refNumberController.dispose();
    _remarksController.dispose();
    super.dispose();
  }

  Future<void> _pickScheme() async {
    final picked = await SchemePickerBottomSheet.show(
      context,
      schemeService: _schemeService,
    );
    if (picked != null && mounted) {
      setState(() {
        _selectedScheme = picked;
        _errorMessage = null;
      });
    }
  }

  Future<void> _pickDate() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: _submissionDate.isAfter(now) ? now : _submissionDate,
      firstDate: DateTime(2000),
      lastDate: now,
      helpText: 'Select Portal Submission Date',
    );
    if (picked != null && mounted) {
      setState(() {
        _submissionDate = picked;
      });
    }
  }

  String _formatDate(DateTime dt) {
    final d = dt.day.toString().padLeft(2, '0');
    final m = dt.month.toString().padLeft(2, '0');
    final y = dt.year.toString();
    return '$d/$m/$y';
  }

  Future<void> _handleSubmit() async {
    if (_selectedScheme == null) {
      setState(() {
        _errorMessage = 'Please select a government scheme to track.';
      });
      return;
    }

    if (!_formKey.currentState!.validate()) {
      return;
    }

    setState(() {
      _isSubmitting = true;
      _errorMessage = null;
    });

    try {
      final request = ApplicationCreateRequestModel(
        schemeId: _selectedScheme!.id,
        applicationReferenceNumber: _refNumberNotIssued
            ? null
            : (_refNumberController.text.trim().isNotEmpty
                ? _refNumberController.text.trim()
                : null),
        referenceNumberNotIssued: _refNumberNotIssued,
        submissionDate: _submissionDate.toUtc(),
        remarks: _remarksController.text.trim().isNotEmpty
            ? _remarksController.text.trim()
            : null,
      );

      final created = await _applicationService.createApplication(request);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Application for "${created.schemeName}" is now being tracked.',
            ),
            backgroundColor: Colors.green.shade800,
          ),
        );
        Navigator.of(context).pop(created);
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString().replaceFirst('Exception: ', '');
          _isSubmitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Track Submitted Application'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const ApplicationDisclaimerCard(),
              const SizedBox(height: 16),
              if (_errorMessage != null) ...[
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.red.shade300),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.error_outline,
                          color: Colors.red.shade700, size: 20),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _errorMessage!,
                          style: TextStyle(
                              color: Colors.red.shade900, fontSize: 13),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
              ],

              // 1. Scheme Selection Card
              Card(
                elevation: 1,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                  side: BorderSide(
                    color: _selectedScheme == null
                        ? Colors.grey.shade300
                        : AppTheme.primaryBlue.withAlpha(60),
                  ),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text(
                            'Welfare Scheme *',
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.bold,
                              color: Colors.black87,
                            ),
                          ),
                          if (_selectedScheme != null)
                            TextButton.icon(
                              key: const Key('change_scheme_button'),
                              icon: const Icon(Icons.swap_horiz, size: 16),
                              label: const Text('Change'),
                              onPressed: _isSubmitting ? null : _pickScheme,
                              style: TextButton.styleFrom(
                                padding: EdgeInsets.zero,
                                visualDensity: VisualDensity.compact,
                              ),
                            ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      if (_selectedScheme == null)
                        OutlinedButton.icon(
                          key: const Key('select_scheme_button'),
                          icon: const Icon(Icons.search, size: 18),
                          label: const Text('Select Scheme from Catalog'),
                          style: OutlinedButton.styleFrom(
                            minimumSize: const Size.fromHeight(48),
                            foregroundColor: AppTheme.primaryBlue,
                          ),
                          onPressed: _isSubmitting ? null : _pickScheme,
                        )
                      else ...[
                        Text(
                          _selectedScheme!.schemeName,
                          key: const Key('selected_scheme_name'),
                          style: const TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.bold,
                            color: Colors.black87,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 8, vertical: 2),
                              decoration: BoxDecoration(
                                color: AppTheme.primaryBlue.withAlpha(25),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                _selectedScheme!.category,
                                style: const TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w600,
                                  color: AppTheme.primaryBlue,
                                ),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                _selectedScheme!.department,
                                style: TextStyle(
                                  fontSize: 12,
                                  color: Colors.grey.shade600,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 16),

              // 2. Application Reference Number Card
              Card(
                elevation: 1,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                  side: BorderSide(color: Colors.grey.shade300),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Application Reference Number',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: Colors.black87,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'The official acknowledgement or application number provided by the government portal.',
                        style: TextStyle(
                            fontSize: 12, color: Colors.grey.shade600),
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        key: const Key('reference_number_input'),
                        controller: _refNumberController,
                        enabled: !_refNumberNotIssued && !_isSubmitting,
                        decoration: InputDecoration(
                          hintText: 'e.g. MH/2026/PMAY/98231',
                          prefixIcon: const Icon(Icons.tag, size: 20),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8),
                          ),
                          filled: _refNumberNotIssued,
                          fillColor: Colors.grey.shade100,
                        ),
                        validator: (value) {
                          if (!_refNumberNotIssued &&
                              (value == null || value.trim().isEmpty)) {
                            return 'Enter reference number or check "Not yet issued" below';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 8),
                      CheckboxListTile(
                        key: const Key('ref_not_issued_checkbox'),
                        contentPadding: EdgeInsets.zero,
                        dense: true,
                        title: const Text(
                          'Reference number not yet issued by portal',
                          style: TextStyle(fontSize: 13),
                        ),
                        value: _refNumberNotIssued,
                        onChanged: _isSubmitting
                            ? null
                            : (val) {
                                setState(() {
                                  _refNumberNotIssued = val ?? false;
                                  if (_refNumberNotIssued) {
                                    _refNumberController.clear();
                                  }
                                });
                              },
                        controlAffinity: ListTileControlAffinity.leading,
                      ),
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 16),

              // 3. Submission Date Card
              Card(
                elevation: 1,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                  side: BorderSide(color: Colors.grey.shade300),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Portal Submission Date *',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: Colors.black87,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Date when you completed formal filing on the official government website.',
                        style: TextStyle(
                            fontSize: 12, color: Colors.grey.shade600),
                      ),
                      const SizedBox(height: 12),
                      InkWell(
                        key: const Key('submission_date_picker_tile'),
                        onTap: _isSubmitting ? null : _pickDate,
                        borderRadius: BorderRadius.circular(8),
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 14, vertical: 12),
                          decoration: BoxDecoration(
                            border: Border.all(color: Colors.grey.shade400),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Row(
                            children: [
                              const Icon(Icons.calendar_today,
                                  size: 18, color: AppTheme.primaryBlue),
                              const SizedBox(width: 12),
                              Text(
                                _formatDate(_submissionDate),
                                key: const Key('selected_date_text'),
                                style: const TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                  color: Colors.black87,
                                ),
                              ),
                              const Spacer(),
                              Text(
                                'Select Date',
                                style: TextStyle(
                                  fontSize: 13,
                                  color: AppTheme.primaryBlue,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 16),

              // 4. Initial Remarks (Optional)
              Card(
                elevation: 1,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                  side: BorderSide(color: Colors.grey.shade300),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Notes / Initial Remarks (Optional)',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: Colors.black87,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Any personal notes (e.g. portal acknowledgment details, submission center, receipt numbers).',
                        style: TextStyle(
                            fontSize: 12, color: Colors.grey.shade600),
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        key: const Key('remarks_input'),
                        controller: _remarksController,
                        enabled: !_isSubmitting,
                        maxLines: 2,
                        decoration: InputDecoration(
                          hintText: 'e.g. Filed online via MahaOnline portal',
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),

              const SizedBox(height: 24),

              // Submit Button
              ElevatedButton.icon(
                key: const Key('submit_application_button'),
                icon: _isSubmitting
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Icon(Icons.bookmark_add_outlined, size: 20),
                label: Text(
                  _isSubmitting ? 'Saving Application...' : 'Track Application',
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primaryBlue,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),
                onPressed: _isSubmitting ? null : _handleSubmit,
              ),

              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }
}
