class ApiEndpoints {
  // Base backend URL (use 10.0.2.2 for Android emulator accessing localhost)
  static const String emulatorBaseUrl = 'http://10.0.2.2:8000';
  static const String localBaseUrl = 'http://127.0.0.1:8000';

  // System endpoints
  static const String health = '/health';
  static const String apiV1 = '/api/v1';

  // Future phase endpoints
  static const String schemes = '/api/v1/schemes';
  static const String documents = '/api/v1/documents';
  static const String eligibility = '/api/v1/eligibility';
  static const String readiness = '/api/v1/readiness';
}

