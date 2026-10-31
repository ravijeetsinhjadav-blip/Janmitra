# JanMitra Assist – Implementation Progress Tracker

**Project Name:** JanMitra Assist – AI-Powered Government Service Eligibility and Document Intelligence System  
**Academic Target:** MCA Major Project  
**Current Phase:** Phase 3 (Authentication & User Management) – COMPLETED

---

## 1. Environment & Architecture Dependency Audit

| Tool / Technology | Required For | Status on Machine | Detected Version / Path | Action Taken / Status |
| :--- | :--- | :--- | :--- | :--- |
| **Git** | Version Control | **Installed** | `2.53.0.windows.2` | Monorepo tracked with clean branch history |
| **Python** | Backend API | **Installed** | `3.13.3` (`pip 25.2`) | Active venv at `backend/venv` |
| **FastAPI** | REST API Framework | **Installed** | `0.115.11` | Phase 1-3 endpoints mounted and active |
| **SQLAlchemy** | ORM Engine | **Installed** | `2.1.6` | Declarative models for users, sessions, profiles |
| **Psycopg 3** | PostgreSQL Driver | **Installed** | `3.3.6` (`psycopg-binary 3.3.6`) | Configured via `postgresql+psycopg://` URL |
| **Alembic** | Database Migrations | **Installed** | `1.20.1` | Migrations `e36378f07849` and `4dcd7dfc601d` |
| **PyJWT** | JWT Authentication | **Installed** | `2.10.1` (`pyjwt[crypto]`) | HS256 access tokens with payload verification |
| **Bcrypt** | Cryptographic Hashing | **Installed** | `4.3.0` | Secure hashing for OTPs and secret tokens |
| **Flutter SDK** | Mobile Client | **Installed (Local)**| `3.27.4` / Dart `3.6.2` | Local SDK configured at `.\flutter\bin\flutter.bat` |
| **flutter_secure_storage** | Mobile Token Vault | **Installed** | `^9.2.2` | Hardware-backed keystore/keychain for tokens |
| **Node.js / npm** | Admin Dashboard | **Installed** | `v24.14.1` / `11.11.0` | React dashboard scaffolded in Phase 1 |
| **PostgreSQL Server** | Relational Database | Service Configured | Localhost port 5432 | Psycopg 3 driver & migrations ready |

---

## 2. Phase 3 Tasks & Completion Status

- [x] **Task 1: Mobile OTP Authentication & Modular SMS Engine**
  - Implemented `BaseSMSProvider` abstract interface in `backend/app/services/otp_service.py`.
  - Built `DevelopmentSMSAdapter`: logs OTP in console and returns `dev_otp` in dev mode for local testing without SMS costs.
  - Built `ProductionSMSAdapter`: prepared for real SMS gateway integration via environment variables.
  - Implemented configurable OTP expiry (default: 300s), resend cooldown (default: 60s), and attempt limit (5 attempts max with lockout).
  - Normalizes Indian mobile numbers into E.164 standard (`+91XXXXXXXXXX`).

- [x] **Task 2: Secure JWT Authentication & Refresh Token Rotation**
  - Configured short-lived JWT access tokens (default: 30 minutes) using `PyJWT` and secret key from environment.
  - Generated cryptographically secure 256-bit random refresh tokens (default: 30 days).
  - Enforced refresh token rotation: old refresh token is marked revoked immediately upon issuing a new pair.
  - Persisted SHA-256 hashes of refresh tokens in `user_sessions` table (raw tokens are never stored).
  - Built secure logout endpoint (`POST /api/v1/auth/logout`) supporting single session or all-session revocation.

- [x] **Task 3: Citizen Registration & Role-Based Authorization**
  - Automatic citizen account provisioning upon first successful OTP verification.
  - Public registration strictly assigns role `citizen`; prevents privilege self-elevation.
  - Created reusable FastAPI dependencies in `backend/app/core/dependencies.py`:
    - `get_current_user`: extracts and validates Bearer JWT.
    - `get_current_active_citizen`: enforces active citizen checks.
    - `get_current_admin`: restricts access to administrative endpoints.

- [x] **Task 4: User Profile Management API**
  - Implemented full profile lifecycle in `backend/app/api/v1/endpoints/users.py`:
    - `GET /api/v1/users/me`: retrieves authenticated user details.
    - `GET /api/v1/users/me/profile`: retrieves citizen profile.
    - `PUT /api/v1/users/me/profile`: creates or replaces citizen profile.
    - `PATCH /api/v1/users/me/profile`: partial update of profile fields.
    - `DELETE /api/v1/users/me/profile`: deletes profile while preserving user account.
  - Strict user data isolation: all operations query by `current_user.id`.
  - **Privacy Enforcement:** Aadhaar number is strictly excluded from registration, schemas, and database tables.

