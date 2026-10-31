import 'dart:convert';
import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import 'package:janmitra_assist/features/subscription/models/subscription_models.dart';
import 'package:janmitra_assist/features/subscription/services/subscription_service.dart';
import 'payment_success_screen.dart';
import 'payment_failure_screen.dart';
import 'payment_history_screen.dart';

class SubscriptionPlansScreen extends StatefulWidget {
  final CitizenSubscriptionModel? initialSubscription;
  final SubscriptionPlansResponseModel? initialPlans;

  const SubscriptionPlansScreen({
    super.key,
    this.initialSubscription,
    this.initialPlans,
  });

  @override
  State<SubscriptionPlansScreen> createState() =>
      _SubscriptionPlansScreenState();
}

class _SubscriptionPlansScreenState extends State<SubscriptionPlansScreen> {
  final SubscriptionService _service = SubscriptionService();

  CitizenSubscriptionModel? _subscription;
  SubscriptionPlansResponseModel? _plansResponse;
  bool _isLoading = false;
  bool _isProcessingPayment = false;
  String? _errorMessage;
  String _selectedCycle = 'monthly'; // 'monthly' or 'yearly'

  @override
  void initState() {
    super.initState();
    if (widget.initialSubscription != null && widget.initialPlans != null) {
      _subscription = widget.initialSubscription;
      _plansResponse = widget.initialPlans;
    } else {
      _loadData();
    }
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final sub = await _service.getMySubscription();
      final plans = await _service.getPlans();

      if (mounted) {
        setState(() {
          _subscription = sub;
          _plansResponse = plans;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString().replaceFirst('Exception: ', '');
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _handleUpgrade() async {
    setState(() {
      _isProcessingPayment = true;
    });

    try {
      // 1. Create secure order on backend
      final order = await _service.createOrder(billingCycle: _selectedCycle);

      if (!mounted) return;

      // 2. Open payment method dialog (UPI, QR, Cards)
      final method = await _showPaymentMethodSheet(order);
      if (method == null) {
        setState(() {
          _isProcessingPayment = false;
        });
        return;
      }

      // 3. Process payment confirmation
      // Generates simulated Razorpay payment signature in dev mode
      final paymentId = 'pay_${DateTime.now().millisecondsSinceEpoch}';
      final devSecret = 'janmitra_razorpay_secret_dev_32char';
      final payloadBytes = utf8.encode('${order.orderId}|$paymentId');
      final signature = Hmac(sha256, utf8.encode(devSecret))
          .convert(payloadBytes)
          .toString();

      final verifyRes = await _service.verifyPayment(
        orderId: order.orderId,
        paymentId: paymentId,
        signature: signature,
        paymentMethod: method,
      );

      if (!mounted) return;
      setState(() {
        _isProcessingPayment = false;
        _subscription = verifyRes.subscription;
      });

      // Navigate to success receipt screen
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) =>
              PaymentSuccessScreen(verificationResult: verifyRes),
        ),
      );

      _loadData();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isProcessingPayment = false;
      });
      Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => PaymentFailureScreen(
            errorMessage: e.toString().replaceFirst('Exception: ', ''),
          ),
        ),
      );
    }
  }

  Future<String?> _showPaymentMethodSheet(RazorpayOrderModel order) {
    return showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Row(
                  children: [
                    Icon(Icons.payment, color: AppTheme.primaryBlue),
                    SizedBox(width: 8),
                    Text(
                      'Razorpay Secure Checkout',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                Text(
                  '₹${order.amountInr.toStringAsFixed(2)}',
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: AppTheme.accentGreen,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Order: ${order.orderId}',
              style: TextStyle(
                fontSize: 11,
                fontFamily: 'monospace',
                color: Colors.grey.shade600,
              ),
            ),
            const Divider(height: 24),
            const Text(
              'Select Payment Instrument:',
              style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 10),
            ListTile(
              leading: const CircleAvatar(
                backgroundColor: Colors.blue,
                child: Icon(Icons.qr_code, color: Colors.white, size: 20),
              ),
              title: const Text('UPI QR / Intent'),
              subtitle: const Text('Google Pay, PhonePe, Paytm, BHIM'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.of(ctx).pop('upi_qr'),
            ),
            ListTile(
              leading: CircleAvatar(
                backgroundColor: Colors.teal.shade700,
                child: const Icon(Icons.credit_card, color: Colors.white, size: 20),
              ),
              title: const Text('Debit / Credit Cards'),
              subtitle: const Text('Visa, MasterCard, RuPay'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.of(ctx).pop('card'),
            ),
            ListTile(
              leading: CircleAvatar(
                backgroundColor: Colors.deepPurple.shade700,
                child: const Icon(Icons.account_balance,
                    color: Colors.white, size: 20),
              ),
              title: const Text('Net Banking'),
              subtitle: const Text('All Major Indian Banks'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.of(ctx).pop('netbanking'),
            ),
            const SizedBox(height: 12),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Subscription & Quota'),
        actions: [
          IconButton(
            icon: const Icon(Icons.receipt_long_outlined),
            tooltip: 'Payment History',
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => const PaymentHistoryScreen(),
                ),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
            onPressed: _isLoading ? null : () => _loadData(),
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Loading subscription status and plans...'),
          ],
        ),
      );
    }

    if (_errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline, size: 50, color: Colors.red.shade600),
              const SizedBox(height: 12),
              Text(
                _errorMessage!,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 14),
              ),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: () => _loadData(),
                icon: const Icon(Icons.refresh),
                label: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }

    final sub = _subscription;
    final isPremium = sub?.isPremium ?? false;

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Current Status & Quota Card
          if (sub != null) _buildCurrentStatusCard(sub),
          const SizedBox(height: 16),

          // Billing Cycle Switcher
          _buildBillingCycleSwitcher(),
          const SizedBox(height: 16),

          // Comparison Section
          const Text(
            'Select a Plan',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.bold,
              color: AppTheme.primaryDark,
            ),
          ),
          const SizedBox(height: 8),

          // Plan Cards
          if (_plansResponse != null)
            ..._plansResponse!.plans.map(
              (plan) => _buildPlanCard(plan, isCurrent: (plan.planType == (isPremium ? 'premium' : 'free'))),
            ),

          const SizedBox(height: 16),

          // Statutory Disclaimers Card
          _buildDisclaimerCard(),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _buildCurrentStatusCard(CitizenSubscriptionModel sub) {
    final isPrem = sub.isPremium;
    final color = isPrem ? AppTheme.accentGreen : AppTheme.primaryBlue;

    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: color.withAlpha(60)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Icon(
                      isPrem ? Icons.star_rounded : Icons.person_outline,
                      color: color,
                      size: 26,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      isPrem ? 'JanMitra Premium' : 'JanMitra Free Tier',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: color,
                      ),
                    ),
                  ],
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: color.withAlpha(20),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    sub.status.toUpperCase(),
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.bold,
                      color: color,
                    ),
                  ),
                ),
              ],
            ),
            if (isPrem && sub.endDate != null) ...[
              const SizedBox(height: 4),
              Text(
                'Expires on ${sub.endDate!.day}/${sub.endDate!.month}/${sub.endDate!.year} (${sub.daysRemaining ?? 0} days left)',
                style: TextStyle(fontSize: 12, color: Colors.grey.shade700),
              ),
            ],
            const Divider(height: 20),
            const Text(
              'Monthly Usage Quota',
              style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            _buildQuotaBar(
              label: 'AI Document Analyses',
              used: sub.usage.aiDocumentAnalysesUsed,
              limit: sub.usage.aiDocumentAnalysesLimit,
            ),
            const SizedBox(height: 8),
            _buildQuotaBar(
              label: 'Personalized AI Guidance Sessions',
              used: sub.usage.aiGuidanceSessionsUsed,
              limit: sub.usage.aiGuidanceSessionsLimit,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQuotaBar({
    required String label,
    required int used,
    required int limit,
  }) {
    final ratio = (limit > 0) ? (used / limit).clamp(0.0, 1.0) : 0.0;
    final isNearLimit = ratio >= 0.8;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: const TextStyle(fontSize: 12)),
            Text(
              '$used of $limit used',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.bold,
                color: isNearLimit ? Colors.red.shade700 : Colors.black87,
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        ClipRRect(
          borderRadius: BorderRadius.circular(3),
          child: LinearProgressIndicator(
            value: ratio,
            backgroundColor: Colors.grey.shade200,
            color: isNearLimit ? Colors.orange.shade800 : AppTheme.primaryBlue,
            minHeight: 6,
          ),
        ),
      ],
    );
  }

  Widget _buildBillingCycleSwitcher() {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: Colors.grey.shade200,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          Expanded(
            child: _buildCycleTab(
              id: 'monthly',
              title: 'Monthly (₹99)',
              subtitle: 'Billed monthly',
            ),
          ),
          Expanded(
            child: _buildCycleTab(
              id: 'yearly',
              title: 'Yearly (₹799)',
              subtitle: 'Save ~33%',
              badge: 'Best Value',
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCycleTab({
    required String id,
    required String title,
    required String subtitle,
    String? badge,
  }) {
    final isSelected = _selectedCycle == id;
    return GestureDetector(
      onTap: () {
        setState(() {
          _selectedCycle = id;
        });
      },
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 8),
        decoration: BoxDecoration(
          color: isSelected ? Colors.white : Colors.transparent,
          borderRadius: BorderRadius.circular(8),
          boxShadow: isSelected
              ? [
                  BoxShadow(
                    color: Colors.black.withAlpha(15),
                    blurRadius: 4,
                    offset: const Offset(0, 2),
                  )
                ]
              : null,
        ),
        child: Column(
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight:
                        isSelected ? FontWeight.bold : FontWeight.w600,
                    color: isSelected ? AppTheme.primaryBlue : Colors.grey.shade700,
                  ),
                ),
                if (badge != null) ...[
                  const SizedBox(width: 4),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                    decoration: BoxDecoration(
                      color: Colors.green.shade600,
                      borderRadius: BorderRadius.circular(3),
                    ),
                    child: Text(
                      badge,
                      style: const TextStyle(
                        fontSize: 8,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                  ),
                ],
              ],
            ),
            Text(
              subtitle,
              style: TextStyle(
                fontSize: 10,
                color: isSelected ? AppTheme.accentGreen : Colors.grey.shade600,
                fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPlanCard(SubscriptionPlanModel plan, {required bool isCurrent}) {
    final isPremium = plan.planType == 'premium';
    final price = _selectedCycle == 'yearly' ? plan.priceYearly : plan.priceMonthly;
    final priceLabel =
        price == 0 ? 'Free' : '₹${price.toStringAsFixed(0)} / ${_selectedCycle == 'yearly' ? 'year' : 'month'}';

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      elevation: isPremium ? 3 : 1,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: isPremium
              ? AppTheme.primaryBlue.withAlpha(120)
              : Colors.grey.shade300,
          width: isPremium ? 1.5 : 1.0,
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
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      plan.name,
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.primaryDark,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      priceLabel,
                      style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                        color: isPremium ? AppTheme.primaryBlue : Colors.black87,
                      ),
                    ),
                  ],
                ),
                if (isCurrent)
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: Colors.blue.shade50,
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(color: Colors.blue.shade300),
                    ),
                    child: Text(
                      'CURRENT PLAN',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                        color: Colors.blue.shade800,
                      ),
                    ),
                  )
                else if (isPremium)
                  ElevatedButton(
                    onPressed: _isProcessingPayment ? null : _handleUpgrade,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.accentGreen,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 8),
                    ),
                    child: _isProcessingPayment
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          )
                        : const Text(
                            'Upgrade Now',
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                  ),
              ],
            ),
            const SizedBox(height: 6),
            Text(
              plan.description,
              style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
            ),
            const Divider(height: 20),
            ...plan.features.map(
              (f) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 3),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      Icons.check_circle_outline,
                      size: 16,
                      color: isPremium ? AppTheme.accentGreen : Colors.grey,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        f,
                        style: const TextStyle(fontSize: 12, height: 1.3),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDisclaimerCard() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.amber.shade50,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.amber.shade300),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.shield_outlined, color: Colors.amber.shade900, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Statutory Subscription Notice',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 12,
                    color: Colors.amber.shade900,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'JanMitra Assist fees cover platform intelligence, document OCR, and preparation checklists. '
                  'JanMitra Assist is an application preparation assistant and does NOT submit government forms on your behalf.',
                  style: TextStyle(
                    fontSize: 11,
                    color: Colors.brown.shade800,
                    height: 1.3,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
