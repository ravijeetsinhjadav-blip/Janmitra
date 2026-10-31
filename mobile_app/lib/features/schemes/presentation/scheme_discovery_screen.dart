import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import '../models/scheme_models.dart';
import '../services/scheme_service.dart';
import 'assessment_history_screen.dart';
import 'recommended_schemes_screen.dart';
import 'scheme_details_screen.dart';

class SchemeDiscoveryScreen extends StatefulWidget {
  const SchemeDiscoveryScreen({super.key});

  @override
  State<SchemeDiscoveryScreen> createState() => _SchemeDiscoveryScreenState();
}

class _SchemeDiscoveryScreenState extends State<SchemeDiscoveryScreen> {
  final SchemeService _schemeService = SchemeService();
  final TextEditingController _searchController = TextEditingController();

  bool _isLoading = true;
  String? _errorMessage;
  List<SchemeModel> _schemes = [];
  List<SchemeCategoryModel> _categories = [];
  String _selectedCategory = 'All';
  String _selectedState = 'All';
  int _currentPage = 1;
  int _totalPages = 1;

  final List<String> _states = [
    'All',
    'Maharashtra',
    'Uttar Pradesh',
    'Bihar',
    'Madhya Pradesh',
    'Rajasthan',
    'Gujarat',
    'Karnataka',
    'Tamil Nadu',
    'West Bengal',
    'Delhi',
  ];

