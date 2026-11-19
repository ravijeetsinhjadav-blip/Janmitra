# JANMITRA ASSIST – PHASE 11 FINAL SECURITY & PRODUCTION READINESS AUDIT REPORT

**Date:** November 2, 2026  
**Project:** JanMitra Assist – AI-Powered Government Service Eligibility and Document Intelligence System  
**Auditor:** Senior Software Architect, Security Engineer & QA Lead  
**Audit Type:** Strict Read-Only Technical & Architectural Audit  
**Operating System:** Windows 11  
**Git Branch:** `master` | **HEAD Commit:** `ae199388170391c053ede8264670612919041a9e`

---

## 1. EXECUTIVE SUMMARY & AUDIT METHODOLOGY

This audit was conducted under a strict **READ-ONLY mandate**: no source code was modified, no database was reset, and no commits were created. Every finding documented herein is derived directly from inspecting source code, migration revision trees, configuration files, automated test suites (pytest, flutter test, flutter analyze, vite build), and live runtime processes.

### High-Level Summary
| Area | Local Dev / Academic Evaluation | Production Readiness | Status |
| :--- | :--- | :--- | :--- |
| **Authentication Architecture** | Fully functional Email + Password (Argon2id) | Token security sound; rate limiter needs Redis | **Conditional Pass** |
| **Admin Provisioning** | Secure interactive CLI (`getpass.getpass`) | Domain & secret rotation policy needed | **Pass** |
| **Database & Migrations** | Functional SQLite fallback | Startup raw DDL in `main.py` bypasses Alembic | **High Concern** |
| **Password Recovery & SMTP** | Functional via in-memory `DevMailbox` | Real SMTP server delivery unverified | **Medium Concern** |
| **Rate Limiting** | Functional in-memory sliding window | Multi-worker bypassable; restart volatile | **Medium Concern** |
| **Background Scheduler** | Functional in single Uvicorn process | Multi-worker duplicate dispatch risk | **High Concern** |
| **PostgreSQL Integration** | PostgreSQL DDL compiles cleanly | 6 multi-threaded concurrency tests skipped | **Needs Live PG** |
| **Application Integration** | React (3000), Flutter (8080), Backend (8000) live | Mobile lacks native deep-link reset screen | **Pass** |

---

## 2. GIT STATE & WORKING TREE INTEGRITY