- [x] **Task 5: Account Deletion Request Workflow**
  - Implemented `POST /api/v1/users/me/delete-request` in `backend/app/api/v1/endpoints/users.py`.
  - Schedules account for permanent deletion after a 30-day retention window.
  - Immediately deactivates account (`user.is_active = False`) and revokes all active sessions.

- [x] **Task 6: Database Migrations for Authentication**
  - Created Alembic migration `4dcd7dfc601d_add_auth_and_user_management_tables.py`:
    - `otp_challenges`: stores hashed OTP, attempt counter, cooldown, and expiry.
    - `user_sessions`: stores hashed refresh tokens, device info, IP, and revocation state.
    - `account_deletion_requests`: tracks deletion requests, scheduled date, and reason.
  - Verified static SQL compilation via `alembic upgrade head --sql`.

- [x] **Task 7: Flutter Mobile Client Implementation**
  - Configured `FlutterSecureStorage` in `mobile_app/lib/core/services/secure_storage_service.dart`.
  - Enforced mobile security rule: tokens are NEVER stored in SharedPreferences.
  - Implemented `AuthService` in `mobile_app/lib/core/network/auth_service.dart`:
    - OTP challenge request & verification.
    - Automatic token refresh on 401 HTTP response.
    - Profile fetching and updating.
    - Account deletion request submission.
  - Built complete Flutter UI flow:
    1. `SplashScreen`: validates persistent tokens and routes accordingly.
    2. `LoginScreen`: 10-digit Indian mobile validation and OTP request.
    3. `OTPVerificationScreen`: 6-digit OTP entry, cooldown timer, resend button, and dev-mode autofill.
    4. `ProfileSetupScreen`: required and optional demographic fields with privacy notice.
    5. `HomeScreen`: authenticated citizen banner, verification badge, profile completion chip, and logout.
    6. `ProfileViewScreen`: view and edit profile details.
    7. `AccountDeletionDialog`: 30-day retention confirmation dialog.

- [x] **Task 8: Testing & Verification**
  - **Backend Unit Tests:** 31 unit tests across auth, user management, and core database models using in-memory SQLite (100% passed).
  - **PostgreSQL Compatibility Tests:** 3 dedicated PostgreSQL dialect tests verifying UUID, JSONB, and foreign key cascade rules without requiring an active daemon (100% passed); 1 live PostgreSQL integration test prepared and skipped cleanly when port 5432 is offline.
  - **Subscription Pricing Correction:** Audited and corrected subscription pricing to approved standard: Monthly ₹99, Yearly ₹799 (removed unauthorized six-month cycle and non-standard pricing).
  - **Account Deletion Retention:** Ensured deletion request deactivates the citizen account, revokes sessions, and adheres to statutory retention without immediate data destruction.
  - **Mobile Client:** 3 widget tests written in `mobile_app/test/widget_test.dart` (100% passed).
  - **Code Quality:** `flutter analyze` completed with **0 errors, 0 warnings**.

---

## 3. Verification Commands & Actual Results

