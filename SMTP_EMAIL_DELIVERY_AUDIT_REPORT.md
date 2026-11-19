# JanMitra Assist – SMTP Email Delivery End-to-End Audit Report

**Project Title:** JanMitra Assist – AI-Powered Government Service Eligibility and Document Intelligence System  
**Audit Scope:** Password Recovery Email Delivery, SMTP Service Implementation, Token Security, and Local/External Delivery Verification  
**Date:** November 3, 2026  
**Status:** **PASSED (Local SMTP Socket Delivery & Fallback Verified, 33/33 Auth Tests, 289/289 Full Regression Suite)**

---

## 1. Executive Summary

A comprehensive technical audit and verification of the JanMitra Assist password recovery email dispatch architecture was conducted. The system was evaluated against enterprise security standards, including RFC 5321 SMTP delivery, cryptographic token handling, anti-enumeration mitigations, sliding-window rate limiting, and session revocation.

All **15 audit objectives** have been satisfied:
1. **Cryptographic Token Integrity:** Single-use password reset tokens are generated using 32 bytes of cryptographic randomness, hashed exclusively using SHA-256 (`ix_password_reset_tokens_token_hash`), and expire strictly after 15 minutes. Raw tokens are never persisted in the database.
2. **Session Invalidation:** Successful password reset triggers immediate revocation of all active refresh sessions (`is_revoked = True`), mitigating session hijacking.
3. **Anti-Enumeration & Anti-Brute-Force:** `/forgot-password` returns an identical generic response whether an account exists or not, and is protected by sliding-window rate limiters per email and per client IP.
4. **Zero Plaintext OTPs:** The system strictly uses secure deep-link tokens (`/reset-password?token=<hex>`). Legacy OTPs have been completely eliminated.
5. **SMTP Delivery & DevMailbox Fallback:** Wire-level SMTP socket delivery was verified using an isolated local TCP SMTP test server, confirming RFC 5321 exchange, base64 UTF-8 MIME multi-part encoding, and `smtp_success` status. When SMTP daemons are offline, `EmailService` safely falls back to `DevMailbox` without uncaught exceptions or leaking secrets.
6. **External SMTP Status:** External production SMTP delivery (e.g. AWS SES / SendGrid) is **unconfigured and unverified** in this local environment; credentials must be provisioned during production deployment.

---

## 2. Files Inspected and Modified

