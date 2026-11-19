import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';
import '../../models/application_models.dart';
import '../../services/application_service.dart';
import '../widgets/application_card.dart';
import '../widgets/application_disclaimer_card.dart';
import 'add_application_screen.dart';
import 'application_detail_screen.dart';

/// Screen displaying the citizen's tracked government applications.
/// Features status filtering, pull-to-refresh, incremental pagination,
/// empty/error states, and entry points to register and view details.
class ApplicationsListScreen extends StatefulWidget {
  final ApplicationService? applicationService;
  final void Function(ApplicationModel)? onApplicationTap;
  final VoidCallback? onAddApplication;

  const ApplicationsListScreen({
    super.key,
    this.applicationService,
    this.onApplicationTap,
    this.onAddApplication,
  });

  @override
  State<ApplicationsListScreen> createState() => _ApplicationsListScreenState();
}

class _ApplicationsListScreenState extends State<ApplicationsListScreen> {
  late final ApplicationService _applicationService;
  final ScrollController _scrollController = ScrollController();

  static const List<String> _statusFilters = [
    'All',
    'Submitted',
    'Under Review',
    'Pending',
    'Document Verification',
    'Approved',
    'Rejected',
    'Completed',
  ];

  String _selectedStatus = 'All';
  bool _isLoading = true;
  bool _isLoadingMore = false;
  String? _errorMessage;

  List<ApplicationModel> _applications = [];
  int _currentPage = 1;
  int _totalPages = 1;
  int _activeRequestId = 0;

  @override
  void initState() {
    super.initState();
    _applicationService = widget.applicationService ?? ApplicationService();
    _scrollController.addListener(_onScroll);
    _loadApplications();
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (!_scrollController.hasClients) return;
    final maxScroll = _scrollController.position.maxScrollExtent;
    final currentScroll = _scrollController.position.pixels;
    // Trigger load more when user is within 200px of bottom
    if (currentScroll >= (maxScroll - 200)) {
      _loadMoreApplications();
    }
  }

  Future<void> _loadApplications({bool isRefresh = false}) async {
    final requestId = ++_activeRequestId;

    if (!isRefresh) {
      setState(() {
        _isLoading = true;
        _isLoadingMore = false;
        _errorMessage = null;
      });
    } else {
      setState(() {
        _isLoadingMore = false;
      });
    }

    try {
      final statusParam = _selectedStatus == 'All' ? null : _selectedStatus;
      final response = await _applicationService.getApplications(
        status: statusParam,
        page: 1,
        pageSize: 20,
      );

      if (!mounted || requestId != _activeRequestId) return;

      setState(() {
        _applications = response.applications;
        _currentPage = 1;
        _totalPages = response.totalPages;
        _isLoading = false;
        _isLoadingMore = false;
        _errorMessage = null;
      });
    } catch (e) {
      if (!mounted || requestId != _activeRequestId) return;

      setState(() {
        _errorMessage = e.toString().replaceFirst('Exception: ', '');
        _isLoading = false;
        _isLoadingMore = false;
      });
    }
  }

  Future<void> _loadMoreApplications() async {
    if (_isLoading ||
        _isLoadingMore ||
        _currentPage >= _totalPages ||
        _errorMessage != null) {
      return;
    }

    final requestId = _activeRequestId;

    setState(() {
      _isLoadingMore = true;
    });

    try {
      final nextPage = _currentPage + 1;
      final statusParam = _selectedStatus == 'All' ? null : _selectedStatus;
      final response = await _applicationService.getApplications(
        status: statusParam,
        page: nextPage,
        pageSize: 20,
      );

      if (!mounted || requestId != _activeRequestId) return;

      setState(() {
        final existingIds = _applications.map((a) => a.id).toSet();
        for (final app in response.applications) {
          if (!existingIds.contains(app.id)) {
            _applications.add(app);
            existingIds.add(app.id);
          }
        }
        _currentPage = response.page;
        _totalPages = response.totalPages;
        _isLoadingMore = false;
      });
    } catch (_) {
      if (!mounted || requestId != _activeRequestId) return;
      setState(() {
        _isLoadingMore = false;
      });
    }
  }

  void _onStatusFilterSelected(String status) {
    if (_selectedStatus == status) return;
    setState(() {
      _selectedStatus = status;
    });
    _loadApplications();
  }