### 3.1 Backend Unit & Integration Tests (Pytest)
```powershell
& .\backend\venv\Scripts\pytest.exe .\backend\tests -v
```
**Actual Output:**
```
============================= test session starts =============================
platform win32 -- Python 3.13.3, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\ravij\OneDrive\Desktop\Janmitra\backend
configfile: pytest.ini
plugins: anyio-4.15.1, asyncio-1.4.1
collected 35 items

backend\tests\test_auth.py::TestOTPWorkflow::test_otp_generation_success PASSED          [  2%]
backend\tests\test_auth.py::TestOTPWorkflow::test_invalid_mobile_number_rejection PASSED [  5%]
backend\tests\test_auth.py::TestOTPWorkflow::test_otp_verification_and_new_user_registration PASSED [  8%]
backend\tests\test_auth.py::TestOTPWorkflow::test_incorrect_otp_rejection PASSED        [ 11%]
backend\tests\test_auth.py::TestOTPWorkflow::test_expired_otp_rejection PASSED          [ 14%]
backend\tests\test_auth.py::TestOTPWorkflow::test_otp_attempt_limits_lockout PASSED     [ 17%]
backend\tests\test_auth.py::TestOTPWorkflow::test_dev_otp_never_exposed_in_production PASSED [ 20%]
backend\tests\test_auth.py::TestJWTSessionsAndRoles::test_existing_user_login_no_duplicate PASSED [ 22%]
backend\tests\test_auth.py::TestJWTSessionsAndRoles::test_authenticated_me_endpoint PASSED [ 25%]
backend\tests\test_auth.py::TestJWTSessionsAndRoles::test_unauthorized_without_token PASSED [ 28%]
backend\tests\test_auth.py::TestJWTSessionsAndRoles::test_refresh_token_rotation PASSED  [ 31%]
backend\tests\test_auth.py::TestJWTSessionsAndRoles::test_logout_revokes_token PASSED    [ 34%]
backend\tests\test_database.py::TestDatabaseModelsMetadata::test_all_expected_tables_registered PASSED [ 37%]
backend\tests\test_database.py::TestDatabaseModelsMetadata::test_user_model_schema PASSED [ 40%]
backend\tests\test_database.py::TestDatabaseModelsMetadata::test_user_profile_relationship_and_privacy PASSED [ 42%]
backend\tests\test_database.py::TestDatabaseModelsMetadata::test_scheme_model_schema PASSED [ 45%]
backend\tests\test_database.py::TestDatabaseModelsMetadata::test_document_metadata_storage_separation PASSED [ 48%]
backend\tests\test_database.py::TestDatabaseModelsMetadata::test_assessment_jsonb_and_advisory_nature PASSED [ 51%]
backend\tests\test_database.py::TestDatabaseModelsMetadata::test_application_manual_status_values PASSED [ 54%]
backend\tests\test_database.py::TestDatabaseModelsMetadata::test_subscription_pricing_and_plans PASSED [ 57%]
backend\tests\test_database.py::TestDatabaseModelsMetadata::test_notification_model_schema PASSED [ 60%]
backend\tests\test_database.py::TestDatabaseHealthApi::test_root_endpoint_includes_db_link PASSED [ 62%]
backend\tests\test_database.py::TestDatabaseHealthApi::test_general_health_endpoint_still_operational PASSED [ 65%]
backend\tests\test_database.py::TestDatabaseHealthApi::test_database_health_endpoint_safe_response PASSED [ 68%]
backend\tests\test_health.py::test_health_check PASSED                                  [ 71%]
backend\tests\test_health.py::test_root_endpoint PASSED                                 [ 74%]
backend\tests\test_postgres_integration.py::TestPostgresDialectCompatibility::test_all_models_compile_for_postgresql PASSED [ 77%]
backend\tests\test_postgres_integration.py::TestPostgresDialectCompatibility::test_postgresql_uuid_and_jsonb_types PASSED [ 80%]
backend\tests\test_postgres_integration.py::TestPostgresDialectCompatibility::test_postgresql_foreign_key_cascades PASSED [ 82%]
backend\tests\test_postgres_integration.py::TestPostgresLiveIntegration::test_live_postgres_otp_and_session_persistence SKIPPED [ 85%]
backend\tests\test_users.py::TestUserProfileManagement::test_create_and_get_profile PASSED [ 88%]
backend\tests\test_users.py::TestUserProfileManagement::test_patch_profile PASSED      [ 91%]
backend\tests\test_users.py::TestUserProfileManagement::test_user_data_isolation PASSED [ 94%]
backend\tests\test_users.py::TestUserProfileManagement::test_delete_profile PASSED     [ 97%]
backend\tests\test_users.py::TestUserProfileManagement::test_account_deletion_request_workflow PASSED [100%]

================== 34 passed, 1 skipped, 1 warning in 8.07s ===================
```

### 3.2 Flutter Mobile Widget Tests
```powershell
cd mobile_app; ..\flutter\bin\flutter.bat test
```
**Actual Output:**
```
00:00 +0: loading C:/Users/ravij/OneDrive/Desktop/Janmitra/mobile_app/test/widget_test.dart
00:00 +0: JanMitra Assist launch and splash screen verification test
00:02 +1: LoginScreen citizen sign-in verification test
00:03 +2: HomeScreen Phase 3 citizen status verification test
00:04 +3: All tests passed!
```

### 3.3 Flutter Static Analysis
```powershell
cd mobile_app; ..\flutter\bin\flutter.bat analyze
```
**Actual Output:**
```
Analyzing mobile_app...
No issues found! (ran in 123.4s)
```

### 3.4 Alembic Static Migration Verification
```powershell
Set-Location backend; & .\venv\Scripts\alembic.exe upgrade head --sql
```
**Actual Output:** Successfully generated clean transactional PostgreSQL DDL migrating from `e36378f07849` to `4dcd7dfc601d`, creating `otp_challenges`, `user_sessions`, and `account_deletion_requests` with strict foreign key constraints and indexes.

### 3.5 Manual Testing Still Required
The following verification steps require external system resources and must be executed manually once infrastructure is provisioned:
1. **Live PostgreSQL Service:** Start local or remote PostgreSQL daemon, create `janmitra_db`, and execute `alembic upgrade head`.
2. **Third-Party SMS Gateway:** When a production SMS provider (e.g., Twilio, Fast2SMS) is finalized, configure production API credentials in `.env` and verify over-the-air SMS OTP delivery to a physical device.
3. **Physical Android/iOS Device Run:** Deploy Flutter app to a physical Android device or emulator to test hardware Keystore encryption and biometric unlock.

