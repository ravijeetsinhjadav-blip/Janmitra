import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:geolocator/geolocator.dart';
import '../../../../core/network/auth_service.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../home/presentation/screens/home_screen.dart';
import '../../models/user_profile_model.dart';

class ProfileSetupScreen extends StatefulWidget {
  final bool isInitialSetup;
  final UserProfileModel? existingProfile;

  const ProfileSetupScreen({
    super.key,
    this.isInitialSetup = false,
    this.existingProfile,
  });

  @override
  State<ProfileSetupScreen> createState() => _ProfileSetupScreenState();
}

class _ProfileSetupScreenState extends State<ProfileSetupScreen> {
  final _formKey = GlobalKey<FormState>();
  final AuthService _authService = AuthService();

  final TextEditingController _fullNameController = TextEditingController();
  final TextEditingController _dobController = TextEditingController();
  final TextEditingController _districtController = TextEditingController();
  final TextEditingController _incomeController = TextEditingController();
  final TextEditingController _occupationController = TextEditingController();

  String _selectedState = 'Maharashtra';
  String _residenceType = 'rural';
  String? _selectedEducation;
  bool _isLoading = false;
  bool _isDetectingLocation = false;
  String? _errorMessage;

  static const List<String> _indianStates = [
    'Andhra Pradesh',
    'Arunachal Pradesh',
    'Assam',
    'Bihar',
    'Chhattisgarh',
    'Goa',
    'Gujarat',
    'Haryana',
    'Himachal Pradesh',
    'Jharkhand',
    'Karnataka',
    'Kerala',
    'Madhya Pradesh',
    'Maharashtra',
    'Manipur',
    'Meghalaya',
    'Mizoram',
    'Nagaland',
    'Odisha',
    'Punjab',
    'Rajasthan',
    'Sikkim',
    'Tamil Nadu',
    'Telangana',
    'Tripura',
    'Uttar Pradesh',
    'Uttarakhand',
    'West Bengal',
    'Delhi',
    'Jammu and Kashmir',
    'Ladakh',
  ];

  static const List<String> _educationLevels = [
    'Below 10th Standard',
    '10th Standard Pass',
    '12th Standard Pass',
    'Diploma / ITI',
    'Graduate / Bachelor Degree',
    'Post Graduate / Master Degree',
    'Doctorate / PhD',
  ];

  @override
  void initState() {
    super.initState();
    if (widget.existingProfile != null) {
      final p = widget.existingProfile!;
      _fullNameController.text = p.fullName;
      _dobController.text = p.dateOfBirth;
      if (_indianStates.contains(p.state)) {
        _selectedState = p.state;
      }
      _districtController.text = p.district;
      _residenceType =
          p.residenceType.toLowerCase() == 'urban' ? 'urban' : 'rural';
      if (p.annualFamilyIncome != null) {
        _incomeController.text = p.annualFamilyIncome!.toStringAsFixed(0);
      }
      if (p.occupation != null) {
        _occupationController.text = p.occupation!;
      }
      if (p.educationLevel != null &&
          _educationLevels.contains(p.educationLevel)) {
        _selectedEducation = p.educationLevel;
      }
    }
  }

  @override
  void dispose() {
    _fullNameController.dispose();
    _dobController.dispose();
    _districtController.dispose();
    _incomeController.dispose();
    _occupationController.dispose();
    super.dispose();
  }

  Future<void> _selectDateOfBirth() async {
    final DateTime initialDate =
        DateTime.now().subtract(const Duration(days: 365 * 25));
    final DateTime firstDate = DateTime(1930);
    final DateTime lastDate =
        DateTime.now().subtract(const Duration(days: 365 * 10));

    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: initialDate,
      firstDate: firstDate,
      lastDate: lastDate,
      helpText: 'Select Citizen Date of Birth',
    );

