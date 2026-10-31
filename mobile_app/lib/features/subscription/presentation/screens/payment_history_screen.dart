import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import 'package:janmitra_assist/features/subscription/models/subscription_models.dart';
import 'package:janmitra_assist/features/subscription/services/subscription_service.dart';

class PaymentHistoryScreen extends StatefulWidget {
  final List<PaymentTransactionModel>? initialTransactions;

  const PaymentHistoryScreen({
    super.key,
    this.initialTransactions,
  });

  @override
  State<PaymentHistoryScreen> createState() => _PaymentHistoryScreenState();
}

class _PaymentHistoryScreenState extends State<PaymentHistoryScreen> {
  final SubscriptionService _service = SubscriptionService();
  List<PaymentTransactionModel>? _transactions;
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    if (widget.initialTransactions != null) {
      _transactions = widget.initialTransactions;
    } else {
      _loadHistory();
    }
  }

  Future<void> _loadHistory() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final res = await _service.getPaymentHistory();
      if (mounted) {
        setState(() {
          _transactions = res.items;
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

  Color _getStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'captured':
        return AppTheme.accentGreen;
      case 'created':
        return Colors.orange.shade800;
      case 'failed':
      default:
        return Colors.red.shade700;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Payment History'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
            onPressed: _isLoading ? null : () => _loadHistory(),
          ),
        ],
      ),
      body: _buildBody(),
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
                onPressed: () => _loadHistory(),
                icon: const Icon(Icons.refresh),
                label: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }

    if (_transactions == null || _transactions!.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.receipt_long_outlined, size: 56, color: Colors.grey),
              SizedBox(height: 12),
              Text(
                'No payment transactions yet',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 6),
              Text(
                'When you subscribe to JanMitra Premium, receipts will appear here.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 13, color: Colors.grey),
              ),
            ],
          ),
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      itemCount: _transactions!.length,
      itemBuilder: (context, index) {
        final tx = _transactions![index];
        final color = _getStatusColor(tx.paymentStatus);
        final dateFormatted =
            '${tx.createdAt.day}/${tx.createdAt.month}/${tx.createdAt.year}';

        return Card(
          margin: const EdgeInsets.symmetric(vertical: 6),
          elevation: 1,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
            side: BorderSide(color: Colors.grey.shade300),
          ),
          child: Padding(
            padding: const EdgeInsets.all(14.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      '₹${tx.amount.toStringAsFixed(2)}',
                      style: const TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: AppTheme.primaryDark,
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 3,
                      ),
                      decoration: BoxDecoration(
                        color: color.withAlpha(25),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: color.withAlpha(80)),
                      ),
                      child: Text(
                        tx.paymentStatus.toUpperCase(),
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: color,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Text(
                  'JanMitra ${tx.planType.toUpperCase()} • ${tx.billingCycle.toUpperCase()}',
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'Date: $dateFormatted',
                      style:
                          TextStyle(fontSize: 12, color: Colors.grey.shade600),
                    ),
                    if (tx.paymentMethod != null)
                      Text(
                        'Method: ${tx.paymentMethod!.toUpperCase()}',
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.grey.shade700,
                        ),
                      ),
                  ],
                ),
                const Divider(height: 16),
                Text(
                  'Order: ${tx.razorpayOrderId}',
                  style: TextStyle(
                    fontSize: 10,
                    fontFamily: 'monospace',
                    color: Colors.grey.shade600,
                  ),
                ),
                if (tx.razorpayPaymentId != null)
                  Text(
                    'Payment: ${tx.razorpayPaymentId}',
                    style: TextStyle(
                      fontSize: 10,
                      fontFamily: 'monospace',
                      color: Colors.grey.shade600,
                    ),
                  ),
                if (tx.errorDescription != null) ...[
                  const SizedBox(height: 4),
                  Text(
                    'Reason: ${tx.errorDescription}',
                    style: TextStyle(
                      fontSize: 11,
                      color: Colors.red.shade700,
                    ),
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }
}
