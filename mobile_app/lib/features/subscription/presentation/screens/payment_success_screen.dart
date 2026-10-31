import 'package:flutter/material.dart';
import '../../../../core/theme/app_theme.dart';
import 'package:janmitra_assist/features/subscription/models/subscription_models.dart';

class PaymentSuccessScreen extends StatelessWidget {
  final PaymentVerificationResponseModel verificationResult;

  const PaymentSuccessScreen({
    super.key,
    required this.verificationResult,
  });

  @override
  Widget build(BuildContext context) {
    final sub = verificationResult.subscription;
    final cycle = sub.billingCycle ?? 'monthly';
    final expiryFormatted = sub.endDate != null
        ? '${sub.endDate!.day}/${sub.endDate!.month}/${sub.endDate!.year}'
        : 'Ongoing';

    return Scaffold(
      appBar: AppBar(
        title: const Text('Payment Confirmed'),
        automaticallyImplyLeading: false,
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: Colors.green.shade50,
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.check_circle_rounded,
                  color: AppTheme.accentGreen,
                  size: 72,
                ),
              ),
              const SizedBox(height: 20),
              const Text(
                'Welcome to JanMitra Premium!',
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                  color: AppTheme.primaryDark,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                verificationResult.message,
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 14, color: Colors.grey.shade700),
              ),
              const SizedBox(height: 24),

              // Confirmation Card
              Card(
                elevation: 2,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                  side: BorderSide(color: Colors.green.shade300),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    children: [
                      _buildReceiptRow('Tier', 'JanMitra Premium ⭐'),
                      const Divider(height: 16),
                      _buildReceiptRow(
                        'Billing Cycle',
                        cycle.toUpperCase(),
                      ),
                      const Divider(height: 16),
                      _buildReceiptRow('Valid Until', expiryFormatted),
                      const Divider(height: 16),
                      _buildReceiptRow(
                        'Monthly Document Quota',
                        '${sub.usage.aiDocumentAnalysesLimit} analyses',
                      ),
                      const Divider(height: 16),
                      _buildReceiptRow(
                        'Monthly Guidance Quota',
                        '${sub.usage.aiGuidanceSessionsLimit} sessions',
                      ),
                      const Divider(height: 16),
                      _buildReceiptRow(
                        'Transaction ID',
                        verificationResult.transactionId.substring(0, 13) + '...',
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),

              ElevatedButton.icon(
                icon: const Icon(Icons.arrow_forward),
                label: const Text('Start Using Premium Features'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.accentGreen,
                  foregroundColor: Colors.white,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
                  textStyle: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                onPressed: () {
                  Navigator.of(context).pop(true);
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildReceiptRow(String label, String value) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: TextStyle(fontSize: 13, color: Colors.grey.shade600),
        ),
        Text(
          value,
          style: const TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.bold,
            color: Colors.black87,
          ),
        ),
      ],
    );
  }
}
