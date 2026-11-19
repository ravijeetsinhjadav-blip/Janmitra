import 'package:flutter/material.dart';
import '../../../../core/constants/app_constants.dart';
import '../../../../core/network/auth_service.dart';
import '../../../../core/services/secure_storage_service.dart';
import '../../../../core/theme/app_theme.dart';
import '../../../auth/presentation/screens/login_screen.dart';
import '../../../profile/models/user_profile_model.dart';
import '../../../profile/presentation/screens/profile_setup_screen.dart';
import '../../../profile/presentation/screens/profile_view_screen.dart';
import '../../../schemes/presentation/assessment_history_screen.dart';
import '../../../schemes/presentation/recommended_schemes_screen.dart';
import '../../../schemes/presentation/scheme_discovery_screen.dart';
import '../../../documents/presentation/screens/document_vault_screen.dart';
import '../../../subscription/presentation/screens/subscription_plans_screen.dart';
import '../../../applications/presentation/screens/applications_list_screen.dart';
import '../../../notifications/presentation/screens/notification_history_screen.dart';
import '../widgets/welcome_card.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final AuthService _authService = AuthService();
  final SecureStorageService _storage = SecureStorageService();

  String? _mobileNumber;
  String _role = 'Citizen';
  UserProfileModel? _profile;
  int _currentNavIndex = 0;

  @override
  void initState() {
    super.initState();
    _loadCitizenData();
  }

  Future<void> _loadCitizenData() async {
    final mobile = await _storage.getMobileNumber();
    final role = await _storage.getUserRole();
    try {
      final profile = await _authService.getUserProfile();
      if (mounted) {
        setState(() {
          _mobileNumber = mobile;
          _role = (role ?? 'citizen').toUpperCase();
          _profile = profile;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _mobileNumber = mobile;
          _role = (role ?? 'citizen').toUpperCase();
        });
      }
    }
  }

  Future<void> _handleSignOut() async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('Sign Out',
            style: TextStyle(fontWeight: FontWeight.bold)),
        content:
            const Text('Are you sure you want to sign out of JanMitra Assist?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            style:
                ElevatedButton.styleFrom(backgroundColor: AppTheme.primaryNavy),
            child: const Text('Sign Out'),
          ),
        ],
      ),
    );

    if (confirm == true) {
      await _authService.logout();
      if (!mounted) return;
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const LoginScreen()),
        (route) => false,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.surfaceBg,
      appBar: _buildAppBar(),
      body: RefreshIndicator(
        onRefresh: _loadCitizenData,
        color: AppTheme.primaryBlue,
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // 1. Prestigious Digital India Civic Welcome Banner
              const WelcomeCard(),
              const SizedBox(height: 14),

              // 2. Citizen Identity & Profile Hero Card
              _buildCitizenHeroCard(),
              const SizedBox(height: 18),

              // 3. Quick Action Services Grid (6 Core Civic Pillars)
              _buildQuickServicesSection(),
              const SizedBox(height: 18),

              // 4. Featured Government Schemes Showcase
              _buildFeaturedSchemesSection(),
              const SizedBox(height: 18),

              // 5. AI Scheme Advisory Banner
              _buildAIAdvisoryHeroBanner(),
              const SizedBox(height: 18),

              // 6. Comprehensive Platform Modules & Activity
              _buildPlatformModulesOverview(),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
      bottomNavigationBar: _buildBottomNav(),
    );
  }

  PreferredSizeWidget _buildAppBar() {
    return AppBar(
      backgroundColor: AppTheme.primaryNavy,
      elevation: 0,
      title: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: Colors.white.withAlpha(30),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.shield, color: AppTheme.saffronAccent, size: 20),
          ),
          const SizedBox(width: 10),
          const Text(
            AppConstants.appName,
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w800,
              color: Colors.white,
              letterSpacing: 0.2,
            ),
          ),
        ],
      ),
      actions: [
        IconButton(
          key: const Key('home_notifications_bell_button'),
          icon: const Icon(Icons.notifications_none_rounded, color: Colors.white),
          tooltip: 'Notifications',
          onPressed: () async {
            await Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => const NotificationHistoryScreen(),
              ),
            );
          },
        ),
        IconButton(
          icon: const Icon(Icons.account_circle_outlined, color: Colors.white),
          tooltip: 'Citizen Profile',
          onPressed: () async {
            await Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const ProfileViewScreen()),
            );
            _loadCitizenData();
          },
        ),
        IconButton(
          icon: const Icon(Icons.logout_rounded, color: Colors.white),
          tooltip: 'Sign Out',
          onPressed: _handleSignOut,
        ),
      ],
    );
  }

  Widget _buildCitizenHeroCard() {
    final citizenName = _profile?.fullName.isNotEmpty == true
        ? _profile!.fullName
        : 'Citizen User';
    final hasProfile = _profile != null;

    return Container(
      decoration: BoxDecoration(
        gradient: AppTheme.heroGradient,
        borderRadius: BorderRadius.circular(16),
        boxShadow: const [
          BoxShadow(
            color: Color(0x250F2B5C),
            blurRadius: 14,
            offset: Offset(0, 4),
          ),
        ],
      ),
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: Colors.white.withAlpha(40),
                  border: Border.all(color: Colors.white.withAlpha(80), width: 1.5),
                ),
                child: const Icon(Icons.person, color: Colors.white, size: 28),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      citizenName,
                      style: const TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w800,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      _mobileNumber != null
                          ? (_mobileNumber!.startsWith('+')
                              ? _mobileNumber!
                              : '+91 $_mobileNumber')
                          : 'Aadhaar Mobile Linked',
                      style: TextStyle(
                        fontSize: 12.5,
                        color: Colors.white.withAlpha(200),
                        fontWeight: FontWeight.w400,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(
                  color: Colors.white.withAlpha(35),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: Colors.white.withAlpha(70)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.verified, size: 14, color: Color(0xFF86EFAC)),
                    const SizedBox(width: 4),
                    Text(
                      _role,
                      style: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: Colors.black.withAlpha(40),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Icon(
                      hasProfile ? Icons.check_circle : Icons.warning_amber_rounded,
                      size: 17,
                      color: hasProfile ? const Color(0xFF86EFAC) : const Color(0xFFFDE047),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      hasProfile ? 'Profile Completed' : 'Profile Incomplete',
                      style: TextStyle(
                        fontSize: 12.5,
                        fontWeight: FontWeight.w600,
                        color: hasProfile ? const Color(0xFF86EFAC) : const Color(0xFFFDE047),
                      ),
                    ),
                  ],
                ),
                InkWell(
                  onTap: () async {
                    if (hasProfile) {
                      await Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => const ProfileViewScreen()),
                      );
                    } else {
                      await Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => const ProfileSetupScreen()),
                      );
                    }
                    _loadCitizenData();
                  },
                  borderRadius: BorderRadius.circular(8),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    child: Text(
                      hasProfile ? 'View Profile' : 'Complete Now',
                      style: const TextStyle(
                        fontSize: 12.5,
                        fontWeight: FontWeight.w700,
                        color: Colors.white,
                        decoration: TextDecoration.underline,
                        decorationColor: Colors.white,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildQuickServicesSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Citizen Services Hub',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w800,
                color: AppTheme.primaryNavy,
              ),
            ),
            Text(
              '6 Active Services',
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: AppTheme.primaryBlue,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        GridView.count(
          crossAxisCount: 3,
          crossAxisSpacing: 10,
          mainAxisSpacing: 10,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          childAspectRatio: 0.85,
          children: [
            _buildQuickActionCard(
              icon: Icons.account_balance,
              iconColor: const Color(0xFF1E5BB0),
              bgColor: const Color(0xFFEFF6FF),
              title: 'Schemes',
              subtitle: '7+ Official',
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const SchemeDiscoveryScreen()),
              ),
            ),
            _buildQuickActionCard(
              icon: Icons.auto_awesome,
              iconColor: const Color(0xFFD97706),
              bgColor: const Color(0xFFFFFBEB),
              title: 'AI Matches',
              subtitle: 'Eligibility',
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const RecommendedSchemesScreen()),
              ),
            ),
            _buildQuickActionCard(
              icon: Icons.folder_shared,
              iconColor: const Color(0xFF059669),
              bgColor: const Color(0xFFECFDF5),
              title: 'Doc Vault',
              subtitle: 'OCR Verify',
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const DocumentVaultScreen()),
              ),
            ),
            _buildQuickActionCard(
              icon: Icons.fact_check_outlined,
              iconColor: const Color(0xFF0D9488),
              bgColor: const Color(0xFFF0FDFA),
              title: 'Checklists',
              subtitle: 'Form Guide',
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const SchemeDiscoveryScreen()),
              ),
            ),
            _buildQuickActionCard(
              icon: Icons.assignment_turned_in_outlined,
              iconColor: const Color(0xFF7C3AED),
              bgColor: const Color(0xFFFAF5FF),
              title: 'Tracking',
              subtitle: 'Live Status',
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const ApplicationsListScreen()),
              ),
            ),
            _buildQuickActionCard(
              icon: Icons.workspace_premium,
              iconColor: const Color(0xFFB45309),
              bgColor: const Color(0xFFFEF3C7),
              title: 'Premium',
              subtitle: '₹99/month',
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const SubscriptionPlansScreen()),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildQuickActionCard({
    required IconData icon,
    required Color iconColor,
    required Color bgColor,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
  }) {
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      elevation: 0,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: AppTheme.borderColor),
            boxShadow: AppTheme.cardShadow,
          ),
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 12),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: bgColor,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, color: iconColor, size: 24),
              ),
              const SizedBox(height: 8),
              Text(
                title,
                textAlign: TextAlign.center,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 12.5,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.primaryDark,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                subtitle,
                textAlign: TextAlign.center,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 10.5,
                  fontWeight: FontWeight.w500,
                  color: AppTheme.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildFeaturedSchemesSection() {
    final schemes = [
      {
        'title': 'PM-KISAN Samman Nidhi',
        'benefit': '₹6,000 / year DBT Benefit',
        'dept': 'Ministry of Agriculture',
        'tag': 'Direct Benefit',
        'color': const Color(0xFF059669),
      },
      {
        'title': 'Ayushman Bharat (PM-JAY)',
        'benefit': '₹5 Lakh Free Hospital Cover',
        'dept': 'Ministry of Health',
        'tag': 'Health Insurance',
        'color': const Color(0xFF1E5BB0),
      },
      {
        'title': 'PMAY - Gramin Housing',
        'benefit': '₹1.20 Lakh Housing Subsidy',
        'dept': 'Ministry of Rural Dev.',
        'tag': 'Housing',
        'color': const Color(0xFFD97706),
      },
      {
        'title': 'PM Ujjwala Yojana (PMUY)',
        'benefit': 'Free LPG Connection & Subsidy',
        'dept': 'Ministry of Petroleum',
        'tag': 'Welfare',
        'color': const Color(0xFF7C3AED),
      },
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              'Featured Central Schemes',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w800,
                color: AppTheme.primaryNavy,
              ),
            ),
            TextButton(
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const SchemeDiscoveryScreen()),
              ),
              child: const Text('View All (7)'),
            ),
          ],
        ),
        const SizedBox(height: 6),
        SizedBox(
          height: 142,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: schemes.length,
            separatorBuilder: (_, __) => const SizedBox(width: 12),
            itemBuilder: (ctx, i) {
              final s = schemes[i];
              final themeColor = s['color'] as Color;
              return Container(
                width: 250,
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: AppTheme.borderColor),
                  boxShadow: AppTheme.cardShadow,
                ),
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: themeColor.withAlpha(25),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            s['tag'] as String,
                            style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                              color: themeColor,
                            ),
                          ),
                        ),
                        const Icon(Icons.verified, size: 16, color: Color(0xFF16A34A)),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      s['title'] as String,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w800,
                        color: AppTheme.primaryDark,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      s['benefit'] as String,
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: Color(0xFF059669),
                      ),
                    ),
                    const Spacer(),
                    Text(
                      s['dept'] as String,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 10.5,
                        color: AppTheme.textSecondary,
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _buildAIAdvisoryHeroBanner() {
    return Container(
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF4C1D95), Color(0xFF7C3AED)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: const [
          BoxShadow(
            color: Color(0x207C3AED),
            blurRadius: 12,
            offset: Offset(0, 4),
          ),
        ],
      ),
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.white.withAlpha(35),
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.psychology, color: Colors.white, size: 24),
              ),
              const SizedBox(width: 12),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'AI Scheme Advisory & Readiness',
                      style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w800,
                        color: Colors.white,
                      ),
                    ),
                    SizedBox(height: 2),
                    Text(
                      'Multilingual guidance in Hindi, Gujarati & English',
                      style: TextStyle(
                        fontSize: 11.5,
                        color: Color(0xFFE9D5FF),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          const Text(
            'Instant calculation of missing documents, rule eligibility match, and step-by-step guidance for official submissions.',
            style: TextStyle(
              fontSize: 12,
              color: Colors.white70,
              height: 1.35,
            ),
          ),
          const SizedBox(height: 14),
          ElevatedButton.icon(
            icon: const Icon(Icons.auto_awesome, size: 16),
            label: const Text('Get AI Scheme Advisory'),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.white,
              foregroundColor: const Color(0xFF4C1D95),
              elevation: 0,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 11),
            ),
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const RecommendedSchemesScreen()),
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildPlatformModulesOverview() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Platform Governance & Modules',
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w800,
            color: AppTheme.primaryNavy,
          ),
        ),
        const SizedBox(height: 10),

        // Module Card 1: Scheme Engine & Search
        _buildModuleCard(
          icon: Icons.account_balance,
          iconColor: AppTheme.primaryBlue,
          title: 'Explore Welfare Schemes',
          description:
              'Search central & state schemes, assess likely eligibility, and access official application portals.',
          primaryBtnLabel: 'Browse All Schemes',
          onPrimaryTap: () => Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => const SchemeDiscoveryScreen()),
          ),
          secondaryBtnLabel: 'My Matches',
          onSecondaryTap: () => Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => const RecommendedSchemesScreen()),
          ),
          tertiaryBtnLabel: 'Assessments',
          onTertiaryTap: () => Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => const AssessmentHistoryScreen()),
          ),
        ),
        const SizedBox(height: 12),

        // Module Card 2: Document Vault & OCR
        _buildModuleCard(
          icon: Icons.folder_shared,
          iconColor: AppTheme.accentGreen,
          title: 'Citizen Document Vault & OCR',
          description:
              'Securely store certificates and identity documents with Google Cloud Vision OCR intelligence.',
          primaryBtnLabel: 'Open Document Vault',
          onPrimaryTap: () => Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => const DocumentVaultScreen()),
          ),
        ),
        const SizedBox(height: 12),

        // Module Card 3: Preparation & Checklists
        _buildModuleCard(
          icon: Icons.fact_check_outlined,
          iconColor: const Color(0xFF0D9488),
          title: 'Application Preparation & Checklists',
          description:
              'Interactive step-by-step preparation checklists, common mistakes warnings, document specifications, and official portal directions.',
          primaryBtnLabel: 'Prepare for Schemes',
          onPrimaryTap: () => Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => const SchemeDiscoveryScreen()),
          ),
        ),
        const SizedBox(height: 12),

        // Module Card 4: Applications Tracker
        _buildModuleCard(
          icon: Icons.assignment_turned_in_outlined,
          iconColor: const Color(0xFF7C3AED),
          title: 'Application Tracking & Status History',
          description:
              'Log formal portal filings, update citizen-reported progress, maintain audit history, and track deadlines.',
          primaryBtnLabel: 'Track Government Applications',
          onPrimaryTap: () => Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => const ApplicationsListScreen()),
          ),
        ),
        const SizedBox(height: 12),

        // Module Card 5: Subscription Plans
        _buildModuleCard(
          icon: Icons.workspace_premium,
          iconColor: const Color(0xFFD97706),
          title: 'Assisted Service & Subscription Plans',
          description:
              'Explore Free vs Premium (₹99/mo or ₹799/yr), quota usage, and secure Razorpay payment checkout.',
          primaryBtnLabel: 'View Plans & Quota',
          onPrimaryTap: () => Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => const SubscriptionPlansScreen()),
          ),
        ),
      ],
    );
  }

  Widget _buildModuleCard({
    required IconData icon,
    required Color iconColor,
    required String title,
    required String description,
    required String primaryBtnLabel,
    required VoidCallback onPrimaryTap,
    String? secondaryBtnLabel,
    VoidCallback? onSecondaryTap,
    String? tertiaryBtnLabel,
    VoidCallback? onTertiaryTap,
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
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: iconColor.withAlpha(25),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(icon, color: iconColor, size: 24),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            title,
                            style: const TextStyle(
                              fontSize: 14.5,
                              fontWeight: FontWeight.w700,
                              color: AppTheme.primaryDark,
                            ),
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 7, vertical: 2),
                          decoration: BoxDecoration(
                            color: const Color(0xFFECFDF5),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(color: const Color(0xFF86EFAC)),
                          ),
                          child: const Text(
                            'Active',
                            style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                              color: Color(0xFF059669),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 3),
                    Text(
                      description,
                      style: const TextStyle(
                        fontSize: 11.5,
                        color: AppTheme.textSecondary,
                        height: 1.3,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: ElevatedButton(
                  onPressed: onPrimaryTap,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: iconColor,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 11),
                  ),
                  child: Text(primaryBtnLabel,
                      style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
                ),
              ),
            ],
          ),
          if (secondaryBtnLabel != null && onSecondaryTap != null) ...[
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    icon: const Icon(Icons.auto_awesome, size: 15, color: Colors.amber),
                    label: Text(secondaryBtnLabel),
                    onPressed: onSecondaryTap,
                  ),
                ),
                if (tertiaryBtnLabel != null && onTertiaryTap != null) ...[
                  const SizedBox(width: 8),
                  Expanded(
                    child: OutlinedButton.icon(
                      icon: const Icon(Icons.history, size: 15, color: AppTheme.primaryBlue),
                      label: Text(tertiaryBtnLabel),
                      onPressed: onTertiaryTap,
                    ),
                  ),
                ],
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildBottomNav() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: AppTheme.borderColor, width: 1)),
        boxShadow: const [
          BoxShadow(
            color: Color(0x0F000000),
            blurRadius: 10,
            offset: Offset(0, -2),
          ),
        ],
      ),
      child: NavigationBar(
        selectedIndex: _currentNavIndex,
        height: 64,
        backgroundColor: Colors.white,
        indicatorColor: AppTheme.primaryBlue.withAlpha(30),
        onDestinationSelected: (index) {
          setState(() {
            _currentNavIndex = index;
          });
          if (index == 1) {
            Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const SchemeDiscoveryScreen()),
            ).then((_) {
              if (mounted) setState(() => _currentNavIndex = 0);
            });
          } else if (index == 2) {
            Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const DocumentVaultScreen()),
            ).then((_) {
              if (mounted) setState(() => _currentNavIndex = 0);
            });
          } else if (index == 3) {
            Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const ApplicationsListScreen()),
            ).then((_) {
              if (mounted) setState(() => _currentNavIndex = 0);
            });
          }
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home, color: AppTheme.primaryBlue),
            label: 'Home',
          ),
          NavigationDestination(
            icon: Icon(Icons.account_balance_outlined),
            selectedIcon: Icon(Icons.account_balance, color: AppTheme.primaryBlue),
            label: 'Schemes',
          ),
          NavigationDestination(
            icon: Icon(Icons.folder_outlined),
            selectedIcon: Icon(Icons.folder_shared, color: AppTheme.primaryBlue),
            label: 'Vault',
          ),
          NavigationDestination(
            icon: Icon(Icons.assignment_turned_in_outlined),
            selectedIcon: Icon(Icons.assignment_turned_in, color: AppTheme.primaryBlue),
            label: 'Tracking',
          ),
        ],
      ),
    );
  }
}
