class ApiEndpoints {
  // Global Live Public HTTPS URL (Render Cloud Production - 24/7 without laptop)
  static String baseUrl = 'https://janmitra-e8ca.onrender.com';

  // System endpoints
  static const String health = '/health';
  static const String databaseHealth = '/database/health';
  static const String apiV1 = '/api/v1';

  // Phase 3 Authentication endpoints (Email + Password, No OTP)
  static const String authLogin = '/api/v1/auth/login';
  static const String authRegister = '/api/v1/auth/register';
  static const String authForgotPassword = '/api/v1/auth/forgot-password';
  static const String authResetPassword = '/api/v1/auth/reset-password';
  static const String authSetCredentials = '/api/v1/auth/set-credentials';
  static const String authRefresh = '/api/v1/auth/refresh';
  static const String authLogout = '/api/v1/auth/logout';
  static const String authMe = '/api/v1/auth/me';

  // Phase 3 User Management & Profile endpoints
  static const String userProfile = '/api/v1/users/me/profile';
  static const String userDeleteRequest = '/api/v1/users/me/delete-request';

  // Phase 4 Government Scheme Discovery & Eligibility Engine
  static const String schemes = '/api/v1/schemes';
  static const String schemeCategories = '/api/v1/schemes/categories';
  static const String schemeRecommendations = '/api/v1/schemes/recommendations';
  static const String schemeAssessmentsHistory =
      '/api/v1/schemes/assessments/history';
  static String schemeDetail(String id) => '/api/v1/schemes/$id';
  static String schemeAssess(String id) => '/api/v1/schemes/$id/assess';
  static String schemeAssessmentDetail(String id) =>
      '/api/v1/schemes/assessments/$id';

  // Scheme Intelligence, Category Rules, Document Guides & Beneficiary Analytics
  static String schemeCategoriesList(String schemeId) =>
      '/api/v1/schemes/$schemeId/categories';
  static String schemeCategoryRules(String schemeId, {String? category}) =>
      category != null
          ? '/api/v1/schemes/$schemeId/category-rules?category=$category'
          : '/api/v1/schemes/$schemeId/category-rules';
  static String schemeCategoryDocuments(String schemeId, {String? category}) =>
      category != null
          ? '/api/v1/schemes/$schemeId/documents?category=$category'
          : '/api/v1/schemes/$schemeId/documents';
  static String schemeAnalytics(String schemeId) =>
      '/api/v1/schemes/$schemeId/analytics';
  static String schemeEvaluateCategory(String schemeId) =>
      '/api/v1/schemes/$schemeId/evaluate-category';
  static const String documentGuides = '/api/v1/document-guides';
  static String documentGuideDetail(String documentType) =>
      '/api/v1/document-guides/$documentType';

  // Phase 5 Document Vault & OCR Pipeline
  static const String documents = '/api/v1/documents';
  static const String documentUpload = '/api/v1/documents/upload';
  static String documentDetail(String id) => '/api/v1/documents/$id';
  static String documentDownload(String id) => '/api/v1/documents/$id/download';
  static String documentRetryOcr(String id) =>
      '/api/v1/documents/$id/retry-ocr';
  static String schemeDocumentChecklist(String schemeId) =>
      '/api/v1/documents/scheme/$schemeId/checklist';

  // Phase 6 AI Advisory & Readiness Assessment Engine
  static const String advisory = '/api/v1/advisory';
  static String schemeAssessAndAdvise(String schemeId) =>
      '/api/v1/advisory/schemes/$schemeId/assess-and-advise';
  static String assessmentAdvisory(String assessmentId) =>
      '/api/v1/advisory/assessments/$assessmentId';
  static String assessmentRegenerate(String assessmentId) =>
      '/api/v1/advisory/assessments/$assessmentId/regenerate';

  // Phase 7.1 Application Assistance Module
  static const String assistance = '/api/v1/assistance';
  static String schemeAssistancePrepare(String schemeId) =>
      '/api/v1/assistance/schemes/$schemeId/prepare';
  static String schemeAssistanceChecklistToggle(
          String schemeId, String itemId) =>
      '/api/v1/assistance/schemes/$schemeId/checklist/$itemId';
  static String schemeAssistanceGuide(String schemeId) =>
      '/api/v1/assistance/schemes/$schemeId/guide';

  // Phase 7.2 & Phase 9 Subscriptions & Assisted Payments Module
  static const String subscriptionsPlans = '/api/v1/subscriptions/plans';
  static const String subscriptionsMe = '/api/v1/subscriptions/me';
  static const String subscriptionsCancel = '/api/v1/subscriptions/cancel';
  static const String subscriptionsHistory = '/api/v1/subscriptions/history';
  static const String paymentsCreateOrder = '/api/v1/payments/create-order';
  static const String paymentsVerify = '/api/v1/payments/verify';
  static const String paymentsHistory = '/api/v1/payments/history';

  // Phase 8 Application Tracking, Status History & Citizen Reminders
  static const String applications = '/api/v1/applications';
  static String applicationDetail(String id) => '/api/v1/applications/$id';
  static String applicationHistory(String id) =>
      '/api/v1/applications/$id/history';
  static const String applicationUpcomingReminders =
      '/api/v1/applications/reminders/upcoming';
  static String applicationReminders(String applicationId) =>
      '/api/v1/applications/$applicationId/reminders';
  static String applicationReminderDetail(
          String applicationId, String reminderId) =>
      '/api/v1/applications/$applicationId/reminders/$reminderId';

  // Phase 8 Notifications & Firebase Cloud Messaging
  static const String notifications = '/api/v1/notifications';
  static const String notificationDevices = '/api/v1/notifications/devices';
  static String notificationDeviceDetail(String token) =>
      '/api/v1/notifications/devices/$token';
  static String notificationRead(String id) => '/api/v1/notifications/$id/read';
  static const String notificationsReadAll = '/api/v1/notifications/read-all';
  static const String notificationsUnreadCount =
      '/api/v1/notifications/unread-count';

  // Future phase endpoints
  static const String readiness = '/api/v1/readiness';
}
