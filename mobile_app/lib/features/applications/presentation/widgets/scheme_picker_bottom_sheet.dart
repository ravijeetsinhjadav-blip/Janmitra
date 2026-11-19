import 'dart:async';
import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';
import '../../../schemes/models/scheme_models.dart';
import '../../../schemes/services/scheme_service.dart';

/// Searchable modal bottom sheet allowing citizens to select an official welfare scheme
/// from the existing JanMitra scheme catalog without duplicating scheme endpoints.
class SchemePickerBottomSheet extends StatefulWidget {
  /// Injectable scheme service for testing and custom use
  final SchemeService? schemeService;

  /// Optional initial search query
  final String? initialQuery;

  const SchemePickerBottomSheet({
    super.key,
    this.schemeService,
    this.initialQuery,
  });

  /// Static helper to display the picker as a modal bottom sheet
  static Future<SchemeModel?> show(
    BuildContext context, {
    SchemeService? schemeService,
    String? initialQuery,
  }) {
    return showModalBottomSheet<SchemeModel>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(ctx).viewInsets.bottom,
        ),
        child: SchemePickerBottomSheet(
          schemeService: schemeService,
          initialQuery: initialQuery,
        ),
      ),
    );
  }

  @override
  State<SchemePickerBottomSheet> createState() =>
      _SchemePickerBottomSheetState();
}

class _SchemePickerBottomSheetState extends State<SchemePickerBottomSheet> {
  late final SchemeService _schemeService;
  late final TextEditingController _searchController;

  Timer? _debounceTimer;
  int _activeRequestId = 0;

  bool _isLoading = false;
  String? _errorMessage;
  List<SchemeModel> _schemes = [];

  @override
  void initState() {
    super.initState();
    _schemeService = widget.schemeService ?? SchemeService();
    _searchController = TextEditingController(text: widget.initialQuery ?? '');
    _fetchSchemes(_searchController.text);
  }

  @override
  void dispose() {
    _debounceTimer?.cancel();
    _searchController.dispose();
    super.dispose();
  }

  void _onSearchChanged(String query) {
    _debounceTimer?.cancel();
    _debounceTimer = Timer(const Duration(milliseconds: 350), () {
      _fetchSchemes(query);
    });
  }

  Future<void> _fetchSchemes(String rawQuery) async {
    final query = rawQuery.trim();
    final requestId = ++_activeRequestId;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final response = await _schemeService.getSchemes(
        query: query.isNotEmpty ? query : null,
        page: 1,
        pageSize: 30,
      );

      // Discard out-of-order responses
      if (!mounted || requestId != _activeRequestId) return;

      setState(() {
        _schemes = response.items;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted || requestId != _activeRequestId) return;

      setState(() {
        _errorMessage = e.toString().replaceFirst('Exception: ', '');
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: BoxConstraints(
        maxHeight: MediaQuery.of(context).size.height * 0.85,
      ),
      child: Material(
        color: Colors.white,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        clipBehavior: Clip.antiAlias,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Drag handle
            Center(
              child: Container(
                margin: const EdgeInsets.only(top: 12, bottom: 8),
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),

            // Header
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: Row(
                children: [
                  const Icon(Icons.account_balance_outlined,
                      color: AppTheme.primaryBlue, size: 22),
                  const SizedBox(width: 8),
                  const Expanded(
                    child: Text(
                      'Select Government Scheme',
                      style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.bold,
                        color: Colors.black87,
                      ),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, size: 20),
                    tooltip: 'Close',
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
            ),

            // Search Input
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
              child: TextField(
                controller: _searchController,
                onChanged: _onSearchChanged,
                decoration: InputDecoration(
                  hintText: 'Search schemes by name or keyword...',
                  prefixIcon: const Icon(Icons.search, size: 20),
                  suffixIcon: _searchController.text.isNotEmpty
                      ? IconButton(
                          icon: const Icon(Icons.clear, size: 18),
                          onPressed: () {
                            _searchController.clear();
                            _fetchSchemes('');
                          },
                        )
                      : null,
                  contentPadding:
                      const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                    borderSide: BorderSide(color: Colors.grey.shade300),
                  ),
                  filled: true,
                  fillColor: Colors.grey.shade50,
                ),
              ),
            ),

            const Divider(height: 16),

            // Body Content
            Expanded(
              child: _buildBody(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(strokeWidth: 2.5),
            SizedBox(height: 12),
            Text(
              'Searching welfare schemes...',
              style: TextStyle(fontSize: 13, color: Colors.black54),
            ),
          ],
        ),
      );
    }

    if (_errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.error_outline_rounded,
                  size: 44, color: Colors.red.shade400),
              const SizedBox(height: 10),
              Text(
                _errorMessage!,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.red, fontSize: 13),
              ),
              const SizedBox(height: 14),
              ElevatedButton.icon(
                icon: const Icon(Icons.refresh, size: 16),
                label: const Text('Try Again'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primaryBlue,
                  foregroundColor: Colors.white,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                ),
                onPressed: () => _fetchSchemes(_searchController.text),
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
              Icon(Icons.search_off_rounded,
                  size: 48, color: Colors.grey.shade400),
              const SizedBox(height: 10),
              const Text(
                'No schemes found',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: Colors.black87,
                ),
              ),
              const SizedBox(height: 6),
              const Text(
                'Try searching with different keywords or check spelling.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 12, color: Colors.black54),
              ),
            ],
          ),
        ),
      );
    }

    return ListView.separated(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      itemCount: _schemes.length,
      separatorBuilder: (_, __) => const Divider(height: 1),
      itemBuilder: (context, index) {
        final scheme = _schemes[index];
        return ListTile(
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          title: Text(
            scheme.schemeName,
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: Colors.black87,
            ),
          ),
          subtitle: Padding(
            padding: const EdgeInsets.only(top: 4.0),
            child: Row(
              children: [
                if (scheme.category.isNotEmpty) ...[
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: AppTheme.primaryBlue.withAlpha(20),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      scheme.category,
                      style: const TextStyle(
                        fontSize: 11,
                        color: AppTheme.primaryBlue,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),
                ],
                Expanded(
                  child: Text(
                    scheme.department,
                    style: const TextStyle(fontSize: 11, color: Colors.black54),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
          ),
          trailing: const Icon(Icons.arrow_forward_ios_rounded,
              size: 14, color: Colors.black45),
          onTap: () {
            Navigator.of(context).pop(scheme);
          },
        );
      },
    );
  }
}
