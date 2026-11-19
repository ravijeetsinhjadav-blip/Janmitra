import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../schemes/models/scheme_intelligence_models.dart';
import '../../../schemes/services/scheme_service.dart';
import '../widgets/upload_document_dialog.dart';

class DocumentGuideScreen extends StatefulWidget {
  final String documentType;
  final String? documentTitle;

  const DocumentGuideScreen({
    super.key,
    required this.documentType,
    this.documentTitle,
  });

  @override
  State<DocumentGuideScreen> createState() => _DocumentGuideScreenState();
}

class _DocumentGuideScreenState extends State<DocumentGuideScreen> {
  final SchemeService _schemeService = SchemeService();
  bool _isLoading = true;
  String? _errorMessage;
  DocumentGuideModel? _guide;

  String _selectedState = 'Maharashtra';
  String _selectedLanguage = 'en';

  @override
  void initState() {
    super.initState();
    _loadGuide();
  }

  Future<void> _loadGuide() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final guide = await _schemeService.getDocumentGuide(widget.documentType);
      if (mounted) {
        setState(() {
          _guide = guide;
          _isLoading = false;
          if (guide != null && guide.stateSpecificAuthority.isNotEmpty) {
            _selectedState = guide.stateSpecificAuthority.keys.first;
          }
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

  void _openUploadDialog() {
    showDialog(
      context: context,
      builder: (_) => UploadDocumentDialog(
        initialDocumentType: widget.documentType,
        onUploadSuccess: () {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Document successfully uploaded to your Vault!'),
              backgroundColor: AppTheme.successGreen,
            ),
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final title = _guide?.documentName ?? widget.documentTitle ?? 'Document Guide';

    return Scaffold(
      appBar: AppBar(
        title: Text(title, style: const TextStyle(fontSize: 18)),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh Guide',
            onPressed: _loadGuide,
          ),
        ],
      ),
      body: _buildBody(),
      bottomNavigationBar: _guide == null
          ? null
          : Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                boxShadow: [
                  BoxShadow(
                    color: const Color(0x0D000000),
                    offset: const Offset(0, -2),
                    blurRadius: 8,
                  ),
                ],
              ),
              child: ElevatedButton.icon(
                onPressed: _openUploadDialog,
                icon: const Icon(Icons.cloud_upload_outlined),
                label: const Text('Upload This Document to Vault'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primaryNavy,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
              ),
            ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage != null || _guide == null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.menu_book_outlined, size: 48, color: Colors.grey),
              const SizedBox(height: 16),
              Text(
                _errorMessage ?? 'Guide information is being updated by department.',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.grey, fontSize: 15),
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: _loadGuide,
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }

    final guide = _guide!;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Document Overview Card
        Card(
          elevation: 1,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: const Color(0x141E3A8A),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Icon(Icons.verified_outlined, color: AppTheme.primaryNavy, size: 28),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            guide.documentName,
                            style: const TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                              color: AppTheme.textPrimary,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            'Department: ${guide.issuingDepartment}',
                            style: const TextStyle(
                              fontSize: 13,
                              color: AppTheme.textSecondary,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                const Divider(),
                const SizedBox(height: 8),
                Text(
                  guide.description,
                  style: const TextStyle(fontSize: 14, color: AppTheme.textPrimary, height: 1.4),
                ),
              ],
            ),
          ),
        ),

        const SizedBox(height: 16),

        // Fees & SLA Timelines Banner
        _buildFeesAndTimelinesCard(guide),

        const SizedBox(height: 16),

        // State-Specific Issuing Authority
        _buildIssuingAuthorityCard(guide),

        const SizedBox(height: 16),

        // Supporting Documents Required
        _buildSupportingDocumentsCard(guide),

        const SizedBox(height: 16),

        // Application Steps (Online & Offline) with Language Selector
        _buildApplicationStepsCard(guide),

        const SizedBox(height: 16),

        // Official Links & Portal Access
        _buildOfficialLinksCard(guide),

        const SizedBox(height: 24),
      ],
    );
  }

  Widget _buildFeesAndTimelinesCard(DocumentGuideModel guide) {
    final fees = guide.feesAndTimelines;
    final statutoryFee = fees['statutory_fee_inr'] ?? 0;
    final deliveryDays = fees['statutory_delivery_days'] ?? 15;
    final actNotice = fees['right_to_services_act'] ?? 'Guaranteed under Public Services Act';

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF0FDF4),
        border: Border.all(color: const Color(0xFFBBF7D0)),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.access_time_filled, color: AppTheme.successGreen, size: 20),
              const SizedBox(width: 8),
              const Text(
                'Statutory Fees & SLA Timelines',
                style: TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF166534), fontSize: 14),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: const Color(0xFFDCFCE7)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Statutory Fee', style: TextStyle(fontSize: 11, color: Colors.grey)),
                      const SizedBox(height: 2),
                      Text(
                        statutoryFee == 0 ? 'FREE' : '₹$statutoryFee',
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Color(0xFF15803D)),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: const Color(0xFFDCFCE7)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('SLA Delivery Limit', style: TextStyle(fontSize: 11, color: Colors.grey)),
                      const SizedBox(height: 2),
                      Text(
                        '$deliveryDays Working Days',
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Color(0xFF15803D)),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
            decoration: BoxDecoration(
              color: const Color(0xFFFEF3C7),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: const Color(0xFFFDE68A)),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const [
                Icon(Icons.info_outline, size: 16, color: Color(0xFFB45309)),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Fee and processing time may vary by state and application mode. Please confirm on the official state portal.',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w500,
                      color: Color(0xFF92400E),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 6),
          Text(
            actNotice.toString(),
            style: const TextStyle(fontSize: 11, color: Color(0xFF166534), fontStyle: FontStyle.italic),
          ),
        ],
      ),
    );
  }

  Widget _buildIssuingAuthorityCard(DocumentGuideModel guide) {
    final stateMap = guide.stateSpecificAuthority;
    final states = stateMap.keys.toList();
    final currentAuthority = stateMap[_selectedState] ?? stateMap['All India'] ?? guide.issuingDepartment;

    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Issuing Authority by State',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: AppTheme.textPrimary),
                ),
                if (states.length > 1)
                  DropdownButton<String>(
                    value: states.contains(_selectedState) ? _selectedState : states.first,
                    isDense: true,
                    style: const TextStyle(color: AppTheme.primaryNavy, fontWeight: FontWeight.bold, fontSize: 13),
                    items: states.map((s) {
                      return DropdownMenuItem<String>(
                        value: s,
                        child: Text(s),
                      );
                    }).toList(),
                    onChanged: (val) {
                      if (val != null) {
                        setState(() => _selectedState = val);
                      }
                    },
                  ),
              ],
            ),
            const SizedBox(height: 10),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.account_balance_outlined, color: AppTheme.primaryNavy, size: 22),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Competent Officer / Portal ($_selectedState):',
                          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.textSecondary),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          currentAuthority,
                          style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: AppTheme.textPrimary),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSupportingDocumentsCard(DocumentGuideModel guide) {
    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: const [
                Icon(Icons.folder_shared_outlined, color: AppTheme.accentGold, size: 20),
                SizedBox(width: 8),
                Text(
                  'Required Supporting Documents',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: AppTheme.textPrimary),
                ),
              ],
            ),
            const SizedBox(height: 6),
            const Text(
              'Attach self-attested copies of these proofs when applying:',
              style: TextStyle(fontSize: 12, color: AppTheme.textSecondary),
            ),
            const SizedBox(height: 12),
            ...guide.requiredSupportingDocuments.map((docProof) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 8.0),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.check_circle_outline, color: AppTheme.successGreen, size: 18),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        docProof,
                        style: const TextStyle(fontSize: 13, height: 1.3),
                      ),
                    ),
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }

  Widget _buildApplicationStepsCard(DocumentGuideModel guide) {
    final onlineSteps = guide.onlineSteps[_selectedLanguage] ?? guide.onlineSteps['en'] ?? [];
    final offlineSteps = guide.offlineSteps[_selectedLanguage] ?? guide.offlineSteps['en'] ?? [];

    return DefaultTabController(
      length: 2,
      child: Card(
        elevation: 1,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Step-by-Step Instructions',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: AppTheme.textPrimary),
                  ),
                  // Language Toggle
                  SegmentedButton<String>(
                    segments: const [
                      ButtonSegment(value: 'en', label: Text('EN', style: TextStyle(fontSize: 11))),
                      ButtonSegment(value: 'hi', label: Text('HI', style: TextStyle(fontSize: 11))),
                      ButtonSegment(value: 'gu', label: Text('GU', style: TextStyle(fontSize: 11))),
                    ],
                    selected: {_selectedLanguage},
                    onSelectionChanged: (newSelection) {
                      setState(() => _selectedLanguage = newSelection.first);
                    },
                    style: const ButtonStyle(
                      visualDensity: VisualDensity.compact,
                      tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              const TabBar(
                labelColor: AppTheme.primaryNavy,
                unselectedLabelColor: Colors.grey,
                indicatorColor: AppTheme.primaryNavy,
                tabs: [
                  Tab(text: 'Online Portal', icon: Icon(Icons.language, size: 18)),
                  Tab(text: 'Physical / Office', icon: Icon(Icons.storefront_outlined, size: 18)),
                ],
              ),
              const SizedBox(height: 12),
              SizedBox(
                height: 280,
                child: TabBarView(
                  children: [
                    // Online Steps
                    ListView.builder(
                      shrinkWrap: true,
                      itemCount: onlineSteps.length,
                      itemBuilder: (context, idx) {
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 10.0),
                          child: Text(
                            onlineSteps[idx],
                            style: const TextStyle(fontSize: 13, height: 1.4, color: AppTheme.textPrimary),
                          ),
                        );
                      },
                    ),
                    // Offline Steps
                    ListView.builder(
                      shrinkWrap: true,
                      itemCount: offlineSteps.length,
                      itemBuilder: (context, idx) {
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 10.0),
                          child: Text(
                            offlineSteps[idx],
                            style: const TextStyle(fontSize: 13, height: 1.4, color: AppTheme.textPrimary),
                          ),
                        );
                      },
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildOfficialLinksCard(DocumentGuideModel guide) {
    final links = guide.officialLinks;
    if (links.isEmpty) return const SizedBox.shrink();

    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: const [
                Icon(Icons.link, color: AppTheme.primaryNavy, size: 20),
                SizedBox(width: 8),
                Text(
                  'Verified Official Portals',
                  style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15, color: AppTheme.textPrimary),
                ),
              ],
            ),
            const SizedBox(height: 6),
            const Text(
              'Direct links to official state government delivery portals:',
              style: TextStyle(fontSize: 12, color: AppTheme.textSecondary),
            ),
            const SizedBox(height: 12),
            ...links.entries.map((entry) {
              final label = entry.key
                  .replaceAll('_', ' ')
                  .split(' ')
                  .map((w) => w.isNotEmpty ? '${w[0].toUpperCase()}${w.substring(1)}' : '')
                  .join(' ');
              return Padding(
                padding: const EdgeInsets.only(bottom: 8.0),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF1F5F9),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.open_in_new, size: 16, color: AppTheme.primaryNavy),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(label, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                            Text(entry.value, style: const TextStyle(fontSize: 11, color: AppTheme.textSecondary)),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }),
          ],
        ),
      ),
    );
  }
}
