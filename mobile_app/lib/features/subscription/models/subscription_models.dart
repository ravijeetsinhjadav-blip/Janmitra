class SubscriptionPlanModel {
  final String planType;
  final String name;
  final String description;
  final double priceMonthly;
  final double priceYearly;
  final String currency;
  final List<String> features;
  final int docAnalysesLimit;
  final int aiGuidanceLimit;
  final bool isPopular;

  SubscriptionPlanModel({
    required this.planType,
    required this.name,
    required this.description,
    required this.priceMonthly,
    required this.priceYearly,
    required this.currency,
    required this.features,
    required this.docAnalysesLimit,
    required this.aiGuidanceLimit,
    this.isPopular = false,
  });

  factory SubscriptionPlanModel.fromJson(Map<String, dynamic> json) {
    return SubscriptionPlanModel(
      planType: json['plan_type'] as String? ?? 'free',
      name: json['name'] as String? ?? 'Plan',
      description: json['description'] as String? ?? '',
      priceMonthly: (json['price_monthly'] as num?)?.toDouble() ?? 0.0,
      priceYearly: (json['price_yearly'] as num?)?.toDouble() ?? 0.0,
      currency: json['currency'] as String? ?? 'INR',
      features: (json['features'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      docAnalysesLimit: json['doc_analyses_limit'] as int? ?? 3,
      aiGuidanceLimit: json['ai_guidance_limit'] as int? ?? 5,
      isPopular: json['is_popular'] as bool? ?? false,
    );
  }
}

class SubscriptionPlansResponseModel {
  final List<SubscriptionPlanModel> plans;
  final String disclaimer;

  SubscriptionPlansResponseModel({
    required this.plans,
    required this.disclaimer,
  });

  factory SubscriptionPlansResponseModel.fromJson(Map<String, dynamic> json) {
    return SubscriptionPlansResponseModel(
      plans: (json['plans'] as List<dynamic>?)
              ?.map(
                (e) =>
                    SubscriptionPlanModel.fromJson(e as Map<String, dynamic>),
              )
              .toList() ??
          [],
      disclaimer: json['disclaimer'] as String? ?? '',
    );
  }
}

class UsageQuotaModel {
  final int aiDocumentAnalysesUsed;
  final int aiDocumentAnalysesLimit;
  final int aiGuidanceSessionsUsed;
  final int aiGuidanceSessionsLimit;
  final bool canAnalyzeDocument;
  final bool canRequestGuidance;
  final DateTime quotaResetDate;

  UsageQuotaModel({
    required this.aiDocumentAnalysesUsed,
    required this.aiDocumentAnalysesLimit,
    required this.aiGuidanceSessionsUsed,
    required this.aiGuidanceSessionsLimit,
    required this.canAnalyzeDocument,
    required this.canRequestGuidance,
    required this.quotaResetDate,
  });

  factory UsageQuotaModel.fromJson(Map<String, dynamic> json) {
    return UsageQuotaModel(
      aiDocumentAnalysesUsed: json['ai_document_analyses_used'] as int? ?? 0,
      aiDocumentAnalysesLimit: json['ai_document_analyses_limit'] as int? ?? 3,
      aiGuidanceSessionsUsed: json['ai_guidance_sessions_used'] as int? ?? 0,
      aiGuidanceSessionsLimit: json['ai_guidance_sessions_limit'] as int? ?? 5,
      canAnalyzeDocument: json['can_analyze_document'] as bool? ?? true,
      canRequestGuidance: json['can_request_guidance'] as bool? ?? true,
      quotaResetDate: json['quota_reset_date'] != null
          ? DateTime.tryParse(json['quota_reset_date'] as String) ??
              DateTime.now()
          : DateTime.now(),
    );
  }
}

class CitizenSubscriptionModel {
  final String userId;
  final String planType;
  final String? billingCycle;
  final String status;
  final bool isActive;
  final DateTime startDate;
  final DateTime? endDate;
  final int? daysRemaining;
  final UsageQuotaModel usage;
  final String disclaimer;

  CitizenSubscriptionModel({
    required this.userId,
    required this.planType,
    this.billingCycle,
    required this.status,
    required this.isActive,
    required this.startDate,
    this.endDate,
    this.daysRemaining,
    required this.usage,
    required this.disclaimer,
  });

  bool get isPremium => planType == 'premium' && isActive;

  factory CitizenSubscriptionModel.fromJson(Map<String, dynamic> json) {
    return CitizenSubscriptionModel(
      userId: json['user_id'] as String? ?? '',
      planType: json['plan_type'] as String? ?? 'free',
      billingCycle: json['billing_cycle'] as String?,
      status: json['status'] as String? ?? 'active',
      isActive: json['is_active'] as bool? ?? true,
      startDate: json['start_date'] != null
          ? DateTime.tryParse(json['start_date'] as String) ?? DateTime.now()
          : DateTime.now(),
      endDate: json['end_date'] != null
          ? DateTime.tryParse(json['end_date'] as String)
          : null,
      daysRemaining: json['days_remaining'] as int?,
      usage: UsageQuotaModel.fromJson(
        json['usage'] as Map<String, dynamic>? ?? {},
      ),
      disclaimer: json['disclaimer'] as String? ?? '',
    );
  }
}

class RazorpayOrderModel {
  final String orderId;
  final int amount;
  final double amountInr;
  final String currency;
  final String keyId;
  final String planType;
  final String billingCycle;
  final bool isDevMode;

  RazorpayOrderModel({
    required this.orderId,
    required this.amount,
    required this.amountInr,
    required this.currency,
    required this.keyId,
    required this.planType,
    required this.billingCycle,
    this.isDevMode = false,
  });

  factory RazorpayOrderModel.fromJson(Map<String, dynamic> json) {
    return RazorpayOrderModel(
      orderId: json['order_id'] as String? ?? '',
      amount: json['amount'] as int? ?? 0,
      amountInr: (json['amount_inr'] as num?)?.toDouble() ?? 0.0,
      currency: json['currency'] as String? ?? 'INR',
      keyId: json['key_id'] as String? ?? '',
      planType: json['plan_type'] as String? ?? 'premium',
      billingCycle: json['billing_cycle'] as String? ?? 'monthly',
      isDevMode: json['is_dev_mode'] as bool? ?? false,
    );
  }
}

class PaymentVerificationResponseModel {
  final bool success;
  final String message;
  final String transactionId;
  final CitizenSubscriptionModel subscription;

  PaymentVerificationResponseModel({
    required this.success,
    required this.message,
    required this.transactionId,
    required this.subscription,
  });

  factory PaymentVerificationResponseModel.fromJson(Map<String, dynamic> json) {
    return PaymentVerificationResponseModel(
      success: json['success'] as bool? ?? false,
      message: json['message'] as String? ?? '',
      transactionId: json['transaction_id'] as String? ?? '',
      subscription: CitizenSubscriptionModel.fromJson(
        json['subscription'] as Map<String, dynamic>? ?? {},
      ),
    );
  }
}

class PaymentTransactionModel {
  final String id;
  final String razorpayOrderId;
  final String? razorpayPaymentId;
  final double amount;
  final String currency;
  final String planType;
  final String billingCycle;
  final String paymentStatus;
  final String? paymentMethod;
  final String? errorCode;
  final String? errorDescription;
  final DateTime createdAt;

  PaymentTransactionModel({
    required this.id,
    required this.razorpayOrderId,
    this.razorpayPaymentId,
    required this.amount,
    required this.currency,
    required this.planType,
    required this.billingCycle,
    required this.paymentStatus,
    this.paymentMethod,
    this.errorCode,
    this.errorDescription,
    required this.createdAt,
  });

  factory PaymentTransactionModel.fromJson(Map<String, dynamic> json) {
    return PaymentTransactionModel(
      id: json['id'] as String? ?? '',
      razorpayOrderId: json['razorpay_order_id'] as String? ?? '',
      razorpayPaymentId: json['razorpay_payment_id'] as String?,
      amount: (json['amount'] as num?)?.toDouble() ?? 0.0,
      currency: json['currency'] as String? ?? 'INR',
      planType: json['plan_type'] as String? ?? 'premium',
      billingCycle: json['billing_cycle'] as String? ?? 'monthly',
      paymentStatus: json['payment_status'] as String? ?? 'created',
      paymentMethod: json['payment_method'] as String?,
      errorCode: json['error_code'] as String?,
      errorDescription: json['error_description'] as String?,
      createdAt: json['created_at'] != null
          ? DateTime.tryParse(json['created_at'] as String) ?? DateTime.now()
          : DateTime.now(),
    );
  }
}

class PaymentHistoryResponseModel {
  final int total;
  final List<PaymentTransactionModel> items;

  PaymentHistoryResponseModel({
    required this.total,
    required this.items,
  });

  factory PaymentHistoryResponseModel.fromJson(Map<String, dynamic> json) {
    return PaymentHistoryResponseModel(
      total: json['total'] as int? ?? 0,
      items: (json['items'] as List<dynamic>?)
              ?.map(
                (e) =>
                    PaymentTransactionModel.fromJson(e as Map<String, dynamic>),
              )
              .toList() ??
          [],
    );
  }
}