    if (picked != null) {
      final yyyy = picked.year.toString().padLeft(4, '0');
      final mm = picked.month.toString().padLeft(2, '0');
      final dd = picked.day.toString().padLeft(2, '0');
      setState(() {
        _dobController.text = '$yyyy-$mm-$dd';
      });
    }
  }

  /// Request location permission and automatically fetch District and State via GPS
  Future<void> _fetchDistrictFromLocation({bool triggeredByStateChange = false}) async {
    if (_isDetectingLocation) return;
    setState(() => _isDetectingLocation = true);

    try {
      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        if (mounted && !triggeredByStateChange) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Please turn on location (GPS) on your phone to auto-detect district.'),
              backgroundColor: AppTheme.saffronAccent,
            ),
          );
        }
        setState(() => _isDetectingLocation = false);
        return;
      }

      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
        if (permission == LocationPermission.denied) {
          if (mounted && !triggeredByStateChange) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('Location permission denied. Please enter district manually.'),
              ),
            );
          }
          setState(() => _isDetectingLocation = false);
          return;
        }
      }

      if (permission == LocationPermission.deniedForever) {
        if (mounted && !triggeredByStateChange) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Location permission permanently denied in settings. Please enter district manually.'),
            ),
          );
        }
        setState(() => _isDetectingLocation = false);
        return;
      }

      // Fetch current device GPS coordinates
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.medium,
          timeLimit: Duration(seconds: 10),
        ),
      );

      String? detectedDistrict;
      String? detectedState;

      // 1. Primary reverse geocoding: OpenStreetMap Nominatim
      try {
        final url = Uri.parse(
          'https://nominatim.openstreetmap.org/reverse?format=json&lat=${position.latitude}&lon=${position.longitude}&zoom=10&addressdetails=1',
        );
        final response = await http.get(
          url,
          headers: {'User-Agent': 'JanMitraAssist/1.0 (support@janmitra.gov.in)'},
        ).timeout(const Duration(seconds: 6));

        if (response.statusCode == 200) {
          final data = jsonDecode(response.body) as Map<String, dynamic>;
          final address = data['address'] as Map<String, dynamic>?;
          if (address != null) {
            detectedDistrict = (address['state_district'] ??
                    address['county'] ??
                    address['district'] ??
                    address['city'] ??
                    address['town'] ??
                    address['municipality'])
                ?.toString();
            detectedState = address['state']?.toString();
          }
        }
      } catch (_) {}

      // 2. Fallback reverse geocoding: BigDataCloud free client API
      if (detectedDistrict == null || detectedDistrict.isEmpty) {
        try {
          final fallbackUrl = Uri.parse(
            'https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${position.latitude}&longitude=${position.longitude}&localityLanguage=en',
          );
          final response = await http.get(fallbackUrl).timeout(const Duration(seconds: 6));
          if (response.statusCode == 200) {
            final data = jsonDecode(response.body) as Map<String, dynamic>;
            detectedDistrict = (data['locality'] ?? data['city'] ?? data['principalSubdivision'])?.toString();
            detectedState ??= data['principalSubdivision']?.toString();
          }
        } catch (_) {}
      }

      if (detectedDistrict != null && detectedDistrict.isNotEmpty) {
        final cleanDistrict = detectedDistrict
            .replaceAll(RegExp(r'\s+District', caseSensitive: false), '')
            .replaceAll(RegExp(r'\s+Division', caseSensitive: false), '')
            .trim();

        if (mounted) {
          setState(() {
            _districtController.text = cleanDistrict;
            if (detectedState != null && detectedState.isNotEmpty) {
              final match = _indianStates.firstWhere(
                (s) => s.toLowerCase() == detectedState!.toLowerCase(),
                orElse: () => '',
              );
              if (match.isNotEmpty) {
                _selectedState = match;
              }
            }
          });
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('📍 District auto-detected: $cleanDistrict${detectedState != null ? ", $detectedState" : ""}'),
              backgroundColor: AppTheme.accentGreen,
              duration: const Duration(seconds: 3),
            ),
          );
        }
      } else {
        if (mounted && !triggeredByStateChange) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Could not determine district from GPS. Please type it in.'),
            ),
          );
        }
      }
    } catch (e) {
      if (mounted && !triggeredByStateChange) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Location error: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isDetectingLocation = false);
      }
    }
  }

  Future<void> _handleSaveProfile() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      double? income;
      if (_incomeController.text.trim().isNotEmpty) {
        income = double.tryParse(_incomeController.text.trim());
      }

      final profile = UserProfileModel(
        fullName: _fullNameController.text.trim(),
        dateOfBirth: _dobController.text.trim(),
        state: _selectedState,
        district: _districtController.text.trim(),
        residenceType: _residenceType,
        annualFamilyIncome: income,
        occupation: _occupationController.text.trim().isEmpty
            ? null
            : _occupationController.text.trim(),
        educationLevel: _selectedEducation,
      );

      await _authService.saveUserProfile(profile);

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Citizen profile saved successfully!'),
          backgroundColor: AppTheme.accentGreen,
        ),
      );

      if (widget.isInitialSetup || !Navigator.of(context).canPop()) {
        Navigator.of(context).pushAndRemoveUntil(
          MaterialPageRoute(builder: (_) => const HomeScreen()),
          (route) => false,
        );
      } else {
        Navigator.of(context).pop(true);
      }
    } catch (e) {
      setState(() {
        _errorMessage = e.toString().replaceFirst('Exception: ', '');
      });
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.surfaceBg,
      appBar: AppBar(
        backgroundColor: AppTheme.primaryNavy,
        elevation: 0,
        title: Text(
          widget.isInitialSetup
              ? 'Complete Citizen Profile'
              : 'Edit Citizen Profile',
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
        automaticallyImplyLeading: !widget.isInitialSetup,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 16.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (widget.isInitialSetup) ...[
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFFEFF6FF), Color(0xFFDBEAFE)],
                    ),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: const Color(0xFFBFDBFE)),
                  ),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: AppTheme.primaryBlue.withAlpha(25),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(Icons.person_pin_rounded,
                            color: AppTheme.primaryBlue, size: 24),
                      ),
                      const SizedBox(width: 12),
                      const Expanded(
                        child: Text(
                          'Welcome to JanMitra Assist! Complete your profile to unlock instant AI eligibility for 7+ government schemes.',
                          style: TextStyle(
                            fontSize: 12.5,
                            height: 1.35,
                            color: AppTheme.primaryDark,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
              ],

              // Section 1: Basic Identity
              _buildSectionCard(
                title: 'Primary Citizen Identity',
                icon: Icons.badge_outlined,
                children: [
                  TextFormField(
                    controller: _fullNameController,
                    decoration: const InputDecoration(
                      labelText: 'Full Name *',
                      hintText: 'e.g. Ramesh Kumar',
                      prefixIcon: Icon(Icons.person_outline),
                    ),
                    validator: (val) => val == null || val.trim().isEmpty
                        ? 'Full name is required'
                        : null,
                  ),
                  const SizedBox(height: 14),
                  TextFormField(
                    controller: _dobController,
                    readOnly: true,
                    onTap: _selectDateOfBirth,
                    decoration: const InputDecoration(
                      labelText: 'Date of Birth (YYYY-MM-DD) *',
                      hintText: 'Tap to select your date of birth',
                      prefixIcon: Icon(Icons.calendar_today_outlined),
                      suffixIcon: Icon(Icons.arrow_drop_down),
                    ),
                    validator: (val) => val == null || val.trim().isEmpty
                        ? 'Date of birth is required'
                        : null,
                  ),
                ],
              ),
              const SizedBox(height: 14),

              // Section 2: Location & Residence
              _buildSectionCard(
                title: 'Geographic Location',
                icon: Icons.location_on_outlined,
                children: [
                  DropdownButtonFormField<String>(
                    initialValue: _selectedState,
                    decoration: const InputDecoration(
                      labelText: 'State of Residence *',
                      prefixIcon: Icon(Icons.map_outlined),
                    ),
                    items: _indianStates.map((s) {
                      return DropdownMenuItem(value: s, child: Text(s));
                    }).toList(),
                    onChanged: (val) {
                      if (val != null) {
                        setState(() => _selectedState = val);
                        // Trigger location permission & auto-detect district as requested
                        _fetchDistrictFromLocation(triggeredByStateChange: true);
                      }
                    },
                  ),
                  const SizedBox(height: 14),
                  TextFormField(
                    controller: _districtController,
                    decoration: InputDecoration(
                      labelText: 'District *',
                      hintText: 'e.g. Pune, Nagpur, Jaipur',
                      prefixIcon: const Icon(Icons.location_city_outlined),
                      suffixIcon: _isDetectingLocation
                          ? const SizedBox(
                              width: 24,
                              height: 24,
                              child: Padding(
                                padding: EdgeInsets.all(12),
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: AppTheme.primaryBlue,
                                ),
                              ),
                            )
                          : IconButton(
                              icon: const Icon(
                                Icons.my_location,
                                color: AppTheme.primaryBlue,
                              ),
                              tooltip:
                                  'Auto-detect District via Location (स्थान से स्वतः भरें)',
                              onPressed: () => _fetchDistrictFromLocation(),
                            ),
                    ),
                    validator: (val) => val == null || val.trim().isEmpty
                        ? 'District is required'
                        : null,
                  ),
                  const SizedBox(height: 4),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton.icon(
                      style: TextButton.styleFrom(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 4, vertical: 2),
                        minimumSize: Size.zero,
                        tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
                      icon: const Icon(Icons.my_location,
                          size: 14, color: AppTheme.primaryBlue),
                      label: Text(
                        _isDetectingLocation
                            ? 'Detecting location via GPS...'
                            : '📍 Auto-detect District via GPS (स्थान से स्वतः भरें)',
                        style: const TextStyle(
                          fontSize: 11.5,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.primaryBlue,
                        ),
                      ),
                      onPressed: _isDetectingLocation
                          ? null
                          : () => _fetchDistrictFromLocation(),
                    ),
                  ),
                  const SizedBox(height: 14),
                  const Text(
                    'Residence Type *',
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 13,
                      color: AppTheme.primaryDark,
                    ),
                  ),
                  const SizedBox(height: 8),
                  SegmentedButton<String>(
                    segments: const [
                      ButtonSegment<String>(
                        value: 'rural',
                        label: Text('Rural (ग्रामीण)'),
                        icon: Icon(Icons.holiday_village_outlined),
                      ),
                      ButtonSegment<String>(
                        value: 'urban',
                        label: Text('Urban (शहरी)'),
                        icon: Icon(Icons.location_city_outlined),
                      ),
                    ],
                    selected: {_residenceType},
                    onSelectionChanged: (Set<String> newSelection) {
                      setState(() => _residenceType = newSelection.first);
                    },
                  ),
                ],
              ),
              const SizedBox(height: 14),

              // Section 3: Socio-Economic Profile
              _buildSectionCard(
                title: 'Socio-Economic & Scheme Profiling',
                icon: Icons.work_outline,
                children: [
                  TextFormField(
                    controller: _incomeController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Annual Family Income (INR)',
                      hintText: 'e.g. 180000',
                      prefixIcon: Icon(Icons.currency_rupee),
                    ),
                  ),
                  const SizedBox(height: 14),
                  TextFormField(
                    controller: _occupationController,
                    decoration: const InputDecoration(
                      labelText: 'Occupation',
                      hintText: 'e.g. Farmer, Student, Artisan, Self-employed',
                      prefixIcon: Icon(Icons.work_outline),
                    ),
                  ),
                  const SizedBox(height: 14),
                  DropdownButtonFormField<String>(
                    initialValue: _selectedEducation,
                    decoration: const InputDecoration(
                      labelText: 'Education Level',
                      prefixIcon: Icon(Icons.school_outlined),
                    ),
                    hint: const Text('Select education level'),
                    items: _educationLevels.map((lvl) {
                      return DropdownMenuItem(value: lvl, child: Text(lvl));
                    }).toList(),
                    onChanged: (val) {
                      setState(() => _selectedEducation = val);
                    },
                  ),
                ],
              ),
              const SizedBox(height: 14),

              // Privacy Assurance Box
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: const Color(0xFFECFDF5),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFFA7F3D0)),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.verified_user_outlined,
                        color: Color(0xFF059669), size: 22),
                    SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'Aadhaar Privacy Commitment: Aadhaar number is NOT collected or stored in JanMitra Assist database.',
                        style: TextStyle(
                          fontSize: 11.5,
                          color: Color(0xFF065F46),
                          fontWeight: FontWeight.w500,
                          height: 1.3,
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              if (_errorMessage != null) ...[
                const SizedBox(height: 14),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: Colors.red.shade200),
                  ),
                  child: Text(
                    _errorMessage!,
                    style: TextStyle(color: Colors.red.shade800, fontSize: 13),
                  ),
                ),
              ],
              const SizedBox(height: 24),

              ElevatedButton(
                onPressed: _isLoading ? null : _handleSaveProfile,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primaryNavy,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  elevation: 2,
                ),
                child: _isLoading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : Text(
                        widget.isInitialSetup
                            ? 'Complete Setup & Explore Schemes'
                            : 'Save Citizen Profile',
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                          color: Colors.white,
                        ),
                      ),
              ),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSectionCard({
    required String title,
    required IconData icon,
    required List<Widget> children,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.borderColor),
        boxShadow: AppTheme.cardShadow,
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 20, color: AppTheme.primaryBlue),
              const SizedBox(width: 8),
              Text(
                title,
                style: const TextStyle(
                  fontSize: 14.5,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.primaryNavy,
                ),
              ),
            ],
          ),
          const Divider(height: 20, color: AppTheme.borderColor),
          ...children,
        ],
      ),
    );
  }
}
