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
      appBar: AppBar(
        title: Text(widget.isInitialSetup
            ? 'Complete Citizen Profile'
            : 'Edit Citizen Profile'),
        automaticallyImplyLeading: !widget.isInitialSetup,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20.0),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (widget.isInitialSetup) ...[
                Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.blue.shade50,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: Colors.blue.shade200),
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.person_pin_rounded,
                          color: Colors.blue.shade800, size: 28),
                      const SizedBox(width: 12),
                      const Expanded(
                        child: Text(
                          'Welcome to JanMitra Assist! Please set up your basic profile so we can deliver tailored government scheme guidance.',
                          style: TextStyle(fontSize: 13, height: 1.4),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
              ],
              TextFormField(
                controller: _fullNameController,
                decoration: const InputDecoration(
                  labelText: 'Full Name *',
                  hintText: 'e.g. Ramesh Kumar',
                  prefixIcon: Icon(Icons.person_outline),
                  border: OutlineInputBorder(),
                ),
                validator: (val) => val == null || val.trim().isEmpty
                    ? 'Full name is required'
                    : null,
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _dobController,
                readOnly: true,
                onTap: _selectDateOfBirth,
                decoration: const InputDecoration(
                  labelText: 'Date of Birth (YYYY-MM-DD) *',
                  hintText: 'Tap to select your date of birth',
                  prefixIcon: Icon(Icons.calendar_today_outlined),
                  border: OutlineInputBorder(),
                ),
                validator: (val) => val == null || val.trim().isEmpty
                    ? 'Date of birth is required'
                    : null,
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                initialValue: _selectedState,
                decoration: const InputDecoration(
                  labelText: 'State of Residence *',
                  prefixIcon: Icon(Icons.map_outlined),
                  border: OutlineInputBorder(),
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
              const SizedBox(height: 16),
              TextFormField(
                controller: _districtController,
                decoration: const InputDecoration(
                  labelText: 'District *',
                  hintText: 'e.g. Pune, Nagpur, Jaipur',
                  prefixIcon: Icon(Icons.location_city_outlined),
                  border: OutlineInputBorder(),
                ),
                validator: (val) => val == null || val.trim().isEmpty
                    ? 'District is required'
                    : null,
              ),
              const SizedBox(height: 16),
              const Text(
                'Residence Type *',
                style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
              ),
              const SizedBox(height: 6),
              SegmentedButton<String>(
                segments: const [
                  ButtonSegment<String>(
                    value: 'rural',
                    label: Text('Rural'),
                    icon: Icon(Icons.holiday_village_outlined),
                  ),
                  ButtonSegment<String>(
                    value: 'urban',
                    label: Text('Urban'),
                    icon: Icon(Icons.location_city_outlined),
                  ),
                ],
                selected: {_residenceType},
                onSelectionChanged: (Set<String> newSelection) {
                  setState(() => _residenceType = newSelection.first);
                },
              ),
              const Divider(height: 32),
              const Text(
                'Optional Demographic Details',
                style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 15,
                    color: Colors.black87),
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _incomeController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Annual Family Income (INR)',
                  hintText: 'e.g. 180000',
                  prefixIcon: Icon(Icons.currency_rupee),
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _occupationController,
                decoration: const InputDecoration(
                  labelText: 'Occupation',
                  hintText: 'e.g. Farmer, Student, Artisan, Self-employed',
                  prefixIcon: Icon(Icons.work_outline),
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                initialValue: _selectedEducation,
                decoration: const InputDecoration(
                  labelText: 'Education Level',
                  prefixIcon: Icon(Icons.school_outlined),
                  border: OutlineInputBorder(),
                ),
                hint: const Text('Select education level'),
                items: _educationLevels.map((lvl) {
                  return DropdownMenuItem(value: lvl, child: Text(lvl));
                }).toList(),
                onChanged: (val) {
                  setState(() => _selectedEducation = val);
                },
              ),
              const SizedBox(height: 20),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.green.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.green.shade200),
                ),
                child: Row(
                  children: [
                    Icon(Icons.lock_outline,
                        color: Colors.green.shade800, size: 20),
                    const SizedBox(width: 10),
                    const Expanded(
                      child: Text(
                        'Aadhaar Privacy Notice: Aadhaar number is NOT collected or stored in JanMitra Assist.',
                        style: TextStyle(fontSize: 12, color: Colors.black87),
                      ),
                    ),
                  ],
                ),
              ),
              if (_errorMessage != null) ...[
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    borderRadius: BorderRadius.circular(8),
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
                  backgroundColor: AppTheme.primaryBlue,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
                child: _isLoading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                            strokeWidth: 2, color: Colors.white),
                      )
                    : Text(
                        widget.isInitialSetup
                            ? 'Complete Setup & Enter'
                            : 'Save Changes',
                        style: const TextStyle(
                            fontSize: 16, fontWeight: FontWeight.bold),
                      ),
              ),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }
}