  @override
  void initState() {
    super.initState();
    _fetchCategories();
    _fetchSchemes();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _fetchCategories() async {
    try {
      final cats = await _schemeService.getCategories();
      if (mounted) {
        setState(() => _categories = cats);
      }
    } catch (_) {}
  }

  Future<void> _fetchSchemes({int page = 1}) async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final res = await _schemeService.getSchemes(
        query: _searchController.text.trim().isNotEmpty ? _searchController.text.trim() : null,
        category: _selectedCategory != 'All' ? _selectedCategory : null,
        state: _selectedState != 'All' ? _selectedState : null,
        page: page,
        pageSize: 15,
      );

      if (mounted) {
        setState(() {
          _schemes = res.items;
          _currentPage = res.page;
          _totalPages = res.totalPages;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString().replaceAll('Exception: ', '');
          _isLoading = false;
        });
      }
    }
  }

  void _onCategorySelected(String category) {
    setState(() {
      _selectedCategory = category;
      _currentPage = 1;
    });
    _fetchSchemes(page: 1);
  }

  void _onStateChanged(String? state) {
    if (state != null) {
      setState(() {
        _selectedState = state;
        _currentPage = 1;
      });
      _fetchSchemes(page: 1);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Government Schemes'),
        actions: [
          IconButton(
            icon: const Icon(Icons.auto_awesome),
            tooltip: 'Recommended Schemes',
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const RecommendedSchemesScreen()),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.history),
            tooltip: 'My Assessments',
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const AssessmentHistoryScreen()),
              );
            },
          ),
        ],
      ),
      body: Column(
        children: [
          // Search Bar & State Filter
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            child: Column(
              children: [
                TextField(
                  controller: _searchController,
                  decoration: InputDecoration(
                    hintText: 'Search schemes by keyword or ministry...',
                    prefixIcon: const Icon(Icons.search),
                    suffixIcon: _searchController.text.isNotEmpty
                        ? IconButton(
                            icon: const Icon(Icons.clear),
                            onPressed: () {
                              _searchController.clear();
                              _fetchSchemes(page: 1);
                            },
                          )
                        : null,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    contentPadding: const EdgeInsets.symmetric(vertical: 12),
                  ),
                  onSubmitted: (_) => _fetchSchemes(page: 1),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    const Icon(Icons.location_on_outlined, size: 18, color: Colors.black54),
                    const SizedBox(width: 6),
                    const Text('State Scope:', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10),
                        decoration: BoxDecoration(
                          color: Colors.grey.shade100,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.grey.shade300),
                        ),
                        child: DropdownButtonHideUnderline(
                          child: DropdownButton<String>(
                            value: _selectedState,
                            isDense: true,
                            items: _states
                                .map((s) => DropdownMenuItem(value: s, child: Text(s, style: const TextStyle(fontSize: 13))))
                                .toList(),
                            onChanged: _onStateChanged,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // Categories Horizontal Chips
          SizedBox(
            height: 44,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 12),
              children: [
                _buildCategoryChip('All'),
                ..._categories.map((c) => _buildCategoryChip(c.category, count: c.count)),
              ],
            ),
          ),
          const Divider(height: 12),

          // Schemes List
          Expanded(child: _buildSchemesList()),
        ],
      ),
    );
  }

  Widget _buildCategoryChip(String label, {int? count}) {
    final isSelected = _selectedCategory == label;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4.0),
      child: ChoiceChip(
        label: Text(count != null ? '$label ($count)' : label),
        selected: isSelected,
        selectedColor: AppTheme.primaryBlue,
        labelStyle: TextStyle(
          fontSize: 12,
          fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
          color: isSelected ? Colors.white : Colors.black87,
        ),
        onSelected: (selected) {
          if (selected) {
            _onCategorySelected(label);
          }
        },
      ),
    );
  }

  Widget _buildSchemesList() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.error_outline, size: 48, color: Colors.red.shade400),
              const SizedBox(height: 12),
              Text(
                _errorMessage!,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 14),
              ),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: () => _fetchSchemes(page: 1),
                icon: const Icon(Icons.refresh),
                label: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }

    if (_schemes.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.search_off, size: 54, color: Colors.grey.shade400),
              const SizedBox(height: 12),
              const Text(
                'No Welfare Schemes Found',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              const Text(
                'Try adjusting your search keywords, sector category, or state filter.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 13, color: Colors.black54),
              ),
            ],
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () => _fetchSchemes(page: 1),
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        itemCount: _schemes.length + (_totalPages > 1 ? 1 : 0),
        itemBuilder: (context, index) {
          if (index == _schemes.length) {
            return _buildPaginationControls();
          }
          final scheme = _schemes[index];
          return _buildSchemeCard(scheme);
        },
      ),
    );
  }

  Widget _buildSchemeCard(SchemeModel scheme) {
    return Card(
      elevation: 1,
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: Colors.grey.shade200),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () {
          Navigator.of(context).push(
            MaterialPageRoute(
              builder: (_) => SchemeDetailsScreen(scheme: scheme),
            ),
          );
        },
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header with Category & Demo Flag
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: AppTheme.primaryBlue.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      scheme.category,
                      style: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.primaryBlue,
                      ),
                    ),
                  ),
                  if (scheme.isDemoData)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: Colors.amber.shade50,
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: Colors.amber.shade300),
                      ),
                      child: Text(
                        'DEMO',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                          color: Colors.amber.shade900,
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                scheme.schemeName,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.primaryDark,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                scheme.shortDescription ?? scheme.description,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 13, color: Colors.black87),
              ),
              const SizedBox(height: 10),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.public, size: 14, color: Colors.black54),
                      const SizedBox(width: 4),
                      Text(
                        scheme.stateApplicability,
                        style: const TextStyle(fontSize: 11, color: Colors.black54),
                      ),
                    ],
                  ),
                  const Row(
                    children: [
                      Text(
                        'Details',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: AppTheme.primaryBlue,
                        ),
                      ),
                      Icon(Icons.arrow_forward_ios, size: 12, color: AppTheme.primaryBlue),
                    ],
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPaginationControls() {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 16.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          IconButton(
            icon: const Icon(Icons.chevron_left),
            onPressed: _currentPage > 1 ? () => _fetchSchemes(page: _currentPage - 1) : null,
          ),
          Text('Page $_currentPage of $_totalPages'),
          IconButton(
            icon: const Icon(Icons.chevron_right),
            onPressed: _currentPage < _totalPages ? () => _fetchSchemes(page: _currentPage + 1) : null,
          ),
        ],
      ),
    );
  }
}

