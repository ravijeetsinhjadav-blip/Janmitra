import 'dart:convert';
import 'package:http/http.dart' as http;
import '../../../core/network/api_endpoints.dart';
import '../../../core/services/secure_storage_service.dart';
import '../models/subscription_models.dart';

class SubscriptionService {
  static final SubscriptionService _instance = SubscriptionService._internal();
  factory SubscriptionService() => _instance;
  SubscriptionService._internal();

  final SecureStorageService _storage = SecureStorageService();

  Future<Map<String, String>> _buildHeaders() async {
    final token = await _storage.getAccessToken();
    final headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (token != null) {
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  /// Retrieve available subscription plans catalog
  Future<SubscriptionPlansResponseModel> getPlans() async {
    final uri = Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.subscriptionsPlans}');
    final headers = await _buildHeaders();

    final response = await http.get(uri, headers: headers);
    final data = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode == 200) {
      return SubscriptionPlansResponseModel.fromJson(data);
    } else {
      final msg = data['detail'] ?? 'Failed to load subscription plans';
      throw Exception(msg);
    }
  }

  /// Retrieve authenticated citizen's current subscription and quota status
  Future<CitizenSubscriptionModel> getMySubscription() async {
    final uri = Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.subscriptionsMe}');
    final headers = await _buildHeaders();

    final response = await http.get(uri, headers: headers);
    final data = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode == 200) {
      return CitizenSubscriptionModel.fromJson(data);
    } else {
      final msg = data['detail'] ?? 'Failed to load citizen subscription';
      throw Exception(msg);
    }
  }

  /// Create a secure Razorpay order on backend
  Future<RazorpayOrderModel> createOrder({required String billingCycle}) async {
    final uri = Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.paymentsCreateOrder}');
    final headers = await _buildHeaders();
    final body = jsonEncode({
      'plan_type': 'premium',
      'billing_cycle': billingCycle,
    });

    final response = await http.post(uri, headers: headers, body: body);
    final data = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode == 200 || response.statusCode == 201) {
      return RazorpayOrderModel.fromJson(data);
    } else {
      final msg = data['detail'] ?? 'Failed to create payment order';
      throw Exception(msg);
    }
  }

  /// Verify cryptographic payment signature on backend
  Future<PaymentVerificationResponseModel> verifyPayment({
    required String orderId,
    required String paymentId,
    required String signature,
    String? paymentMethod,
  }) async {
    final uri = Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.paymentsVerify}');
    final headers = await _buildHeaders();
    final body = jsonEncode({
      'razorpay_order_id': orderId,
      'razorpay_payment_id': paymentId,
      'razorpay_signature': signature,
      'payment_method': paymentMethod ?? 'upi',
    });

    final response = await http.post(uri, headers: headers, body: body);
    final data = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode == 200) {
      return PaymentVerificationResponseModel.fromJson(data);
    } else {
      final msg = data['detail'] ?? 'Payment verification failed';
      throw Exception(msg);
    }
  }

  /// Retrieve citizen's past payment history
  Future<PaymentHistoryResponseModel> getPaymentHistory() async {
    final uri = Uri.parse('${ApiEndpoints.baseUrl}${ApiEndpoints.paymentsHistory}');
    final headers = await _buildHeaders();

    final response = await http.get(uri, headers: headers);
    final data = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode == 200) {
      return PaymentHistoryResponseModel.fromJson(data);
    } else {
      final msg = data['detail'] ?? 'Failed to load payment history';
      throw Exception(msg);
    }
  }
}
