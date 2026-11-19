# JanMitra Assist – PostgreSQL Integration Test Report

**Project Title:** JanMitra Assist – AI-Powered Government Service Eligibility and Document Intelligence System  
**Test Scope:** Real PostgreSQL Integration & Concurrency Verification in Isolated Docker Container  
**PostgreSQL Version:** PostgreSQL 16.15 (Alpine Linux, 64-bit)  
**Date:** November 3, 2026  
**Status:** **100% PASSED (15 of 15 PostgreSQL Tests, 284 of 284 Full Backend Suite)**

---

## 1. Executive Summary

An isolated, secure PostgreSQL test container was deployed using Docker Desktop on the local machine. All 14 linear Alembic migrations were successfully applied to head `d6e7f8a9b0c1`, creating all 20 required tables with native UUID primary keys, JSONB columns, indexes, and foreign key cascades.

The **6 previously skipped PostgreSQL integration tests** were executed against the live PostgreSQL instance and passed with 100% success. In addition, **4 new PostgreSQL concurrency and locking tests** were added to specifically verify multi-worker reminder claiming using `SELECT ... FOR UPDATE SKIP LOCKED`, lease auto-healing, retry backoff exhaustion, and transaction rollback safety. 

Across the entire backend pytest suite, **284 out of 284 tests passed with zero skips and zero failures**.

---

## 2. PostgreSQL Test Environment Configuration

### 2.1 Docker Daemon Activation
Docker Desktop was initiated via its native background daemon service (`com.docker.backend.exe` / WSL2 `docker-desktop` distro). Engine connectivity was verified over the named pipe `//./pipe/dockerDesktopLinuxEngine`.

### 2.2 Isolated Test Container Specifications
- **Image:** `postgres:16-alpine` (Digest: `0cefaabd882e`)
- **Container Name:** `janmitra_postgres_test_ci`
- **Network Binding:** Bound exclusively to localhost loopback `127.0.0.1:5432:5432` (never exposed publicly).
- **Environment Variables:**
  - `POSTGRES_DB=janmitra_test_db`
  - `POSTGRES_USER=janmitra_test_user`
  - `POSTGRES_PASSWORD=<env-configured-secret>`
- **Database Driver:** `psycopg3` (version 3.3.6) and `psycopg2-binary` (version 2.9.13) for seamless `postgresql+psycopg://` and `postgresql://` URI dialect support.
- **Isolation Guarantee:** All integration and concurrency tests executed against `janmitra_test_db`. The local SQLite development database (`backend/janmitra_dev.db`) was not touched or modified.

### 2.3 Health & Readiness Proof
```bash
docker exec janmitra_postgres_test_ci pg_isready -U janmitra_test_user -d janmitra_test_db
# Output: /var/run/postgresql:5432 - accepting connections
```

Connection verification via SQLAlchemy:
```
Connected to: PostgreSQL 16.15 on x86_64-pc-linux-musl, compiled by gcc (Alpine 15.2.0) 15.2.0, 64-bit
```

---

## 3. Database Schema & Alembic Migrations

### 3.1 Migration Execution
Alembic migrations were applied directly to PostgreSQL using `ALEMBIC_DATABASE_URL`:
```powershell
$env:ALEMBIC_DATABASE_URL="postgresql+psycopg://janmitra_test_user:janmitra_test_password_2026@127.0.0.1:5432/janmitra_test_db"
alembic upgrade head
```