  void _handleCardTap(ApplicationModel application) async {
    if (widget.onApplicationTap != null) {
      widget.onApplicationTap!(application);
    } else {
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => ApplicationDetailScreen(
            applicationId: application.id,
            initialApplication: application,
            applicationService: _applicationService,
          ),
        ),
      );
      if (mounted) {
        _loadApplications(isRefresh: true);
      }
    }
  }

  void _handleAddApplication() async {
    if (widget.onAddApplication != null) {
      widget.onAddApplication!();
    } else {
      final created = await Navigator.of(context).push<ApplicationModel?>(
        MaterialPageRoute(
          builder: (_) => AddApplicationScreen(
            applicationService: _applicationService,
          ),
        ),
      );
      if (created != null && mounted) {
        _loadApplications(isRefresh: true);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('My Applications'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh Applications',
            onPressed: () => _loadApplications(isRefresh: true),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _handleAddApplication,
        icon: const Icon(Icons.add),
        label: const Text('Track Application'),
        backgroundColor: AppTheme.primaryBlue,
        foregroundColor: Colors.white,
      ),
      body: Column(
        children: [
          // Informational Legal / Boundary Notice Banner
          const Padding(
            padding: EdgeInsets.fromLTRB(16, 12, 16, 4),
            child: ApplicationDisclaimerCard(isCompact: true),
          ),

          // Status Filter Chips
          _buildFilterChipsBar(),

          const Divider(height: 1),

          // Main Content
          Expanded(
            child: _buildBody(),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterChipsBar() {
    return Container(
      height: 48,
      padding: const EdgeInsets.symmetric(vertical: 6),
      color: Colors.grey.shade50,
      child: ListView.separated(
        key: const Key('status_filter_list_view'),
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        itemCount: _statusFilters.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (context, index) {
          final status = _statusFilters[index];
          final isSelected = _selectedStatus == status;

          return ChoiceChip(
            label: Text(status),
            selected: isSelected,
            showCheckmark: false,
            selectedColor: AppTheme.primaryBlue.withAlpha(35),
            labelStyle: TextStyle(
              fontSize: 12,
              fontWeight: isSelected ? FontWeight.bold : FontWeight.w500,
              color: isSelected ? AppTheme.primaryBlue : Colors.black87,
            ),
            onSelected: (selected) {
              if (selected) {
                _onStatusFilterSelected(status);
              }
            },
          );
        },
      ),
    );
  }

  Widget _buildBody() {
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
              Icon(Icons.error_outline_rounded,
                  size: 48, color: Colors.red.shade400),
              const SizedBox(height: 12),
              Text(
                _errorMessage!,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 14, color: Colors.red),
              ),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                icon: const Icon(Icons.refresh, size: 16),
                label: const Text('Try Again'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primaryBlue,
                  foregroundColor: Colors.white,
                ),
                onPressed: () => _loadApplications(),
              ),
            ],
          ),
        ),
      );
    }

    if (_applications.isEmpty) {
      return _buildEmptyState();
    }

    return RefreshIndicator(
      onRefresh: () => _loadApplications(isRefresh: true),
      child: ListView.builder(
        key: const Key('applications_list_view'),
        controller: _scrollController,
        physics: const AlwaysScrollableScrollPhysics(),
        padding:
            const EdgeInsets.fromLTRB(16, 12, 16, 80), // bottom fab padding
        itemCount: _applications.length + (_isLoadingMore ? 1 : 0),
        itemBuilder: (context, index) {
          if (index < _applications.length) {
            final app = _applications[index];
            return ApplicationCard(
              application: app,
              onTap: () => _handleCardTap(app),
            );
          } else {
            return const Padding(
              padding: EdgeInsets.symmetric(vertical: 16.0),
              child: Center(
                child: SizedBox(
                  key: Key('pagination_loading_indicator'),
                  width: 22,
                  height: 22,
                  child: CircularProgressIndicator(strokeWidth: 2.5),
                ),
              ),
            );
          }
        },
      ),
    );
  }

  Widget _buildEmptyState() {
    final isFiltered = _selectedStatus != 'All';

    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(32.0),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: isFiltered
                    ? Colors.orange.shade50
                    : AppTheme.primaryBlue.withAlpha(20),
                shape: BoxShape.circle,
              ),
              child: Icon(
                isFiltered
                    ? Icons.filter_alt_off_outlined
                    : Icons.assignment_outlined,
                size: 52,
                color:
                    isFiltered ? Colors.orange.shade800 : AppTheme.primaryBlue,
              ),
            ),
            const SizedBox(height: 16),
            Text(
              isFiltered
                  ? 'No Applications Found'
                  : 'No Tracked Applications Yet',
              style: const TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.bold,
                color: Colors.black87,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              isFiltered
                  ? 'No applications currently have status "$_selectedStatus".'
                  : 'Track formal applications you have submitted on official government portals to maintain a timeline and personal reminders.',
              style: const TextStyle(
                  fontSize: 13, color: Colors.black54, height: 1.4),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 20),
            if (isFiltered)
              OutlinedButton.icon(
                icon: const Icon(Icons.clear_all_rounded, size: 16),
                label: const Text('Show All Applications'),
                onPressed: () => _onStatusFilterSelected('All'),
              )
            else
              ElevatedButton.icon(
                icon: const Icon(Icons.add, size: 16),
                label: const Text('Track Your First Application'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primaryBlue,
                  foregroundColor: Colors.white,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 22, vertical: 12),
                ),
                onPressed: _handleAddApplication,
              ),
          ],
        ),
      ),
    );
  }
}
