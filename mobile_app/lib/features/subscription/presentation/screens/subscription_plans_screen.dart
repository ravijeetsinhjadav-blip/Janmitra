import 'package:flutter/material.dart';
import 'package:razorpay_flutter/razorpay_flutter.dart';
import '../../../../core/theme/app_theme.dart';
import 'package:janmitra_assist/features/subscription/models/subscription_models.dart';
import 'package:janmitra_assist/features/subscription/services/subscription_service.dart';
import 'package:janmitra_assist/features/subscription/services/razorpay_checkout_adapter.dart';
import 'payment_success_screen.dart';
import 'payment_failure_screen.dart';
import 'payment_history_screen.dart';

class SubscriptionPlansScreen extends StatefulWidget {
  final CitizenSubscriptionModel? initialSubscription;
  final SubscriptionPlansResponseModel? initialPlans;
  final RazorpayCheckoutAdapter? checkoutAdapter;

  const SubscriptionPlansScreen({
    super.key,
    this.initialSubscription,
    this.initialPlans,
    this.checkoutAdapter,
  });

  @override
  State<SubscriptionPlansScreen> createState() =>
      _SubscriptionPlansScreenState();
}

class _SubscriptionPlansScreenState extends State<SubscriptionPlansScreen> {
  final SubscriptionService _service = SubscriptionService();
  late final RazorpayCheckoutAdapter _checkoutAdapter;

  CitizenSubscriptionModel? _subscription;
  SubscriptionPlansResponseModel? _plansResponse;
  bool _isLoading = false;
  bool _isProcessingPayment = false;
  String? _errorMessage;
  String _selectedCycle = 'monthly'; // 'monthly' or 'yearly'
  String? _pendingOrderId;

  @override
  void initState() {
    super.initState();
    _checkoutAdapter = widget.checkoutAdapter ?? LiveRazorpayAdapter();
    _checkoutAdapter.init(
      onSuccess: _handlePaymentSuccess,
      onError: _handlePaymentError,
      onExternalWallet: _handleExternalWallet,
    );

    if (widget.initialSubscription != null && widget.initialPlans != null) {
      _subscription = widget.initialSubscription;
      _plansResponse = widget.initialPlans;
    } else {
      _loadData();
    }
  }

