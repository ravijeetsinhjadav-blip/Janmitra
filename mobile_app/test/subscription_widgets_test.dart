import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:razorpay_flutter/razorpay_flutter.dart';
import 'package:janmitra_assist/features/subscription/models/subscription_models.dart';
import 'package:janmitra_assist/features/subscription/services/razorpay_checkout_adapter.dart';
import 'package:janmitra_assist/features/subscription/presentation/screens/payment_failure_screen.dart';
import 'package:janmitra_assist/features/subscription/presentation/screens/payment_history_screen.dart';
import 'package:janmitra_assist/features/subscription/presentation/screens/payment_success_screen.dart';
import 'package:janmitra_assist/features/subscription/presentation/screens/subscription_plans_screen.dart';

void main() {
  group('Subscription & Payment Models Unit Tests', () {
    test('SubscriptionPlanModel correctly deserializes from JSON', () {
      final json = {
        'plan_type': 'free',
        'name': 'Free Plan',
        'description': 'Essential features for all citizens',
        'price_monthly': 0.0,
        'price_yearly': 0.0,
        'currency': 'INR',
        'features': [
          'Basic government scheme search',
          'Basic eligibility guidance',
          'Official portal application links',
          'Up to 3 AI document analyses / month',
          'Up to 5 AI guidance sessions / month',
        ],
        'doc_analyses_limit': 3,
        'ai_guidance_limit': 5,
        'is_popular': false,
      };

      final plan = SubscriptionPlanModel.fromJson(json);

      expect(plan.planType, 'free');
      expect(plan.name, 'Free Plan');
      expect(plan.priceMonthly, 0.0);
      expect(plan.priceYearly, 0.0);
      expect(plan.docAnalysesLimit, 3);
      expect(plan.aiGuidanceLimit, 5);
      expect(plan.features.length, 5);
      expect(plan.isPopular, isFalse);
    });

    test('UsageQuotaModel calculates remaining and flags correctly', () {
      final json = {
        'ai_document_analyses_used': 2,
        'ai_document_analyses_limit': 3,
        'ai_guidance_sessions_used': 5,
        'ai_guidance_sessions_limit': 5,
        'can_analyze_document': true,
        'can_request_guidance': false,
        'quota_reset_date': '2026-11-01T00:00:00Z',
      };

      final quota = UsageQuotaModel.fromJson(json);

      expect(quota.aiDocumentAnalysesUsed, 2);
      expect(quota.aiDocumentAnalysesLimit, 3);
      expect(quota.aiGuidanceSessionsUsed, 5);
      expect(quota.aiGuidanceSessionsLimit, 5);
      expect(quota.canAnalyzeDocument, isTrue);
      expect(quota.canRequestGuidance, isFalse);
      expect(quota.quotaResetDate, isNotNull);
    });

    test('CitizenSubscriptionModel detects active status and dates', () {
      final json = {
        'user_id': 'user-uuid-1234',
        'plan_type': 'premium',
        'billing_cycle': 'monthly',
        'status': 'active',
        'is_active': true,
        'start_date': '2026-10-15T10:00:00Z',
        'end_date': '2026-11-15T10:00:00Z',
        'days_remaining': 15,
        'usage': {
          'ai_document_analyses_used': 10,
          'ai_document_analyses_limit': 30,
          'ai_guidance_sessions_used': 15,
          'ai_guidance_sessions_limit': 100,
          'can_analyze_document': true,
          'can_request_guidance': true,
          'quota_reset_date': '2026-11-01T00:00:00Z',
        },
        'disclaimer': 'JanMitra is an independent preparation platform.',
      };

      final sub = CitizenSubscriptionModel.fromJson(json);

      expect(sub.userId, 'user-uuid-1234');
      expect(sub.planType, 'premium');
      expect(sub.isPremium, isTrue);
      expect(sub.billingCycle, 'monthly');
      expect(sub.daysRemaining, 15);
      expect(sub.usage.aiDocumentAnalysesUsed, 10);
      expect(sub.usage.aiDocumentAnalysesLimit, 30);
    });

    test('PaymentTransactionModel parses status and fields correctly', () {
      final json = {
        'id': 'tx-uuid-5678',
        'razorpay_order_id': 'order_N1234567890',
        'razorpay_payment_id': 'pay_N1234567890',
        'amount': 99.0,
        'currency': 'INR',
        'plan_type': 'premium',
        'billing_cycle': 'monthly',
        'payment_status': 'captured',
        'payment_method': 'upi',
        'error_code': null,
        'error_description': null,
        'created_at': '2026-10-31T12:00:00Z',
      };

      final tx = PaymentTransactionModel.fromJson(json);

      expect(tx.id, 'tx-uuid-5678');
      expect(tx.razorpayOrderId, 'order_N1234567890');
      expect(tx.razorpayPaymentId, 'pay_N1234567890');
      expect(tx.paymentStatus, 'captured');
      expect(tx.amount, 99.0);
      expect(tx.paymentMethod, 'upi');
    });
  });

  group('RazorpayCheckoutAdapter Tests', () {
    test('MockRazorpayAdapter calls onSuccess with deterministic payload', () {
      final adapter = MockRazorpayAdapter();
      PaymentSuccessResponse? successRes;

      adapter.init(
        onSuccess: (res) => successRes = res,
        onError: (_) {},
        onExternalWallet: (_) {},
      );

      adapter.open({
        'key': 'rzp_test_mock',
        'order_id': 'order_test_abc123',
        'amount': 9900,
      });

      expect(successRes, isNotNull);
      expect(successRes!.orderId, 'order_test_abc123');
      expect(successRes!.paymentId, adapter.mockPaymentId);
      expect(successRes!.signature, adapter.mockSignature);

      adapter.dispose();
    });

    test('MockRazorpayAdapter calls onError when shouldSucceed is false', () {
      final adapter = MockRazorpayAdapter()..shouldSucceed = false;
      PaymentFailureResponse? failureRes;

      adapter.init(
        onSuccess: (_) {},
        onError: (res) => failureRes = res,
        onExternalWallet: (_) {},
      );

      adapter.open({
        'key': 'rzp_test_mock',
        'order_id': 'order_test_fail',
        'amount': 9900,
      });

      expect(failureRes, isNotNull);
      expect(failureRes!.code, Razorpay.PAYMENT_CANCELLED);
      expect(failureRes!.message, 'Payment was cancelled by citizen');

      adapter.dispose();
    });

    test('MockRazorpayAdapter calls onExternalWallet when simulateExternalWallet is true', () {
      final adapter = MockRazorpayAdapter()
        ..simulateExternalWallet = true
        ..mockWalletName = 'paytm';
      ExternalWalletResponse? walletRes;

      adapter.init(
        onSuccess: (_) {},
        onError: (_) {},
        onExternalWallet: (res) => walletRes = res,
      );

      adapter.open({
        'key': 'rzp_test_mock',
        'order_id': 'order_test_wallet',
        'amount': 9900,
      });

      expect(walletRes, isNotNull);
      expect(walletRes!.walletName, 'paytm');

      adapter.dispose();
    });
  });

  group('Subscription Screens Widget Tests', () {
    testWidgets('SubscriptionPlansScreen renders plans, quotas, and notice',
        (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final dummyPlans = SubscriptionPlansResponseModel(
        plans: [
          SubscriptionPlanModel(
            planType: 'free',
            name: 'Free Plan',
            description: 'Basic scheme search and eligibility',
            priceMonthly: 0.0,
            priceYearly: 0.0,
            currency: 'INR',
            features: [
              'Basic government scheme search',
              'Up to 3 AI document analyses / month',
            ],
            docAnalysesLimit: 3,
            aiGuidanceLimit: 5,
            isPopular: false,
          ),
          SubscriptionPlanModel(
            planType: 'premium',
            name: 'JanMitra Premium',
            description: 'Advanced readiness and priority guidance',
            priceMonthly: 99.0,
            priceYearly: 799.0,
            currency: 'INR',
            features: [
              'Everything in Free',
              'Up to 30 AI document analyses / month',
              'Priority Application Checklist',
            ],
            docAnalysesLimit: 30,
            aiGuidanceLimit: 100,
            isPopular: true,
          ),
        ],
        disclaimer: 'JanMitra is an independent preparation platform.',
      );

      final dummySub = CitizenSubscriptionModel(
        userId: 'test-user-1',
        planType: 'free',
        billingCycle: 'monthly',
        status: 'active',
        isActive: true,
        startDate: DateTime.parse('2026-10-01T00:00:00Z'),
        endDate: null,
        daysRemaining: null,
        usage: UsageQuotaModel(
          aiDocumentAnalysesUsed: 1,
          aiDocumentAnalysesLimit: 3,
          aiGuidanceSessionsUsed: 2,
          aiGuidanceSessionsLimit: 5,
          canAnalyzeDocument: true,
          canRequestGuidance: true,
          quotaResetDate: DateTime.parse('2026-11-01T00:00:00Z'),
        ),
        disclaimer: 'JanMitra is an independent preparation platform.',
      );

      final mockAdapter = MockRazorpayAdapter();

      await tester.pumpWidget(
        MaterialApp(
          home: SubscriptionPlansScreen(
            initialPlans: dummyPlans,
            initialSubscription: dummySub,
            checkoutAdapter: mockAdapter,
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Check header and plan title
      expect(find.text('Subscription & Quota'), findsOneWidget);
      expect(find.text('JanMitra Free Tier'), findsOneWidget);

      // Check quota indicators
      expect(find.text('Monthly Usage Quota'), findsOneWidget);
      expect(find.text('1 of 3 used'), findsOneWidget);
      expect(find.text('2 of 5 used'), findsOneWidget);

      // Check billing toggle
      expect(find.text('Monthly (₹99)'), findsOneWidget);
      expect(find.text('Yearly (₹799)'), findsOneWidget);

      // Check plan cards
      expect(find.text('Free Plan'), findsOneWidget);
      expect(find.text('JanMitra Premium'), findsOneWidget);
      expect(find.text('Upgrade Now'), findsOneWidget);

      // Check disclaimer
      expect(
        find.textContaining('JanMitra Assist fees cover platform intelligence'),
        findsOneWidget,
      );

      // Toggle billing cycle to Yearly
      await tester.tap(find.text('Yearly (₹799)'));
      await tester.pumpAndSettle();

      expect(find.text('Save ~33%'), findsOneWidget);
    });

    testWidgets('PaymentSuccessScreen renders receipt and tier info',
        (WidgetTester tester) async {
      final verificationResult = PaymentVerificationResponseModel(
        success: true,
        message: 'Payment verified and Premium subscription activated.',
        transactionId: 'tx-test-9999-abcdef',
        subscription: CitizenSubscriptionModel(
          userId: 'test-user-success',
          planType: 'premium',
          billingCycle: 'monthly',
          status: 'active',
          isActive: true,
          startDate: DateTime.parse('2026-10-31T12:00:00Z'),
          endDate: DateTime.parse('2026-11-30T12:00:00Z'),
          daysRemaining: 30,
          usage: UsageQuotaModel(
            aiDocumentAnalysesUsed: 0,
            aiDocumentAnalysesLimit: 30,
            aiGuidanceSessionsUsed: 0,
            aiGuidanceSessionsLimit: 100,
            canAnalyzeDocument: true,
            canRequestGuidance: true,
            quotaResetDate: DateTime.parse('2026-11-01T00:00:00Z'),
          ),
          disclaimer: 'JanMitra is an independent preparation platform.',
        ),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: PaymentSuccessScreen(
            verificationResult: verificationResult,
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Payment Confirmed'), findsOneWidget);
      expect(find.text('Welcome to JanMitra Premium!'), findsOneWidget);
      expect(find.text('JanMitra Premium ⭐'), findsOneWidget);
      expect(find.text('Start Using Premium Features'), findsOneWidget);
    });

    testWidgets('PaymentFailureScreen renders retry and instructions',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: PaymentFailureScreen(
            errorMessage: 'Payment signature verification failed. Untrusted payment payload rejected.',
            orderId: 'order_test_failure_123',
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Payment Incomplete'), findsOneWidget);
      expect(find.text('Payment Could Not Be Processed'), findsOneWidget);
      expect(
        find.textContaining('Payment signature verification failed'),
        findsOneWidget,
      );
      expect(find.text('Order ID: order_test_failure_123'), findsOneWidget);
      expect(find.text('Try Again'), findsOneWidget);
      expect(find.text('Go Back'), findsOneWidget);
    });

    testWidgets('PaymentHistoryScreen renders transaction cards correctly',
        (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      final dummyTransactions = [
        PaymentTransactionModel(
          id: 'tx-1001',
          razorpayOrderId: 'order_1001',
          razorpayPaymentId: 'pay_1001',
          amount: 99.0,
          currency: 'INR',
          planType: 'premium',
          billingCycle: 'monthly',
          paymentStatus: 'captured',
          paymentMethod: 'upi',
          errorCode: null,
          errorDescription: null,
          createdAt: DateTime.parse('2026-10-31T10:00:00Z'),
        ),
        PaymentTransactionModel(
          id: 'tx-1002',
          razorpayOrderId: 'order_1002',
          razorpayPaymentId: null,
          amount: 799.0,
          currency: 'INR',
          planType: 'premium',
          billingCycle: 'yearly',
          paymentStatus: 'failed',
          paymentMethod: 'card',
          errorCode: 'BAD_REQUEST_ERROR',
          errorDescription: 'Transaction declined by issuer',
          createdAt: DateTime.parse('2026-10-30T10:00:00Z'),
        ),
      ];

      await tester.pumpWidget(
        MaterialApp(
          home: PaymentHistoryScreen(
            initialTransactions: dummyTransactions,
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(find.text('Payment History'), findsOneWidget);
      expect(find.text('₹99.00'), findsOneWidget);
      expect(find.text('₹799.00'), findsOneWidget);
      expect(find.text('CAPTURED'), findsOneWidget);
      expect(find.text('FAILED'), findsOneWidget);
      expect(find.text('Method: UPI'), findsOneWidget);
      expect(find.text('Method: CARD'), findsOneWidget);
      expect(find.text('Reason: Transaction declined by issuer'), findsOneWidget);
    });
  });
}