### Exact Repository Status
```bash
$ git status --short
M admin_dashboard/src/components/AdminNavbar.jsx
M admin_dashboard/src/components/Sidebar.jsx
M admin_dashboard/src/pages/ApplicationTracking.jsx
M admin_dashboard/src/pages/AuditLogs.jsx
M admin_dashboard/src/pages/Dashboard.jsx
M admin_dashboard/src/pages/DocumentVerification.jsx
M admin_dashboard/src/pages/FraudAlerts.jsx
M admin_dashboard/src/pages/Login.jsx
M admin_dashboard/src/pages/SchemeManagement.jsx
M admin_dashboard/src/pages/Settings.jsx
M admin_dashboard/src/pages/UserManagement.jsx
M backend/alembic/env.py
M backend/alembic/script.py.mako
M backend/alembic/versions/a3b4c5d6e7f8_add_application_tracking_and_reminders.py
M backend/alembic/versions/b4c5d6e7f8a9_add_password_hash_and_email_auth.py
M backend/app/api/v1/endpoints/admin.py
M backend/app/api/v1/endpoints/analytics.py
M backend/app/api/v1/endpoints/application_tracking.py
M backend/app/api/v1/endpoints/auth.py
M backend/app/api/v1/endpoints/documents.py
M backend/app/api/v1/endpoints/eligibility.py
M backend/app/api/v1/endpoints/fraud.py
M backend/app/api/v1/endpoints/schemes.py
M backend/app/api/v1/endpoints/users.py
M backend/app/cli/admin_create.py
M backend/app/core/config.py
M backend/app/core/database.py
M backend/app/core/security.py
M backend/app/main.py
M backend/app/models/__init__.py
M backend/app/models/application_reminder.py
M backend/app/models/application_status_history.py
M backend/app/models/application_tracking.py
M backend/app/models/audit_log.py
M backend/app/models/document.py
M backend/app/models/fraud_alert.py
M backend/app/models/refresh_token.py
M backend/app/models/scheme.py
M backend/app/models/user.py
M backend/app/schemas/application_reminder.py
M backend/app/schemas/application_status_history.py
M backend/app/schemas/application_tracking.py
M backend/app/schemas/auth.py
M backend/app/schemas/user.py
M backend/app/services/admin_service.py
M backend/app/services/application_reminder_service.py
M backend/app/services/application_tracking_service.py
M backend/app/services/auth_service.py
M backend/app/services/fcm_service.py
M backend/app/services/fraud_detection_service.py
M backend/app/services/ocr_service.py
M backend/app/services/payment_service.py
M backend/app/services/rag_service.py
M backend/app/services/reminder_scheduler_service.py
M backend/app/services/user_service.py
M backend/pyproject.toml
M backend/requirements.txt
M backend/run.py
M backend/tests/conftest.py
M backend/tests/test_admin.py
M backend/tests/test_analytics.py
M backend/tests/test_application_reminders.py
M backend/tests/test_application_tracking.py
M backend/tests/test_auth.py
M backend/tests/test_database.py
M backend/tests/test_documents.py
M backend/tests/test_eligibility.py
M backend/tests/test_fraud.py
M backend/tests/test_ocr.py
M backend/tests/test_payment.py
M backend/tests/test_postgres_integration.py
M backend/tests/test_rag.py
M backend/tests/test_schemes.py
M backend/tests/test_security.py
M backend/tests/test_users.py
M mobile_app/lib/core/constants/api_constants.dart
M mobile_app/lib/core/network/api_client.dart
M mobile_app/lib/data/datasources/auth_remote_datasource.dart
M mobile_app/lib/data/models/user_model.dart
M mobile_app/lib/domain/entities/user.dart
M mobile_app/lib/domain/repositories/auth_repository.dart
M mobile_app/lib/presentation/bloc/auth/auth_bloc.dart
M mobile_app/lib/presentation/bloc/auth/auth_event.dart
M mobile_app/lib/presentation/bloc/auth/auth_state.dart
M mobile_app/lib/presentation/screens/auth/login_screen.dart
M mobile_app/lib/presentation/screens/auth/register_screen.dart
M mobile_app/lib/presentation/screens/dashboard/home_screen.dart
M mobile_app/lib/presentation/screens/profile/profile_screen.dart
M mobile_app/pubspec.yaml
M package.json
?? PHASE_11_FINAL_COMPLETION_REPORT.md
?? PHASE_11_SECURITY_AUDIT_REPORT.md
?? backend/alembic/versions/c5d6e7f8a9b0_add_password_reset_tokens.py
?? backend/app/core/rate_limiter.py
?? backend/app/models/password_reset.py
?? backend/app/services/email_service.py
?? backend/janmitra_dev.db.bak
?? backend/tests/test_password_reset.py
```

- **Staged Files:** Strict 0 bytes (`git diff --cached --stat` empty).
- **Tracked Modified Files:** 90 files.
- **Safety Backup:** Preserved in `C:\Users\ravij\OneDrive\Desktop\janmitra_backup_phase11_20261102T1715`.
- **Integrity Rule:** Zero commits or destructive commands (`git reset`, `git clean`) were issued.

---

## 3. AREA 1: ADMIN SECURITY & CREDENTIAL HYGIENE

### 3.1 Hardcoded Credentials Check
- **Python Source Code & Alembic Migrations:** Exhaustive search across all `.py` and migration files confirmed **ZERO hardcoded passwords, API keys, or admin secrets**.
- **Documentation:** Previous sample admin credentials in `RUNNING_GUIDE.md` (`admin@janmitra.local` / `AdminMaster@2026!`) have been removed and replaced with generic placeholder documentation `<your-administrator-email>`.

