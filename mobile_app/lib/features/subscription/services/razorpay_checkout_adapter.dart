import 'package:razorpay_flutter/razorpay_flutter.dart';

/// Callback signatures matching razorpay_flutter
typedef PaymentSuccessHandler = void Function(PaymentSuccessResponse response);
typedef PaymentErrorHandler = void Function(PaymentFailureResponse response);
typedef ExternalWalletHandler = void Function(ExternalWalletResponse response);

/// Decoupled interface for Razorpay checkout, allowing live platform channel
/// execution on mobile devices and headless deterministic mocking during automated tests.
abstract class RazorpayCheckoutAdapter {
  void init({
    required PaymentSuccessHandler onSuccess,
    required PaymentErrorHandler onError,
    required ExternalWalletHandler onExternalWallet,
  });

  void open(Map<String, dynamic> options);

  void dispose();
}

/// Production adapter wrapping the native Razorpay Flutter SDK platform channel.
class LiveRazorpayAdapter implements RazorpayCheckoutAdapter {
  Razorpay? _razorpay;

  @override
  void init({
    required PaymentSuccessHandler onSuccess,
    required PaymentErrorHandler onError,
    required ExternalWalletHandler onExternalWallet,
  }) {
    _razorpay = Razorpay();
    _razorpay!.on(Razorpay.EVENT_PAYMENT_SUCCESS, onSuccess);
    _razorpay!.on(Razorpay.EVENT_PAYMENT_ERROR, onError);
    _razorpay!.on(Razorpay.EVENT_EXTERNAL_WALLET, onExternalWallet);
  }

  @override
  void open(Map<String, dynamic> options) {
    if (_razorpay == null) {
      throw StateError('RazorpayCheckoutAdapter must be initialized before open()');
    }
    _razorpay!.open(options);
  }

  @override
  void dispose() {
    _razorpay?.clear();
    _razorpay = null;
  }
}

/// Headless test adapter for deterministic automated widget tests without platform channels.
class MockRazorpayAdapter implements RazorpayCheckoutAdapter {
  PaymentSuccessHandler? _onSuccess;
  PaymentErrorHandler? _onError;
  ExternalWalletHandler? _onExternalWallet;

  bool shouldSucceed = true;
  bool simulateExternalWallet = false;
  String mockWalletName = 'paytm';
  String mockPaymentId = 'pay_mock_test_123456';
  String mockSignature = 'mock_signature_test_hash';
  int mockErrorCode = Razorpay.PAYMENT_CANCELLED;
  String mockErrorMessage = 'Payment was cancelled by citizen';

  @override
  void init({
    required PaymentSuccessHandler onSuccess,
    required PaymentErrorHandler onError,
    required ExternalWalletHandler onExternalWallet,
  }) {
    _onSuccess = onSuccess;
    _onError = onError;
    _onExternalWallet = onExternalWallet;
  }

  @override
  void open(Map<String, dynamic> options) {
    final orderId = options['order_id'] as String? ?? 'order_mock_test';
    if (simulateExternalWallet) {
      _onExternalWallet?.call(ExternalWalletResponse(mockWalletName));
    } else if (shouldSucceed) {
      _onSuccess?.call(
        PaymentSuccessResponse(
          mockPaymentId,
          orderId,
          mockSignature,
          {},
        ),
      );
    } else {
      _onError?.call(
        PaymentFailureResponse(
          mockErrorCode,
          mockErrorMessage,
          null,
        ),
      );
    }
  }

  @override
  void dispose() {
    _onSuccess = null;
    _onError = null;
    _onExternalWallet = null;
  }
}