Execution Log:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> e36378f07849, initial_schema_phase_2
INFO  [alembic.runtime.migration] Running upgrade e36378f07849 -> 4dcd7dfc601d, add_auth_and_user_management_tables
INFO  [alembic.runtime.migration] Running upgrade 4dcd7dfc601d -> 7a8e5f3c9102, extend scheme model for phase 4
INFO  [alembic.runtime.migration] Running upgrade 7a8e5f3c9102 -> e9f8a7b6c5d4, extend document metadata for phase 5
INFO  [alembic.runtime.migration] Running upgrade e9f8a7b6c5d4 -> f1a2b3c4d5e6, add phase 6 ai advisory and rag tables
INFO  [alembic.runtime.migration] Running upgrade f1a2b3c4d5e6 -> b2c3d4e5f6a7, add phase 7.2 payment transactions table
INFO  [alembic.runtime.migration] Running upgrade b2c3d4e5f6a7 -> c4d5e6f7a8b9, add webhook_events table and scheme guide cache
INFO  [alembic.runtime.migration] Running upgrade c4d5e6f7a8b9 -> d5e6f7a8b9c0, add user_monthly_quotas table and refund lifecycle columns
INFO  [alembic.runtime.migration] Running upgrade d5e6f7a8b9c0 -> e6f7a8b9c0d1, add processing ownership tokens to document metadata
INFO  [alembic.runtime.migration] Running upgrade e6f7a8b9c0d1 -> f2a3b4c5d6e7, add application status history and reminders
INFO  [alembic.runtime.migration] Running upgrade f2a3b4c5d6e7 -> a3b4c5d6e7f8, add device tokens and fcm push notification support
INFO  [alembic.runtime.migration] Running upgrade a3b4c5d6e7f8 -> b4c5d6e7f8a9, add email password authentication and password_hash
INFO  [alembic.runtime.migration] Running upgrade b4c5d6e7f8a9 -> c5d6e7f8a9b0, add password reset tokens table
INFO  [alembic.runtime.migration] Running upgrade c5d6e7f8a9b0 -> d6e7f8a9b0c1, add reminder dispatch lease and tracking columns
```

### 3.2 Schema Head & Table Verification
Current revision in PostgreSQL `alembic_version` table: `d6e7f8a9b0c1 (head)`.

All 20 tables verified in `janmitra_test_db`:
1. `account_deletion_requests` (UUID PK, FK to users ON DELETE CASCADE)
2. `alembic_version` (Version tracker)
3. `application_reminders` (UUID PK, dispatch leases, retry counters)
4. `application_status_history` (UUID PK, status audit trail)
5. `applications` (UUID PK, user/scheme relationships)
6. `assessments` (UUID PK, JSONB eligibility answers)
7. `device_tokens` (UUID PK, FCM device registration)
8. `document_metadata` (UUID PK, lease expiration, processing tokens)
9. `notifications` (UUID PK, in-app notification records)
10. `otp_challenges` (UUID PK, hashed OTPs)
11. `password_reset_tokens` (UUID PK, SHA-256 hashed single-use tokens)
12. `payment_transactions` (UUID PK, Razorpay orders, refund audit log JSONB)
13. `scheme_knowledge_chunks` (UUID PK, RAG knowledge chunks)
14. `schemes` (UUID PK, criteria JSONB, guide cache JSONB)
15. `subscriptions` (UUID PK, tier billing records)
16. `user_monthly_quotas` (UUID PK, quota ledgers with UNIQUE(user_id, year_month))
17. `user_profiles` (UUID PK, citizen demographic profiles)
18. `user_sessions` (UUID PK, refresh token rotation records)
19. `users` (UUID PK, Argon2id password hash, role ACL)
20. `webhook_events` (UUID PK, idempotent webhook logs)

---

## 4. PostgreSQL Integration Test Results

Module: `backend/tests/test_postgres_integration.py`  
Execution Command: `pytest tests/test_postgres_integration.py -v`  
Status: **15 passed, 0 skipped, 0 failed in 2.92s**

### 4.1 Outcomes of the 6 Previously Skipped Tests

| Previously Skipped Test | Verification Target | Live PostgreSQL Outcome |
|:---|:---|:---:|
| `test_live_postgres_auth_and_session_persistence` | Argon2id citizen creation, SHA-256 password reset tokens, sessions with refresh token hashing, and account deletion requests | **PASSED** |
| `test_concurrent_monthly_quota_record_initialization` | 5 concurrent threads initializing monthly quota ledger for same user; verifies `SELECT FOR UPDATE` and unique constraints | **PASSED** |
| `test_concurrent_document_quota_reservations_respect_limit` | 5 concurrent threads competing for final quota slot; exactly 1 succeeds, 4 receive `BLOCKED_QUOTA` (403) | **PASSED** |
| `test_concurrent_document_retry_requests` | Row-level locking during `DocumentService.retry_ocr()`; exactly 1 worker acquires lease, 4 competitors receive 409 Conflict | **PASSED** |
| `test_live_postgres_lease_renewal_vs_stale_recovery` | Auto-healing on live PostgreSQL: active lease preserved, expired lease cleared and transitioned to `OCR_FAILED` | **PASSED** |
| `test_live_postgres_old_worker_finalization_after_token_invalidation` | Zombie worker attempting finalization with revoked token rejected; prevents illegitimate quota deduction | **PASSED** |

### 4.2 Outcomes of Dialect & Additional Concurrency Tests

| Test Name | Verification Target | Live PostgreSQL Outcome |
|:---|:---|:---:|
| `test_all_models_compile_for_postgresql` | DDL compilation for all 18 ORM models using PostgreSQL dialect | **PASSED** |
| `test_postgresql_uuid_and_jsonb_types` | Validates native PostgreSQL UUID and JSONB column types | **PASSED** |
| `test_postgresql_foreign_key_cascades` | Validates `ON DELETE CASCADE` foreign key compilation | **PASSED** |
| `test_postgresql_users_email_password_ddl` | Validates `password_hash` and `email` column definitions | **PASSED** |
| `test_postgresql_payment_and_quota_ledger_ddl` | Validates payment numeric types, refund JSONB, and lease columns | **PASSED** |
| `test_concurrent_reminder_claiming_skip_locked_postgres` *(New)* | Multi-worker reminder claiming with `SELECT ... FOR UPDATE SKIP LOCKED`: 5 concurrent workers race; exactly 1 acquires lease, 4 skip | **PASSED** |
| `test_live_postgres_reminder_lease_expiry_and_recovery` *(New)* | Expired reminder lease from crashed worker successfully reclaimed by new worker on PostgreSQL | **PASSED** |
| `test_live_postgres_reminder_retry_exhaustion_and_idempotency` *(New)* | Terminal retry backoff on PostgreSQL: reminder with `retry_count >= 3` is rejected from claim | **PASSED** |
| `test_live_postgres_transaction_rollback_safety` *(New)* | Transaction rollback verification: uncommitted inserts are cleanly discarded | **PASSED** |

---

## 5. Full Backend Regression Results

Execution Command: `pytest tests` (with `$env:TEST_POSTGRES_URL` enabled)  
Test Duration: **86.61s (0:01:26)**  
Total Test Items: **284**  
- **Passed:** **284**
- **Failed:** **0**
- **Skipped:** **0**

```
tests\test_admin.py .............                                        [  4%]
tests\test_advisory.py .................                                 [ 10%]
tests\test_applications.py ............................................. [ 26%]
..............                                                           [ 31%]
tests\test_assistance.py .........                                       [ 34%]
tests\test_auth.py ............................                          [ 44%]
tests\test_database.py ............                                      [ 48%]
tests\test_documents.py ...................                              [ 55%]
tests\test_end_to_end_integration.py .....                               [ 57%]
tests\test_health.py ..                                                  [ 57%]
tests\test_notifications.py .......                                      [ 60%]
tests\test_payments_and_subscriptions.py ............................... [ 71%]
.                                                                        [ 71%]
tests\test_phase_9_subscriptions.py ......................               [ 79%]
tests\test_postgres_integration.py ...............                       [ 84%]
tests\test_rate_limiter.py .....                                         [ 86%]
tests\test_reminder_scheduler_idempotency.py .....                       [ 88%]
tests\test_schemes.py .............................                      [ 98%]
tests\test_users.py .....                                                [100%]
================= 284 passed, 2 warnings in 86.61s (0:01:26) ==================
```

---

## 6. Bugs Discovered & Resolved

1. **Driver Interoperability (`psycopg2-binary` vs `psycopg3`):**
   - *Problem:* `psycopg` (v3) was installed in `backend/venv`, but standard SQLAlchemy connection URLs defaulting to `postgresql://` expected `psycopg2`.
   - *Resolution:* Installed `psycopg2-binary-2.9.13` into `backend/venv`. The test harness supports both `postgresql+psycopg://` (psycopg3) and `postgresql://` (psycopg2) natively.
2. **Deterministic Token Entropy in Live Persistence Tests:**
   - *Problem:* `test_live_postgres_auth_and_session_persistence` used a static string for `PasswordResetToken`, which caused a PostgreSQL unique key violation (`ix_password_reset_tokens_token_hash`) on repeat test runs.
   - *Resolution:* Updated token generation to use dynamic UUID entropy (`f"test_reset_token_{uuid.uuid4().hex}"`), guaranteeing repeatability across test executions.
3. **Strict Model Constraint Compliance in Scheme Creation:**
   - *Problem:* The `schemes` table in PostgreSQL enforces NOT NULL constraints on `eligibility_summary`, `official_source_url`, and `official_application_url`, and defines `state_applicability` instead of `state`.
   - *Resolution:* Fixed test fixtures in `backend/tests/test_postgres_integration.py` to supply valid constraint data matching the Alembic schema.

---

## 7. Container Lifecycle & Cleanup Instructions

To maintain reproducible test runs or clean up after local testing:
- **Stop test container:** `docker stop janmitra_postgres_test_ci`
- **Restart test container:** `docker start janmitra_postgres_test_ci`
- **Tear down test container:** `docker rm -f janmitra_postgres_test_ci`

