import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import '../../models/scheme_intelligence_models.dart';
import '../../services/scheme_service.dart';

class SchemeBeneficiaryAnalyticsWidget extends StatefulWidget {
  final String schemeId;
  final String schemeName;

  const SchemeBeneficiaryAnalyticsWidget({
    super.key,
    required this.schemeId,
    required this.schemeName,
  });

  @override
  State<SchemeBeneficiaryAnalyticsWidget> createState() =>
      _SchemeBeneficiaryAnalyticsWidgetState();
}

class _SchemeBeneficiaryAnalyticsWidgetState
    extends State<SchemeBeneficiaryAnalyticsWidget> {
  final SchemeService _schemeService = SchemeService();
  bool _isLoading = true;
  String? _errorMessage;
  SchemeAnalyticsDatasetModel? _dataset;

  @override
  void initState() {
    super.initState();
    _loadAnalytics();
  }

  Future<void> _loadAnalytics() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final dataset = await _schemeService.getSchemeAnalytics(widget.schemeId);
      if (mounted) {
        setState(() {
          _dataset = dataset;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  String _formatNumber(int num) {
    if (num >= 10000000) {
      final crore = (num / 10000000).toStringAsFixed(1);
      return '$crore Crore (${(num / 1000000).toStringAsFixed(0)}M)';
    } else if (num >= 100000) {
      final lakh = (num / 100000).toStringAsFixed(1);
      return '$lakh Lakh';
    } else if (num >= 1000) {
      return '${(num / 1000).toStringAsFixed(1)}K';
    }
    return num.toString();
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Card(
        child: Padding(
          padding: EdgeInsets.all(24.0),
          child: Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                CircularProgressIndicator(),
                SizedBox(height: 12),
                Text('Loading official beneficiary analytics...'),
              ],
            ),
          ),
        ),
      );
    }

    if (_dataset == null) {
      return Card(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Row(
            children: [
              const Icon(Icons.info_outline, color: Colors.grey),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  _errorMessage ??
                      'Official government beneficiary dataset is pending verification for this scheme.',
                  style: const TextStyle(color: Colors.grey, fontSize: 13),
                ),
              ),
            ],
          ),
        ),
      );
    }

    final ds = _dataset!;
    final casteBreakdowns =
        ds.breakdowns.where((b) => b.dimension == 'caste_category').toList();
    final genderBreakdowns =
        ds.breakdowns.where((b) => b.dimension == 'gender').toList();
    final stateBreakdowns =
        ds.breakdowns.where((b) => b.dimension == 'state' || b.dimension == 'district').toList();

    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Title Header & Verified Pill
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: const [
                          Icon(Icons.analytics_outlined,
                              color: AppTheme.primaryNavy, size: 20),
                          SizedBox(width: 6),
                          Text(
                            'Official Beneficiary Analytics',
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 16,
                              color: AppTheme.primaryNavy,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Reporting Period: ${ds.reportingPeriod}',
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppTheme.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: const Color(0xFFDCFCE7),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFF86EFAC)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Icon(Icons.verified,
                          size: 14, color: Color(0xFF15803D)),
                      const SizedBox(width: 4),
                      Text(
                        ds.verificationStatus,
                        style: const TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF15803D),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),

            const SizedBox(height: 16),

            // Top Total Beneficiaries KPI Card
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [AppTheme.primaryNavy, Color(0xFF1E3A8A)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'TOTAL VERIFIED GOVERNMENT BENEFICIARIES',
                    style: TextStyle(
                      color: Colors.white70,
                      fontSize: 11,
                      letterSpacing: 0.8,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    _formatNumber(ds.totalBeneficiaries),
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Metric: ${ds.metricType.replaceAll('_', ' ').toUpperCase()}',
                    style: const TextStyle(color: Colors.white70, fontSize: 11),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 16),

            // Caste / Category Distribution Section
            const Text(
              'Category / Caste Distribution',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 14,
                color: AppTheme.textPrimary,
              ),
            ),
            const SizedBox(height: 8),
            if (casteBreakdowns.isNotEmpty) ...[
              ...casteBreakdowns.map((item) {
                final pct = item.percentage ??
                    (ds.totalBeneficiaries > 0
                        ? (item.metricValue / ds.totalBeneficiaries) * 100
                        : 0.0);
                return Padding(
                  padding: const EdgeInsets.only(bottom: 8.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            item.categoryName,
                            style: const TextStyle(
                                fontSize: 13, fontWeight: FontWeight.w600),
                          ),
                          Text(
                            '${_formatNumber(item.metricValue)} (${pct.toStringAsFixed(1)}%)',
                            style: const TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.bold,
                                color: AppTheme.primaryNavy),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: (pct / 100).clamp(0.0, 1.0),
                          minHeight: 6,
                          backgroundColor: const Color(0xFFE2E8F0),
                          valueColor: const AlwaysStoppedAnimation<Color>(
                              AppTheme.primaryNavy),
                        ),
                      ),
                    ],
                  ),
                );
              }),
              const SizedBox(height: 12),
            ] else ...[
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                decoration: BoxDecoration(
                  color: const Color(0xFFFEF3C7),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFFFDE68A)),
                ),
                child: Row(
                  children: const [
                    Icon(Icons.info_outline, size: 18, color: Color(0xFFB45309)),
                    SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Caste-wise beneficiary data is not available from the verified official source.',
                        style: TextStyle(
                          fontSize: 12,
                          color: Color(0xFF92400E),
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
            ],

            // Gender Distribution
            if (genderBreakdowns.isNotEmpty) ...[
              const Text(
                'Gender Proportion',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                  color: AppTheme.textPrimary,
                ),
              ),
              const SizedBox(height: 8),
              Row(
                children: genderBreakdowns.map((g) {
                  final pct = g.percentage ??
                      (ds.totalBeneficiaries > 0
                          ? (g.metricValue / ds.totalBeneficiaries) * 100
                          : 50.0);
                  return Expanded(
                    child: Container(
                      margin: const EdgeInsets.symmetric(horizontal: 4),
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF8FAFC),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: const Color(0xFFE2E8F0)),
                      ),
                      child: Column(
                        children: [
                          Icon(
                            g.categoryName.toLowerCase().contains('female')
                                ? Icons.female
                                : Icons.male,
                            color: AppTheme.primaryNavy,
                            size: 20,
                          ),
                          const SizedBox(height: 4),
                          Text(
                            g.categoryName,
                            style: const TextStyle(
                                fontSize: 12, fontWeight: FontWeight.w600),
                            textAlign: TextAlign.center,
                          ),
                          Text(
                            '${pct.toStringAsFixed(1)}%',
                            style: const TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.bold,
                                color: AppTheme.primaryNavy),
                          ),
                          Text(
                            _formatNumber(g.metricValue),
                            style: const TextStyle(
                                fontSize: 11, color: Colors.grey),
                          ),
                        ],
                      ),
                    ),
                  );
                }).toList(),
              ),
              const SizedBox(height: 16),
            ],

            // Top State Distribution
            if (stateBreakdowns.isNotEmpty) ...[
              const Text(
                'Geographic Coverage (Top States / Regions)',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 14,
                  color: AppTheme.textPrimary,
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: stateBreakdowns.take(6).map((s) {
                  return Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: const Color(0xFFEFF6FF),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: const Color(0xFFBFDBFE)),
                    ),
                    child: Text(
                      '${s.categoryName}: ${_formatNumber(s.metricValue)}',
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                        color: Color(0xFF1E40AF),
                      ),
                    ),
                  );
                }).toList(),
              ),
              const SizedBox(height: 16),
            ],

            // Official Source Citation
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: const Color(0xFFF1F5F9),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.source_outlined,
                      size: 16, color: AppTheme.textSecondary),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Source: ${ds.sourceName}',
                          style: const TextStyle(
                              fontSize: 11, fontWeight: FontWeight.bold),
                        ),
                        if (ds.reportTitle != null)
                          Text(
                            'Report: ${ds.reportTitle}',
                            style: const TextStyle(
                                fontSize: 11, fontWeight: FontWeight.w500, color: Color(0xFF334155)),
                          ),
                        Text(
                          'Scope: ${ds.geographicScope} | URL: ${ds.sourceUrl}',
                          style: const TextStyle(
                              fontSize: 11, color: AppTheme.primaryNavy),
                        ),
                        if (ds.metricDefinition != null)
                          Padding(
                            padding: const EdgeInsets.only(top: 2.0),
                            child: Text(
                              'Definition: ${ds.metricDefinition}',
                              style: const TextStyle(fontSize: 10, color: Color(0xFF475569)),
                            ),
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 10),

            // Mandatory Civic Disclaimer
            Text(
              ds.civicDisclaimer,
              style: const TextStyle(
                fontSize: 10,
                color: Colors.grey,
                fontStyle: FontStyle.italic,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