### 3.2 Admin Provisioning CLI (`backend/app/cli/admin_create.py`)
- **CLI Security:** The `--password` command-line argument was completely removed to prevent password leakage via shell command history (`.bash_history`, `PSReadLine`) and system process listings (`Get-Process`, `ps -ef`).
- **Interactive Mode:** Uses Python's standard `getpass.getpass("Enter Admin Password: ")` and `getpass.getpass("Confirm Admin Password: ")` without echo.
- **Headless/CI Mode:** Safely falls back to `os.getenv("ADMIN_PROVISION_PASSWORD")` when non-interactive.
- **Password Strength:** Enforces `PasswordValidator.validate()` requiring at least 10 characters, uppercase, lowercase, digit, and special symbol.
- **Hashing:** Hashed immediately using Argon2id (`argon2.PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)`).

### 3.3 Domain Name Hygiene
- During previous smoke tests, an admin was provisioned as `admin@janmitra.gov.in`.
- **Finding:** `janmitra.gov.in` is an assumed/fictional domain used for MCA academic demonstration. In actual government deployment, `.gov.in` domains are strictly allocated by the National Informatics Centre (NIC). No DNS MX records exist for this domain. For production, the organization's verified domain must be used.

### 3.4 Privilege Escalation Prevention
- Public registration (`POST /api/v1/auth/register`) strictly sets `role = "citizen"` regardless of user input.
- User creation schemas (`UserCreate`) do not accept or expose a `role` field from public callers.

---

## 4. AREA 2: DATABASE & MIGRATIONS ARCHITECTURE

### 4.1 Startup Schema Reconciliation in `backend/app/main.py` (HIGH RISK)
- **Code Inspected (`backend/app/main.py` lines 41–48):**
  ```python
  if _is_sqlite:
      with engine.begin() as conn:
          cols = [c["name"] for c in inspect(conn).get_columns("users")]
          if "password_hash" not in cols:
              conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"))
  ```
- **Audit Evaluation:**
  - **Why it was added:** During local SQLite development, older developer databases lacked the `password_hash` column.
  - **Architectural Defect:** Executing raw DDL in application startup code bypasses Alembic version tracking. The `alembic_version` table is not updated by this call, which creates unversioned schema drift.
  - **Production Risk:** If this logic were ever extended to PostgreSQL or production startup, it would create race conditions between multiple application containers starting simultaneously.
  - **Verdict:** Must be removed prior to production release. SQLite and PostgreSQL databases must be migrated exclusively through `alembic upgrade head`.

### 4.2 Alembic Migration Linearity
- Checked Alembic heads:
  ```bash
  $ alembic heads
  c5d6e7f8a9b0 (head)
  ```
- Checked history:
  1. `<base> -> 1a2b3c4d5e6f` (initial)
  2. `1a2b3c4d5e6f -> 2b3c4d5e6f7a` (schemes)
  3. `...`
  4. `9a0b1c2d3e4f -> a1b2c3d4e5f6` (fcm)
  5. `a1b2c3d4e5f6 -> a3b4c5d6e7f8` (tracking & reminders)
  6. `a3b4c5d6e7f8 -> b4c5d6e7f8a9` (password_hash & email auth)
  7. `b4c5d6e7f8a9 -> c5d6e7f8a9b0` (password_reset_tokens)
- **Verdict:** Valid, strictly linear 13-migration chain with zero branch heads or split leaves.

### 4.3 SQLite vs PostgreSQL Compatibility
- All 17 models use portable SQLAlchemy types.
- Dialect DDL compilation tests in `test_postgres_integration.py` confirmed that PostgreSQL types (`UUID(as_uuid=True)`, `JSONB`, `INET`) compile without error under the `PostgresqlImpl` dialect.

---

## 5. AREA 3: SMTP & PASSWORD RECOVERY

### 5.1 Real SMTP vs DevMailbox Fallback (MEDIUM RISK)
- **Code Inspected (`backend/app/services/email_service.py`):**
  - Uses `smtplib.SMTP` / `smtplib.SMTP_SSL`.
  - Configured with `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_USE_TLS`.
  - When SMTP connection raises `(ConnectionRefusedError, socket.error, smtplib.SMTPException)`, it falls back to:
    ```python
    self._dev_mailbox.append({"to": to_email, "subject": subject, "body": body})
    ```
- **Audit Evaluation:**
  - On the current development machine, Docker / Mailpit is offline.
  - All test runs and manual smoke tests operated against `_dev_mailbox`.
  - **Real external SMTP network delivery has NOT been validated.**
  - **Production Requirement:** Before production launch, live SMTP relay (e.g. AWS SES, Sendgrid, or self-hosted Postfix) must be verified with active TLS handshake, STARTTLS, and SPF/DKIM/DMARC DNS records.

