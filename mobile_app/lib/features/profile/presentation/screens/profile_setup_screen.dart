import 'package:flutter/material.dart';
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
                      }
                    },
                  ),
                  const SizedBox(height: 14),
                  TextFormField(
                    controller: _districtController,
                    decoration: const InputDecoration(
                      labelText: 'District *',
                      hintText: 'e.g. Pune, Nagpur, Jaipur',
                      prefixIcon: Icon(Icons.location_city_outlined),
                    ),
                    validator: (val) => val == null || val.trim().isEmpty
                        ? 'District is required'
                        : null,
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