  @override
  void dispose() {
    _checkoutAdapter.dispose();
    super.dispose();
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
      // 1. Create secure server-side order on backend (SEC-01)
      final order = await _service.createOrder(billingCycle: _selectedCycle);

      if (!mounted) return;

      // 2. Open official Razorpay Checkout SDK via decoupled adapter (SEC-02)
      _pendingOrderId = order.orderId;
      final options = {
        'key': order.keyId,
        'amount': order.amount, // in paise
        'name': 'JanMitra Assist',
        'description':
            'JanMitra Premium (${_selectedCycle == 'yearly' ? 'Annual' : 'Monthly'}) Subscription',
        'order_id': order.orderId,
        'currency': order.currency,
        'timeout': 180,
        'prefill': {
          'contact': '',
          'email': '',
        },
        'theme': {
          'color': '#0F766E',
        },
      };

      if (order.isDevMode || order.keyId == 'rzp_test_janmitra_dev_key') {
        _showDevModePaymentDialog(order);
      } else {
        _checkoutAdapter.open(options);
      }
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

  void _showDevModePaymentDialog(RazorpayOrderModel order) {
    String selectedMethod = 'UPI';
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setModalState) => Container(
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: AppTheme.accentGreen.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.shield_outlined,
                        color: AppTheme.accentGreen, size: 24),
                  ),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Razorpay Payment Gateway',
                          style: TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: Colors.black87,
                          ),
                        ),
                        Text(
                          'Secure 256-bit Encrypted Checkout',
                          style: TextStyle(fontSize: 12, color: Colors.black54),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, color: Colors.grey),
                    onPressed: () {
                      Navigator.of(ctx).pop();
                      if (mounted) setState(() => _isProcessingPayment = false);
                    },
                  ),
                ],
              ),
              const Divider(height: 24),
              // Plan Summary Card
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.grey.shade50,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.grey.shade300),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'JanMitra Premium (${_selectedCycle == 'yearly' ? 'Annual Plan' : 'Monthly Plan'})',
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 14,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'Order ID: ${order.orderId}',
                          style: const TextStyle(
                              fontSize: 11, color: Colors.black54),
                        ),
                      ],
                    ),
                    Text(
                      '₹${order.amountInr.toStringAsFixed(0)}',
                      style: const TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.accentGreen,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              const Text(
                'Select Payment Method',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: Colors.black87,
                ),
              ),
              const SizedBox(height: 10),
              // Payment method options
              _buildPaymentOption(
                icon: Icons.qr_code_2,
                title: 'UPI (GPay / PhonePe / Paytm / BHIM)',
                subtitle: 'Fastest payment directly from bank account',
                value: 'UPI',
                selected: selectedMethod,
                onTap: () => setModalState(() => selectedMethod = 'UPI'),
              ),
              const SizedBox(height: 8),
              _buildPaymentOption(
                icon: Icons.credit_card,
                title: 'Credit / Debit Card',
                subtitle: 'Visa, MasterCard, RuPay, Maestro',
                value: 'Card',
                selected: selectedMethod,
                onTap: () => setModalState(() => selectedMethod = 'Card'),
              ),
              const SizedBox(height: 8),
              _buildPaymentOption(
                icon: Icons.account_balance,
                title: 'Net Banking',
                subtitle: 'SBI, HDFC, ICICI, Bank of Baroda & 50+ banks',
                value: 'NetBanking',
                selected: selectedMethod,
                onTap: () => setModalState(() => selectedMethod = 'NetBanking'),
              ),
              const SizedBox(height: 20),
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.accentGreen,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),
                onPressed: () {
                  Navigator.of(ctx).pop();
                  final paymentId =
                      'pay_rzp_${DateTime.now().millisecondsSinceEpoch}';
                  const signature = 'dev_mock_signature';
                  _handlePaymentSuccess(PaymentSuccessResponse(
                    paymentId,
                    order.orderId,
                    signature,
                    {'method': selectedMethod.toLowerCase()},
                  ));
                },
                child: Text(
                  'Pay ₹${order.amountInr.toStringAsFixed(0)} Securely',
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
    ).whenComplete(() {
      if (mounted && _isProcessingPayment) {
        setState(() => _isProcessingPayment = false);
      }
    });
  }

  Widget _buildPaymentOption({
    required IconData icon,
    required String title,
    required String subtitle,
    required String value,
    required String selected,
    required VoidCallback onTap,
  }) {
    final isSelected = selected == value;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: isSelected ? Colors.teal.shade50 : Colors.white,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: isSelected ? AppTheme.accentGreen : Colors.grey.shade300,
            width: isSelected ? 1.5 : 1.0,
          ),
        ),
        child: Row(
          children: [
            Icon(icon,
                color: isSelected ? AppTheme.accentGreen : Colors.grey.shade700,
                size: 24),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontWeight:
                          isSelected ? FontWeight.bold : FontWeight.w500,
                      fontSize: 13,
                      color: Colors.black87,
                    ),
                  ),
                  Text(
                    subtitle,
                    style: const TextStyle(fontSize: 11, color: Colors.black54),
                  ),
                ],
              ),
            ),
            Icon(
              isSelected
                  ? Icons.radio_button_checked
                  : Icons.radio_button_unchecked,
              color: isSelected ? AppTheme.accentGreen : Colors.grey.shade400,
              size: 20,
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _handlePaymentSuccess(PaymentSuccessResponse response) async {
    final paymentId = response.paymentId;
    final orderId = response.orderId ?? _pendingOrderId;
    final signature = response.signature;

    if (paymentId == null || orderId == null || signature == null) {
      if (mounted) {
        setState(() {
          _isProcessingPayment = false;
        });
        Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) => const PaymentFailureScreen(
              errorMessage:
                  'Payment completed but missing signature verification payload from gateway.',
            ),
          ),
        );
      }
      return;
    }

    try {
      // 3. Cryptographically verify signature server-side (SEC-02, SEC-03)
      final verifyRes = await _service.verifyPayment(
        orderId: orderId,
        paymentId: paymentId,
        signature: signature,
      );

      if (!mounted) return;
      setState(() {
        _isProcessingPayment = false;
        _subscription = verifyRes.subscription;
      });

      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => PaymentSuccessScreen(verificationResult: verifyRes),
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

  Future<void> _showCancelSubscriptionDialog() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Cancel Premium Subscription?'),
        content: const Text(
          'Are you sure you want to cancel your JanMitra Premium subscription? '
          'Your account will be reverted to the Free plan (up to 3 document analyses and 5 guidance sessions per month).',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Keep Subscription'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red.shade700,
              foregroundColor: Colors.white,
            ),
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Confirm Cancellation'),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      setState(() => _isLoading = true);
      try {
        final updated = await _service.cancelSubscription();
        if (mounted) {
          setState(() {
            _subscription = updated;
            _isLoading = false;
          });
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text(
                  'Your subscription has been cancelled. Reverted to Free tier.'),
              backgroundColor: Colors.orange,
            ),
          );
        }
      } catch (e) {
        if (mounted) {
          setState(() => _isLoading = false);
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(e.toString().replaceFirst('Exception: ', '')),
              backgroundColor: Colors.red,
            ),
          );
        }
      }
    }
  }

  void _handlePaymentError(PaymentFailureResponse response) {
    if (!mounted) return;
    setState(() {
      _isProcessingPayment = false;
    });
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => PaymentFailureScreen(
          errorMessage: response.message ?? 'Payment failed or was cancelled.',
          orderId: _pendingOrderId,
        ),
      ),
    );
  }

  void _handleExternalWallet(ExternalWalletResponse response) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Selected external wallet: ${response.walletName}'),
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
              (plan) => _buildPlanCard(plan,
                  isCurrent:
                      (plan.planType == (isPremium ? 'premium' : 'free'))),
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
            if (isPrem) ...[
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  ElevatedButton.icon(
                    icon: const Icon(Icons.autorenew_rounded, size: 16),
                    label: const Text(
                      'Renew Subscription',
                      style:
                          TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                    ),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primaryBlue,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(
                          horizontal: 14, vertical: 8),
                    ),
                    onPressed: _isProcessingPayment ? null : _handleUpgrade,
                  ),
                  TextButton.icon(
                    icon: const Icon(Icons.cancel_outlined,
                        size: 16, color: Colors.red),
                    label: const Text(
                      'Cancel Subscription',
                      style: TextStyle(color: Colors.red, fontSize: 12),
                    ),
                    onPressed: _showCancelSubscriptionDialog,
                  ),
                ],
              ),
            ],
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
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: ratio,
            minHeight: 6,
            backgroundColor: Colors.grey.shade200,
            valueColor: AlwaysStoppedAnimation<Color>(
              isNearLimit ? Colors.orange.shade700 : AppTheme.primaryBlue,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildBillingCycleSwitcher() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.grey.shade200,
        borderRadius: BorderRadius.circular(8),
      ),
      padding: const EdgeInsets.all(4),
      child: Row(
        children: [
          Expanded(
            child: GestureDetector(
              onTap: () => setState(() => _selectedCycle = 'monthly'),
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 8),
                decoration: BoxDecoration(
                  color: _selectedCycle == 'monthly'
                      ? Colors.white
                      : Colors.transparent,
                  borderRadius: BorderRadius.circular(6),
                  boxShadow: _selectedCycle == 'monthly'
                      ? [
                          BoxShadow(
                            color: Colors.black.withAlpha(20),
                            blurRadius: 4,
                          )
                        ]
                      : null,
                ),
                child: Center(
                  child: Text(
                    'Monthly (₹99)',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: _selectedCycle == 'monthly'
                          ? FontWeight.bold
                          : FontWeight.normal,
                      color: _selectedCycle == 'monthly'
                          ? AppTheme.primaryDark
                          : Colors.grey.shade700,
                    ),
                  ),
                ),
              ),
            ),
          ),
          Expanded(
            child: GestureDetector(
              onTap: () => setState(() => _selectedCycle = 'yearly'),
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 8),
                decoration: BoxDecoration(
                  color: _selectedCycle == 'yearly'
                      ? Colors.white
                      : Colors.transparent,
                  borderRadius: BorderRadius.circular(6),
                  boxShadow: _selectedCycle == 'yearly'
                      ? [
                          BoxShadow(
                            color: Colors.black.withAlpha(20),
                            blurRadius: 4,
                          )
                        ]
                      : null,
                ),
                child: Center(
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        'Yearly (₹799)',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: _selectedCycle == 'yearly'
                              ? FontWeight.bold
                              : FontWeight.normal,
                          color: _selectedCycle == 'yearly'
                              ? AppTheme.primaryDark
                              : Colors.grey.shade700,
                        ),
                      ),
                      const SizedBox(width: 4),
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 4, vertical: 2),
                        decoration: BoxDecoration(
                          color: AppTheme.accentGreen,
                          borderRadius: BorderRadius.circular(3),
                        ),
                        child: const Text(
                          'Save ~33%',
                          style: TextStyle(
                            fontSize: 9,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPlanCard(SubscriptionPlanModel plan, {required bool isCurrent}) {
    final isPremium = plan.planType == 'premium';
    final priceLabel = isPremium
        ? (_selectedCycle == 'yearly' ? '₹799 / year' : '₹99 / month')
        : 'Free Forever';

    return Card(
      elevation: isPremium ? 3 : 1,
      margin: const EdgeInsets.only(bottom: 14),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(
          color: isPremium ? AppTheme.accentGreen : Colors.grey.shade300,
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
                        color:
                            isPremium ? AppTheme.primaryBlue : Colors.black87,
                      ),
                    ),
                  ],
                ),
                if (isCurrent && isPremium)
                  ElevatedButton(
                    onPressed: _isProcessingPayment ? null : _handleUpgrade,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.accentGreen,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(
                          horizontal: 14, vertical: 8),
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
                            'Renew / Extend',
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                  )
                else if (isCurrent)
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
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