### 5.2 Password Reset Token Security
- **Token Generation:** `secrets.token_urlsafe(32)` (256 bits of cryptographically secure random entropy).
- **Token Storage:** Only the SHA-256 hash `hashlib.sha256(raw_token.encode()).hexdigest()` is stored in `password_reset_tokens.token_hash`. If the database is compromised, reset tokens cannot be reconstructed.
- **Expiration:** Enforced 15-minute validity window checked against UTC (`datetime.now(timezone.utc) > token_record.expires_at`).
- **Single-Use:** Token record sets `is_used = True` upon consumption. Token reuse returns HTTP 400 (`"Invalid or expired reset token"`).
- **Session Revocation:** On password reset completion, `AuthService.revoke_session(user_id=token_record.user_id, all_sessions=True)` is called, revoking all active refresh tokens in `refresh_tokens`.
- **Anti-Enumeration:** `POST /api/v1/auth/forgot-password` returns `{"message": "If this email is registered, a password reset link has been sent."}` for existing and non-existing emails alike, mitigating user enumeration attacks.

---

## 6. AREA 4: RATE LIMITING & BRUTE FORCE PROTECTION

### 6.1 In-Memory Implementation (`backend/app/core/rate_limiter.py`)
- Implemented as `InMemoryRateLimiter`:
  - Uses a process-local `threading.Lock()` and a dictionary of sliding timestamp windows.
  - Protects `/api/v1/auth/login` (5 attempts per 60 seconds per IP/email).
  - Protects `/api/v1/auth/forgot-password` (3 attempts per 300 seconds per IP).

### 6.2 Multi-Worker & Process Restart Limitations (HIGH RISK FOR PROD)
- **Multi-Worker Vulnerability:** In production, Uvicorn is typically run with multiple worker processes (e.g., `uvicorn main:app --workers 4`). Because each worker process has its own isolated memory space, the rate-limit buckets are **not shared across workers**. An attacker distributing requests across worker connections gets $4\times$ the rate-limit allowance.
- **Process Restart Vulnerability:** Any process restart or container redeployment flushes all rate-limit buckets, clearing active lockouts.
- **Verdict:** Sufficient for local single-process MCA demonstration, but **UNSUITABLE for multi-process production**. Must be replaced with Redis-backed rate limiting (e.g., Redis `INCR` + `EXPIRE` or `slowapi` with Redis backend).

---

## 7. AREA 5: BACKGROUND REMINDER SCHEDULER & CONCURRENCY

### 7.1 Lifespan Background Loop (`backend/app/main.py`)
- **Code Inspected (`backend/app/main.py` lines 70–85):**
  ```python
  @asynccontextmanager
  async def lifespan(app: FastAPI):
      # ...
      scheduler_task = asyncio.create_task(_run_reminder_scheduler_loop())
      yield
      scheduler_task.cancel()
  ```
- **Multi-Worker Concurrency Defect (HIGH RISK):**
  - When Uvicorn runs with `--workers N`, **every worker process executes the lifespan handler**.
  - If 4 workers are running, **4 independent scheduler loops run concurrently** checking for due reminders every 60 seconds.

### 7.2 Missing Database Locking in `ReminderSchedulerService`
- **Code Inspected (`backend/app/services/reminder_service.py`):**
  - Reminders are queried with standard `db.query(ApplicationReminder).filter(...)`.
  - **No distributed locking:** Does not use `SELECT ... FOR UPDATE SKIP LOCKED` or PostgreSQL advisory locks.
  - **Duplicate Dispatch Risk:** Two workers executing at the same second will retrieve the identical pending reminder, simultaneously send two duplicate FCM/email notifications, and only then mark the reminder as sent.
  - **Production Requirement:**
    1. Move the scheduler loop out of the web worker into a dedicated single-instance background worker process (Celery / RQ / separate container), OR
    2. Add PostgreSQL `with_for_update(skip_locked=True)` to `process_due_reminders()`.

---

## 8. AREA 6: POSTGRESQL TEST STATUS & THE 6 SKIPPED TESTS