### 2.1 Files Inspected
- [`backend/app/services/email_service.py`](file:///c:/Users/ravij/OneDrive/Desktop/Janmitra/backend/app/services/email_service.py): Checked `EmailService`, `DevMailbox`, HTML/plaintext templates, SSL/TLS branching, and email address masking.
- [`backend/app/api/v1/endpoints/auth.py`](file:///c:/Users/ravij/OneDrive/Desktop/Janmitra/backend/app/api/v1/endpoints/auth.py): Inspected `/forgot-password` and `/reset-password` endpoint definitions.
- [`backend/app/services/auth_service.py`](file:///c:/Users/ravij/OneDrive/Desktop/Janmitra/backend/app/services/auth_service.py): Inspected rate limiting, user lookup, generic response formatting, token creation, password hashing, and session revocation.
- [`backend/app/models/password_reset.py`](file:///c:/Users/ravij/OneDrive/Desktop/Janmitra/backend/app/models/password_reset.py): Verified table schema, indexing, and `__repr__` exclusion of token hashes.
- [`backend/app/core/config.py`](file:///c:/Users/ravij/OneDrive/Desktop/Janmitra/backend/app/core/config.py): Verified environment variable definitions for `SMTP_*` and token expiration settings.
- [`backend/.env.example`](file:///c:/Users/ravij/OneDrive/Desktop/Janmitra/backend/.env.example) & [`.gitignore`](file:///c:/Users/ravij/OneDrive/Desktop/Janmitra/.gitignore): Verified credential hygiene and git exclusion rules.

### 2.2 Files Modified
- [`backend/tests/test_auth.py`](file:///c:/Users/ravij/OneDrive/Desktop/Janmitra/backend/tests/test_auth.py): Added 5 comprehensive automated tests:
  1. `test_forgot_password_rate_limiting_triggers_429`
  2. `test_reset_token_expiration_after_15_minutes`
  3. `test_reset_token_hashed_in_database_and_raw_token_never_persisted`
  4. `test_live_network_smtp_socket_delivery_and_mime_structure`
  5. `test_smtp_network_failure_clean_fallback_to_dev_mailbox`
- [`RUNNING_GUIDE.md`](file:///c:/Users/ravij/OneDrive/Desktop/Janmitra/RUNNING_GUIDE.md): Added Section 6.A.2 with complete Mailpit setup, live TCP test execution, and DevMailbox fallback operational documentation.

---

## 3. SMTP Configuration Details (Without Secrets)

Configuration parameters are loaded exclusively from OS environment variables via Pydantic `BaseSettings`:

| Parameter | Default Value | Production Override Target | Purpose |
|:---|:---|:---|:---|
| `SMTP_HOST` | `"localhost"` | e.g. `email-smtp.us-east-1.amazonaws.com` | Hostname of SMTP relay server |
| `SMTP_PORT` | `1025` | `587` (STARTTLS) or `465` (SSL) | Listening port on SMTP server |
| `SMTP_USER` | `None` (Blank in `.env.example`) | Production SMTP username | SMTP authentication identity |
| `SMTP_PASSWORD` | `None` (Blank in `.env.example`) | Production SMTP secret key | SMTP authentication credential |
| `SMTP_FROM_EMAIL` | `"noreply@janmitra.gov.in"` | Authorized sender address | Sender address in `From:` header |
| `SMTP_FROM_NAME` | `"JanMitra Assist"` | Service brand name | Display name in `From:` header |
| `SMTP_USE_TLS` | `False` | `True` | Upgrades plain TCP to TLS via `STARTTLS` |
| `SMTP_USE_SSL` | `False` | `False` (or `True` if using port 465) | Direct TLS wrapper (`smtplib.SMTP_SSL`) |
| `FRONTEND_BASE_URL` | `"http://localhost:3000"` | Citizen web/app base URL | Domain for password reset deep links |
| `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES` | `15` | `15` | Expiration window for password reset tokens |

### Security & Sanitization Verification
- **Timeout Protection:** Network socket timeout is pinned to `4.0` seconds to prevent worker thread starvation if SMTP hangs.
- **Exception Sanitization:** SMTP exceptions are logged as `{type(e).__name__}` only (e.g. `SMTPConnectError`). Error strings, socket dumps, and credentials are never printed.
- **PII Masking:** Recipient email addresses are masked in application logs (e.g., `ci***t@janmitra.internal`).

---

## 4. Password Recovery Security Verification

```mermaid
sequenceDiagram
    autonumber
    actor Citizen as Citizen / Client
    participant API as FastAPI /api/v1/auth
    participant AuthSvc as AuthService
    participant Limiter as InMemoryRateLimiter
    participant DB as Database (PostgreSQL)
    participant Mail as EmailService
    participant SMTP as SMTP Relay / Mailpit

    Citizen->>API: POST /forgot-password {email}
    API->>AuthSvc: forgot_password(email, client_ip)
    AuthSvc->>Limiter: check_rate_limit("forgot_password", email)
    alt Rate Limit Exceeded
        Limiter-->>Citizen: 429 Too Many Requests (Retry-After)
    else Under Limit
        AuthSvc->>DB: Query User by email
        alt User Not Found
            AuthSvc-->>Citizen: 200 OK (Generic anti-enumeration message)
        else User Active
            AuthSvc->>DB: Invalidate prior unused tokens (is_used=True)
            AuthSvc->>AuthSvc: Generate raw_token (32 random bytes)
            AuthSvc->>AuthSvc: Compute token_hash = SHA256(raw_token)
            AuthSvc->>DB: Store token_hash, expires_at (now + 15m)
            AuthSvc->>Mail: send_password_reset_email(email, link)
            alt SMTP Online
                Mail->>SMTP: Connect socket, HELO, AUTH, DATA
                SMTP-->>Mail: 250 OK: queued
            else SMTP Offline
                Mail->>Mail: Fallback to DevMailbox
            end
            AuthSvc-->>Citizen: 200 OK (Generic anti-enumeration message)
        end
    end

    Citizen->>API: POST /reset-password {token, new_password}
    API->>AuthSvc: reset_password(token, new_password)
    AuthSvc->>AuthSvc: Compute token_hash = SHA256(token)
    AuthSvc->>DB: Query PasswordResetToken where token_hash & is_used=False
    alt Token Invalid or Expired
        AuthSvc-->>Citizen: 400 Bad Request ("invalid or has expired")
    else Token Valid
        AuthSvc->>AuthSvc: Hash new_password (Argon2id)
        AuthSvc->>DB: Update user.password_hash
        AuthSvc->>DB: Mark token.is_used = True, used_at = now
        AuthSvc->>DB: Invalidate all active UserSessions (is_revoked = True)
        AuthSvc-->>Citizen: 200 OK ("Password successfully updated")
    end
```

### Verification Evidence Matrix

| Security Control | Implementation Mechanism | Verification Result |
|:---|:---|:---:|
| **Zero OTPs** | Only cryptographically random tokens (`raw_token`) are used | **CONFIRMED** |
| **Hashed Storage** | Database stores exclusively `token_hash = SHA256(raw_token)` | **CONFIRMED** |
| **Single-Use** | Token marked `is_used = True` upon consumption; reuse rejected with 400 | **CONFIRMED** |
| **15-Minute Expiry** | `expires_at` enforced; expired token rejected with 400 | **CONFIRMED** |
| **Session Revocation** | `AuthService.revoke_session(all_sessions=True)` invalidates all refresh tokens | **CONFIRMED** |
| **Anti-Enumeration** | Uniform 200 response returned regardless of account existence | **CONFIRMED** |
| **Rate Limiting** | Sliding-window limiter triggers 429 when max attempts exceeded | **CONFIRMED** |
| **No Log Leaks** | Raw token, password, and SMTP secrets absent from logs and `__repr__` | **CONFIRMED** |

---

## 5. Local SMTP Socket Testing vs External Delivery

### 5.1 Local Network Socket SMTP Testing (Verified)
- **Mechanism:** Initialized an RFC 5321 compliant local TCP socket listener on `127.0.0.1`.
- **Protocol Flow:** Handled `220 Ready`, `EHLO`, `MAIL FROM:<noreply@janmitra.gov.in>`, `RCPT TO:<citizen.verified@janmitra.internal>`, `DATA`, and `QUIT`.
- **Payload Inspection:** Successfully parsed received data using `email.message_from_string()`. Confirmed base64-encoded UTF-8 `multipart/alternative` structure containing:
  - Subject: `[JanMitra Assist API] Password Reset Instructions`
  - Plain-text part with reset URL and 15-minute expiration notice.
  - Styled HTML part with accessible reset button and security advisory.
- **Delivery Mode:** `DevMailbox` recorded `delivery_mode: "smtp_success"`.

### 5.2 Mailpit Testing (Documented)
- Mailpit is documented as the recommended local GUI email inspector for developers.
- Docker execution command: `docker run -d --name janmitra_mailpit -p 127.0.0.1:1025:1025 -p 127.0.0.1:8025:8025 axllent/mailpit`.
- When active on port 1025, `EmailService` automatically routes through Mailpit without code changes.

### 5.3 External SMTP Delivery Status (Unconfigured & Unverified)
> [!IMPORTANT]
> **External SMTP Delivery Status: UNCONFIGURED / NOT APPLICABLE IN LOCAL ENVIRONMENT**
> 
> Production SMTP relay credentials (such as AWS SES, SendGrid, or Google Workspace SMTP relay) are **not configured** in this local repository environment. No external network emails were transmitted to the public internet during this audit.
>
> External SMTP delivery must be verified independently in a staging/production environment after supplying production DNS records (SPF, DKIM, DMARC) and secure cloud SMTP credentials.

---

## 6. Backend Test Results

### 6.1 Authentication Module Tests (`tests/test_auth.py`)
```powershell
pytest tests/test_auth.py -v
```
- **Total Tests:** 33
- **Passed:** 33
- **Failed:** 0
- **Skipped:** 0
- **Duration:** 29.25s

Key tests executed:
- `test_forgot_password_generic_response_nonexistent_email` (PASSED)
- `test_forgot_password_and_successful_reset_flow` (PASSED)
- `test_reset_password_invalid_token` (PASSED)
- `test_reset_password_revokes_previous_refresh_sessions` (PASSED)
- `test_forgot_password_rate_limiting_triggers_429` (PASSED)
- `test_reset_token_expiration_after_15_minutes` (PASSED)
- `test_reset_token_hashed_in_database_and_raw_token_never_persisted` (PASSED)
- `test_live_network_smtp_socket_delivery_and_mime_structure` (PASSED)
- `test_smtp_network_failure_clean_fallback_to_dev_mailbox` (PASSED)

### 6.2 Full Backend Regression Suite
```powershell
pytest tests
```
- **Total Tests:** 289
- **Passed:** 289
- **Failed:** 0
- **Skipped:** 0
- **Duration:** 74.46s (0:01:14)

---

## 7. Remaining Limitations & Operational Recommendations

1. **In-Memory Rate Limiting Scope:**
   - The current `InMemoryRateLimiter` provides thread-safe brute-force protection within a single FastAPI process (sufficient for local execution, viva demonstration, and development).
   - In a multi-worker production cluster (e.g. multiple Gunicorn/Uvicorn workers behind Nginx), a Redis-backed token bucket limiter should be swapped in to share attempt counters across worker instances.
2. **Production DNS Records:**
   - Real email deliverability to external citizen inboxes (Gmail, Yahoo, Outlook) requires configuring domain SPF records (`v=spf1 include:... ~all`), DKIM public keys, and DMARC policies for `janmitra.gov.in` (or the production domain) on the DNS registrar.
3. **Frontend Hostname Sync:**
   - `FRONTEND_BASE_URL` in `backend/.env` must match the actual citizen web portal or mobile deep link hostname (e.g. `http://127.0.0.1:8080/#/reset-password` for Flutter Web, or `https://app.janmitra.org/reset-password` in production).

---

## 8. Exact Verification Commands

### Run Authentication & Password Reset Tests
```powershell
cd c:\Users\ravij\OneDrive\Desktop\Janmitra\backend
.\venv\Scripts\pytest tests/test_auth.py -v
```

### Run Wire-Level Local SMTP Socket Delivery Verification
```powershell
cd c:\Users\ravij\OneDrive\Desktop\Janmitra\backend
.\venv\Scripts\python ..\scratch\test_local_smtp_server.py
```

### Run Full 289-Test Backend Regression Suite
```powershell
cd c:\Users\ravij\OneDrive\Desktop\Janmitra\backend
$env:TEST_POSTGRES_URL="postgresql+psycopg://janmitra_test_user:janmitra_test_password_2026@127.0.0.1:5432/janmitra_test_db"
.\venv\Scripts\pytest tests
```

