class ApiEndpoints {
  // Base backend URL: defaults to 127.0.0.1 for desktop/web and 10.0.2.2 for Android emulator
  static String baseUrl = 'http://127.0.0.1:8000';

  // System endpoints
  static const String health = '/health';
  static const String databaseHealth = '/database/health';
  static const String apiV1 = '/api/v1';

  // Phase 3 Authentication endpoints
  static const String authSendOtp = '/api/v1/auth/send-otp';
  static const String authVerifyOtp = '/api/v1/auth/verify-otp';
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
  static const String schemeAssessmentsHistory = '/api/v1/schemes/assessments/history';
  static String schemeDetail(String id) => '/api/v1/schemes/$id';
  static String schemeAssess(String id) => '/api/v1/schemes/$id/assess';
  static String schemeAssessmentDetail(String id) => '/api/v1/schemes/assessments/$id';

  // Phase 5 Document Vault & OCR Pipeline
  static const String documents = '/api/v1/documents';
  static const String documentUpload = '/api/v1/documents/upload';
  static String documentDetail(String id) => '/api/v1/documents/$id';
  static String documentDownload(String id) => '/api/v1/documents/$id/download';
  static String documentRetryOcr(String id) => '/api/v1/documents/$id/retry-ocr';
  static String schemeDocumentChecklist(String schemeId) => '/api/v1/documents/scheme/$schemeId/checklist';

  // Future phase endpoints (Phases 6-8)
  static const String readiness = '/api/v1/readiness';

}