### 8.1 The 6 Skipped Tests in `backend/tests/test_postgres_integration.py`
Running `pytest backend/tests/test_postgres_integration.py` produces:
```
6 passed, 6 skipped in 2.14s
```
Skipped tests:
1. `test_live_postgres_auth_and_session_persistence`
2. `test_concurrent_monthly_quota_record_initialization`
3. `test_concurrent_document_quota_reservations_respect_limit`
4. `test_concurrent_document_retry_requests`
5. `test_live_postgres_lease_renewal_vs_stale_recovery`
6. `test_live_postgres_old_worker_finalization_after_token_invalidation`

### 8.2 Why They Were Skipped
- The fixture `pg_engine` cleanly checks:
  ```python
  try:
      engine = create_engine(TEST_POSTGRES_URL)
      with engine.connect() as conn: ...
  except Exception:
      pytest.skip("PostgreSQL test database not available at localhost:5432")
  ```
- The local Docker daemon was offline during testing; hence no PostgreSQL service was listening on port 5432.

### 8.3 Why Live PostgreSQL is Required
- Tests 2 through 6 test multi-threaded database concurrency using Python `threading.Thread` to execute simultaneous quota reservations and lease renewals.
- SQLite cannot run these tests because SQLite uses coarse-grained file-level locking: concurrent writes result in `sqlite3.OperationalError: database is locked`.
- Live PostgreSQL provides row-level locks (`SELECT ... FOR UPDATE`), transaction isolation levels (`SERIALIZABLE` / `READ COMMITTED`), and connection pool concurrency.
- **Verdict:** PostgreSQL table DDL is validated, but **live multi-connection concurrency and locking behaviors have not been tested in this local test session**.

---

## 9. AREA 7: APPLICATION INTEGRATION & ZERO-OTP STATUS

### 9.1 Zero-OTP Verification
- **Codebase Scan:** Zero active OTP submission, verification, or SMS dependencies exist in citizen registration or login flows.
- Twilio and Firebase phone verification SDK calls have been completely bypassed or removed from the active authentication path.
- Legacy fields (`phone_verified`, `otp_code`) remain in `users` table as nullable fields for schema stability, but are unused by active endpoints.

### 9.2 End-to-End Operational State
- **FastAPI Backend (Port 8000):** Healthy (`GET /health` -> 200 OK, `GET /docs` -> 200 OK).
- **React Admin Dashboard (Port 3000):** Healthy (HTTP 200 OK, Vite built in 10.26s with 0 errors).
- **Flutter Web Citizen App (Port 8080):** Healthy (HTTP 200 OK, 139/139 tests passed, 0 analyzer issues).

### 9.3 Missing Mobile Screen
- The Flutter mobile app has:
  - Email + Password Login
  - Citizen Registration
  - Forgot Password request dialog (sends reset email)
- **Missing Feature:** Flutter currently lacks a dedicated in-app `/reset-password` deep-link screen to consume the reset token directly on mobile. The reset email contains a web URL directing the user to the web browser interface.

---

## 10. RISK CLASSIFICATION TABLE

| Risk ID | Severity | Category | Description | Local Dev Impact | Production Impact |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SEC-01** | **HIGH** | Database | Startup raw DDL in `main.py` alters schema outside Alembic version control. | None (SQLite works) | Schema drift, startup race condition across containers |
| **SEC-02** | **HIGH** | Concurrency | Background reminder loop runs in every Uvicorn worker without distributed lock. | None (1 worker) | Duplicate emails/notifications dispatched to users |
| **SEC-03** | **HIGH** | Integration | 6 live PostgreSQL concurrency tests skipped due to offline PostgreSQL daemon. | None (SQLite used) | Unverified transactional row-locking in high load |
| **SEC-04** | **MEDIUM** | Security | In-memory rate limiting does not sync across multi-worker processes or survive restart. | None | Distributed brute-force attacks bypass rate limit |
| **SEC-05** | **MEDIUM** | Email | Real SMTP network transport unverified; test execution relied on `DevMailbox`. | None | Delivery failures if cloud SMTP credentials/ports fail |
| **SEC-06** | **MEDIUM** | Mobile UX | Flutter citizen app lacks dedicated native `/reset-password` deep-link screen. | Low (Web fallback) | Citizen must use web browser to complete password reset |
| **SEC-07** | **LOW** | Identity | Assumed `janmitra.gov.in` domain used for demonstration without verified DNS MX. | None | Fails email reputation checks if used in public cloud |
| **SEC-08** | **LOW** | Schema | Legacy OTP columns (`otp_code`, `otp_expires_at`) persist in `users` table. | None | Technical debt / unused database columns |

---

## 11. DEVELOPMENT VS PRODUCTION READINESS VERDICT

```
================================================================================
FINAL VERDICT:
- LOCAL DEMONSTRATION & MCA MAJOR PROJECT EVALUATION: [ PASSED ]
- PRODUCTION CLOUD DEPLOYMENT:                        [ CONDITIONAL / NOT READY ]
================================================================================
```

### Explanation:
1. **For MCA Major Project Evaluation / Local Viva:**
   The application is in an **exceptional, fully working state**. All 3 layers (FastAPI, React Admin, Flutter) are running live. Authentication is 100% Email + Password with Argon2id. Automated test coverage is extraordinarily high:
   - Backend Pytest: 264 passed, 0 failed.
   - Flutter Tests: 139 passed, 0 failed.
   - Flutter Analyze: 0 issues.
   - React Admin: Clean Vite production build.
   Zero OTP friction exists. The `DevMailbox` cleanly captures reset links for immediate demonstration.

2. **For Public Production Cloud Deployment:**
   The application **cannot be released to public production** until the 3 High-risk issues (startup DDL removal, scheduler worker deduplication/locking, and live PostgreSQL concurrency validation) and the Redis rate-limiting upgrade are implemented.

---

## 12. PRIORITIZED CORRECTION PLAN

Before deploying JanMitra Assist to a production cloud environment, execute the following numbered remediation plan:

1. **Remove Startup DDL from `main.py` (SEC-01):**
   - Delete lines 41–48 in `backend/app/main.py`.
   - Ensure the Alembic linear migration chain (`alembic upgrade head`) is the sole mechanism for database schema synchronization in CI/CD pipelines.

2. **Decouple Background Scheduler from Web Workers (SEC-02):**
   - Remove `asyncio.create_task(_run_reminder_scheduler_loop())` from the FastAPI `lifespan` handler in `main.py`.
   - Create a dedicated CLI command `python -m app.cli.reminder_worker` or standalone Celery/RQ beat process.
   - In `ReminderSchedulerService.process_due_reminders()`, use PostgreSQL row-level locks:
     `db.query(ApplicationReminder).filter(...).with_for_update(skip_locked=True)`.

3. **Validate Live PostgreSQL Integration Suite (SEC-03):**
   - Start a live PostgreSQL 16 container (`docker compose up -d postgres`).
   - Run `pytest backend/tests/test_postgres_integration.py` to ensure all 12 PostgreSQL integration and concurrency tests pass without any skips.

4. **Migrate Rate Limiting to Redis (SEC-04):**
   - Replace `InMemoryRateLimiter` with Redis-backed sliding window counters (using Redis `evalsha` or `slowapi` with `redis://` storage backend).
   - Ensure rate limit buckets persist across server process restarts and synchronize across all Uvicorn worker processes.

5. **Verify Live External SMTP Relay (SEC-05):**
   - Configure live SMTP credentials for a certified provider (e.g., AWS SES, SendGrid, or institutional SMTP).
   - Verify end-to-end email arrival in an external inbox with valid TLS handshake and SPF/DKIM validation.

6. **Implement Flutter Deep-Link Password Reset Screen (SEC-06):**
   - Add a `/reset-password` route in Flutter mobile app with query parameter extraction (`?token=...`).
   - Provide a clean form with `New Password` and `Confirm Password` fields posting to `/api/v1/auth/reset-password`.

7. **Clean Legacy OTP Schema Debt (SEC-08):**
   - Author a final cleanup Alembic migration dropping `otp_code` and `otp_expires_at` columns from `users`.

---

**Report Prepared By:** JanMitra Assist QA & Security Engineering Group  
**Status:** Audit Finalized & Read-Only Repository Verified.

