# JanMitra Assist

**AI-Powered Government Service Eligibility and Document Intelligence System**  
*MCA Major Project*

---

## 1. Project Overview

**JanMitra Assist** is a citizen-focused platform developed to bridge the information and readiness gap between citizens and government welfare schemes. The system assists users in:

- **Discovering relevant government schemes** based on profile and demographic parameters.
- **Understanding likely eligibility** before initiating lengthy official application procedures.
- **Uploading and analyzing required documents** with on-device OCR and AI-assisted extraction.
- **Identifying missing, expired, or inconsistent documents** across scheme requirements.
- **Receiving AI-powered guidance** to resolve documentation mismatches.
- **Preparing application readiness reports and checklists**.
- **Accessing official government application portals** directly to complete official submissions.

> **Important Note:** JanMitra Assist **does not replace official government portals**. Citizens submit and finalize their applications on official government websites or through designated state/central touchpoints. Assessment results and readiness scores are strictly advisory evaluations.

---

## 2. Approved Technology Stack

| Layer | Approved Technology | Purpose / Role |
| :--- | :--- | :--- |
| **Mobile App** | **Flutter (Dart)** | Citizen-facing mobile client (Android target) |
| **Backend** | **Python FastAPI** | High-performance asynchronous REST API |
| **Database** | **PostgreSQL** | Relational data store for schemes, users, and audit logs |
| **ORM** | **SQLAlchemy 2.x** | Object Relational Mapping with declarative models |
| **PostgreSQL Driver** | **Psycopg 3 (`psycopg[binary]`)** | Modern PostgreSQL driver for Python |
| **Database Migrations** | **Alembic** | Schema versioning and migration management |
| **Admin Dashboard** | **React.js (Vite)** | Administrator portal for schemes & configuration |
| **OCR Engine** | **Local Tesseract OCR** | Privacy-first local document text extraction (Phase 3) |
| **AI Model Runtime** | **Ollama (Llama 3.2 1B)** | Local lightweight LLM for eligibility guidance (Phase 4) |
| **Push Notifications**| **Firebase Cloud Messaging** | Scheme alerts and status notifications |
| **Payment Gateway** | **Razorpay Test Mode** | Optional document readiness report checkout |
| **Version Control** | **Git** | Source code management across monorepo |

---

## 3. Monorepo Folder Structure

```
Janmitra/
├── .gitignore                    # Monorepo ignore rules (Python, Node, Flutter, backups)
├── README.md                     # Project documentation & run guides
│
├── backend/                      # Python FastAPI REST API
│   ├── alembic/                  # Alembic database migrations
│   │   ├── versions/             # Migration revision scripts
│   │   │   └── e36378f07849_initial_schema_phase_2.py
│   │   ├── env.py                # Alembic runtime environment (configured for Psycopg 3)
│   │   └── script.py.mako        # Migration template
│   ├── alembic.ini               # Alembic configuration
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       └── api.py        # Central API v1 router
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py         # Pydantic Settings & database environment config
│   │   │   ├── database.py       # SQLAlchemy engine, session lifecycle & health check
│   │   │   └── logging.py        # Safe structured logging configuration
│   │   ├── models/               # Domain SQLAlchemy models (Phase 2)
│   │   │   ├── __init__.py       # Model exports and metadata registration
│   │   │   ├── user.py           # User entity (citizen/admin)
│   │   │   ├── profile.py        # UserProfile entity (demographics, income)
│   │   │   ├── scheme.py         # Scheme repository entity
│   │   │   ├── document.py       # DocumentMetadata entity (metadata only, no blobs)
│   │   │   ├── assessment.py     # Assessment entity (PostgreSQL JSONB advisory)
│   │   │   ├── application.py    # Application entity (manual tracking workflow)
│   │   │   ├── subscription.py   # Subscription entity (free/premium pricing)
│   │   │   └── notification.py   # In-app Notification entity
│   │   ├── __init__.py
│   │   └── main.py               # FastAPI entry point & health check endpoints
│   ├── tests/                    # Pytest test suite
│   │   ├── __init__.py
│   │   ├── test_health.py        # General health check tests
│   │   └── test_database.py      # Database models, schemas & health check tests
│   ├── venv/                     # Python 3.13 virtual environment (gitignored)
│   ├── .env.example              # Environment variables template (no secrets)
│   ├── pytest.ini                # Pytest configuration
│   ├── requirements.txt          # Backend dependencies
│   └── run.py                    # Root script for starting backend locally
│
├── mobile_app/                   # Flutter Citizen Mobile Client
│   ├── android/                  # Android native project files & manifests
│   ├── assets/                   # Images and icons
│   ├── lib/
│   │   ├── core/                 # App constants, civic theme, API routes
│   │   ├── features/             # Feature modules (home, schemes, docs, etc.)
│   │   └── main.dart             # Flutter app entry point
│   ├── test/                     # Widget tests
│   ├── .env.example              # Mobile configuration template
│   ├── pubspec.yaml              # Flutter dependencies and assets config
│   └── README.md                 # Mobile-specific instructions
│
├── admin_dashboard/              # React.js Admin Management Console
│   ├── src/
│   │   ├── components/           # Modular components (Header, Sidebar, Overview)
│   │   ├── App.jsx               # Dashboard layout & view controller
│   │   ├── App.css               # Dashboard styling
│   │   └── main.jsx              # React 18 entry point
│   ├── dist/                     # Verified production build
│   ├── .env.example              # Dashboard environment template
│   ├── package.json              # React dependencies and scripts
│   └── vite.config.js            # Vite build configuration
│
├── docs/                         # Architecture documentation & progress
│   └── IMPLEMENTATION_PROGRESS.md# Phase task tracking & verification results
│
└── backups/                      # Backup storage directories
    ├── database/                 # Database schema and migration dumps
    └── documents/                # Sample sanitized test documents
```

---

## 4. Database Models & Domain Architecture (Phase 2)

All database entities are built using **SQLAlchemy 2.x Declarative Base** with **UUID primary keys** and **PostgreSQL JSONB**:

1. **`User` (`users`)**:
   - Primary citizen / admin account identity.
   - Fields: `id` (UUID PK), `role` (`citizen`/`admin`), `email` (unique, nullable), `mobile_number` (unique, nullable), `is_active`, `created_at`, `updated_at`.
   - *Note: Password authentication is explicitly deferred to later phases.*

2. **`UserProfile` (`user_profiles`)**:
   - Demographic and socioeconomic attributes for eligibility calculation.
   - Fields: `id` (UUID PK), `user_id` (FK to `users.id`, unique, `ondelete="CASCADE"`), `full_name`, `date_of_birth`, `state`, `district`, `residence_type` (`rural`/`urban`), `annual_family_income`, `occupation`, `education_level`.
   - *Privacy Rule: Aadhaar number is strictly excluded from general profile storage.*

3. **`Scheme` (`schemes`)**:
   - Official scheme information repository.
   - Fields: `id` (UUID PK), `scheme_name`, `description`, `department`, `state_applicability`, `eligibility_summary`, `official_source_url`, `official_application_url`, `source_last_verified_at`, `is_active`.
   - Directs citizens to official government portals for final submission.

4. **`DocumentMetadata` (`document_metadata`)**:
   - Metadata tracking uploaded documents without storing binary content in the database.
   - Fields: `id` (UUID PK), `user_id` (FK to `users.id`), `document_type`, `original_filename`, `storage_reference`, `mime_type`, `file_size`, `upload_status`.
   - *Architecture Rule: Binary files are stored exclusively on secure local filesystem/cloud storage, never in PostgreSQL.*

5. **`Assessment` (`assessments`)**:
   - AI and rule-engine advisory evaluation records.
   - Fields: `id` (UUID PK), `user_id` (FK to `users.id`), `scheme_id` (FK to `schemes.id`, nullable), `assessment_type`, `result_data` (PostgreSQL `JSONB`), `overall_readiness_score`.
   - *Advisory Rule: Results are strictly informational and do not represent government decisions.*

6. **`Application` (`applications`)**:
   - Citizen manual tracking for submitted applications.
   - Fields: `id` (UUID PK), `user_id` (FK to `users.id`), `scheme_id` (FK to `schemes.id`), `application_reference_number`, `submission_date`, `status`.
   - Approved tracking statuses: `Submitted`, `Under Review`, `Pending`, `Document Verification`, `Approved`, `Rejected`, `Completed`.

7. **`Subscription` (`subscriptions`)**:
   - Subscription tier and billing records.
   - Fields: `id` (UUID PK), `user_id` (FK to `users.id`), `plan_type` (`free`/`premium`), `billing_cycle` (`monthly`/`yearly`), `status`, `start_date`, `end_date`.
   - Approved pricing tiers & allocations:
     - Free Plan: Up to 3 document analyses/month, 5 personalized AI guidance sessions/month (₹0.00).
     - Premium Monthly: ₹99 / month (up to 30 document analyses/month; proposed safety ceiling of 100 AI guidance sessions/month pending Project Owner confirmation).
     - Premium Yearly: ₹799 / year (up to 30 document analyses/month; proposed safety ceiling of 100 AI guidance sessions/month pending Project Owner confirmation).

8. **`Notification` (`notifications`)**:
   - Citizen in-app deadline reminders, scheme alerts, and status changes.
   - Fields: `id` (UUID PK), `user_id` (FK to `users.id`), `title`, `message`, `notification_type`, `scheduled_at`, `is_read`.

---

## 5. PostgreSQL Installation & Setup Guide

### 5.1 Installing PostgreSQL on Windows

If PostgreSQL is not yet installed on your system:

#### Option A: Windows Package Manager (winget)
Open PowerShell and run:
```powershell
winget install PostgreSQL.PostgreSQL.16
```

#### Option B: Official Windows Installer (Recommended)
1. Download the PostgreSQL 16 Windows Installer from [postgresql.org/download/windows](https://www.postgresql.org/download/windows/).
2. Run the `.exe` installer.
3. When prompted, choose an installation directory (e.g., `C:\Program Files\PostgreSQL\16`).
4. Enter a password for the superuser `postgres` (e.g., `postgres` or your secure local password).
5. Leave the port set to `5432`.
6. Complete the setup wizard.

### 5.2 Creating the Database & User

Open **SQL Shell (psql)** or run from PowerShell:
```powershell
# Connect to PostgreSQL using psql
psql -U postgres -h localhost -p 5432
```

In the PostgreSQL prompt, execute:
```sql
-- Create the JanMitra Assist database
CREATE DATABASE janmitra_db;

-- Verify database creation
\l
```

### 5.3 Configuring Environment Variables

Copy the template to `.env`:
```powershell
Copy-Item backend\.env.example backend\.env
```

Update `backend/.env` with your PostgreSQL password:
```ini
POSTGRES_SERVER="localhost"
POSTGRES_PORT=5432
POSTGRES_USER="postgres"
POSTGRES_PASSWORD="your_actual_password_here"
POSTGRES_DB="janmitra_db"
```

---

## 6. Alembic Database Migration Commands

Alembic is configured to read the connection URL dynamically from `backend/app/core/config.py` using the **Psycopg 3 driver**.

All commands should be executed from the `backend/` directory:

```powershell
Set-Location backend
```

### 6.1 Inspect Pending Migrations (Offline SQL generation)
To view the generated SQL without connecting to a live database:
```powershell
& .\venv\Scripts\alembic.exe upgrade head --sql
```

### 6.2 Apply Migrations to PostgreSQL (Online)
Once PostgreSQL is running:
```powershell
& .\venv\Scripts\alembic.exe upgrade head
```

### 6.3 Check Migration Status
```powershell
& .\venv\Scripts\alembic.exe current
```

### 6.4 Generate Future Migrations (When modifying models)
```powershell
& .\venv\Scripts\alembic.exe revision --autogenerate -m "describe_changes"
```

### 6.5 Rollback Migrations (If required)
```powershell
& .\venv\Scripts\alembic.exe downgrade -1
```

---

## 7. Running & Testing the Backend

### 7.1 Start Backend Server
```powershell
& .\backend\venv\Scripts\python.exe backend\run.py
```

### 7.2 Verify Health Check Endpoints

- **General Health Check:**
  ```powershell
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"
  ```
  Returns `200 OK`:
  ```json
  {
    "status": "healthy",
    "message": "JanMitra Assist backend is running successfully",
    "environment": "development",
    "version": "1.0.0"
  }
  ```

- **Database Connectivity Health Check:**
  ```powershell
  Invoke-RestMethod -Uri "http://127.0.0.1:8000/health/database"
  ```
  - When PostgreSQL is connected: Returns `200 OK` (`{"status": "healthy", "database": "connected"}`).
  - When PostgreSQL is offline: Returns `503 Service Unavailable` (`{"status": "unhealthy", "database": "disconnected"}`) without leaking secrets.

- **Interactive API Documentation (Swagger):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 7.3 Run All Automated Tests
```powershell
& .\backend\venv\Scripts\pytest.exe .\backend\tests -v -rs --ignore=backend/tests/test_browser_e2e_real.py
```
Executes comprehensive regression suite across 21 test modules (301 passed, 10 skipped pending Docker daemon, 0 failed):
- Metadata table registrations for all domain entities
- Column constraints, UUID types, and JSONB schemas
- Dual-mode authentication (Argon2id, HttpOnly Cookies, CSRF tokens, Bearer tokens)
- Password reset token generation, single-use hashing, and expiry
- Citizen registration, login, and non-elevation security
- JWT token issuing, expiry, and refresh token rotation
- Logout, session revocation, and cookie expiration
- Profile creation, updating, retrieval, and isolation
- Scheme discovery, category rules, dynamic document checklists, and provenance
- Document Vault upload, magic byte validation, and OCR intelligence
- AI advisory and multi-dimensional readiness scoring
- Application assistance, manual tracking, and status history
- Subscription tiers, quota reservations, and Razorpay HMAC webhooks
- Distributed reminder dispatch with row leasing and idempotency
- Rate limiting, health check endpoints, and safe error handling

---

## 8. Authentication & User Management (Phase 3)

### 8.1 Authentication Architecture & Flow

JanMitra Assist implements a **mobile number OTP-based authentication architecture** tailored for Indian citizens:

1. **OTP Challenge (`POST /api/v1/auth/send-otp`)**:
   - Accepts 10-digit Indian mobile number (`+91` or 10 digits).
   - Generates cryptographically secure 6-digit numeric OTP.
   - Stores SHA-256 hash in `otp_challenges` with 5-minute expiry.
   - Enforces a 60-second resend cooldown and 5-attempt brute-force limit.
   - **Modular SMS Adapter**: Uses `DevelopmentSMSAdapter` locally (logs OTP and returns `dev_otp` in development mode) to eliminate SMS fees during testing, while `ProductionSMSAdapter` is ready for external SMS gateways.

2. **OTP Verification & Citizen Provisioning (`POST /api/v1/auth/verify-otp`)**:
   - Verifies OTP challenge.
   - If user does not exist: automatically provisions a new `User` with role `citizen`.
   - If user already exists: verifies identity and prevents duplicate user creation.
   - Issues short-lived JWT access token (30 minutes) and 256-bit cryptographically random refresh token (30 days).
   - Stores SHA-256 hash of refresh token in `user_sessions`.

3. **Secure Refresh Token Rotation (`POST /api/v1/auth/refresh`)**:
   - Accepts raw refresh token.
   - Verifies hash against active `user_sessions`.
   - **Rotation:** Immediately revokes previous refresh token and issues a fresh pair.
   - Prevents replay attacks and persistent token hijacking.

4. **Session Revocation & Logout (`POST /api/v1/auth/logout`)**:
   - Invalidates active refresh token (or all sessions for the user).
   - Clears credentials from local storage.

5. **Citizen Profile Lifecycle (`/api/v1/users/me/profile`)**:
   - `GET`: Fetches authenticated citizen's demographic details.
   - `PUT`: Creates or updates profile (Full Name, Date of Birth, State, District, Residence Type, Income, Occupation, Education).
   - `PATCH`: Partial profile updates.
   - `DELETE`: Clears profile without deleting the user account.
   - **Privacy Rule:** Aadhaar numbers are strictly excluded from registration, schemas, and storage.

6. **Account Deletion Request (`POST /api/v1/users/me/delete-request`)**:
   - Initiates a scheduled 30-day retention countdown.
   - Immediately deactivates account (`is_active = False`) and revokes all active sessions.

### 8.2 Phase 3 API Endpoint Reference

| Method | Endpoint | Auth Required | Description |
| :--- | :--- | :---: | :--- |
| `POST` | `/api/v1/auth/send-otp` | No | Request 6-digit OTP challenge for mobile number |
| `POST` | `/api/v1/auth/verify-otp` | No | Verify OTP, provision citizen, return JWT tokens |
| `POST` | `/api/v1/auth/refresh` | No | Rotate refresh token and issue new token pair |
| `POST` | `/api/v1/auth/logout` | Bearer JWT | Revoke active session(s) and sign out |
| `GET` | `/api/v1/auth/me` | Bearer JWT | Retrieve authenticated citizen identity |
| `GET` | `/api/v1/users/me` | Bearer JWT | Retrieve user identity and profile summary |
| `GET` | `/api/v1/users/me/profile` | Bearer JWT | Retrieve citizen profile details |
| `PUT` | `/api/v1/users/me/profile` | Bearer JWT | Create or replace citizen profile |
| `PATCH` | `/api/v1/users/me/profile` | Bearer JWT | Partial update of citizen profile |
| `DELETE` | `/api/v1/users/me/profile` | Bearer JWT | Clear citizen profile |
| `POST` | `/api/v1/users/me/delete-request` | Bearer JWT | Request account deletion (30-day retention) |

---

## 9. Flutter Mobile Application (Phase 3)

### 9.1 Secure Storage Architecture
- In strict adherence to mobile security best practices, JWT access and refresh tokens are **never stored in SharedPreferences**.
- All tokens, keys, and session metadata are persisted using **`FlutterSecureStorage`** backed by Android Keystore and iOS Keychain.

### 9.2 Mobile Screen Workflows
1. **`SplashScreen`**: Checks persistent session; auto-routes to `HomeScreen` if token valid or `LoginScreen` if expired.
2. **`LoginScreen`**: Input validation for 10-digit Indian numbers (`+91`), request OTP challenge.
3. **`OTPVerificationScreen`**: 6-digit entry with resend cooldown countdown and dev-mode autofill support.
4. **`ProfileSetupScreen`**: Form to complete required and optional citizen demographics with clear Aadhaar exclusion notice.
5. **`HomeScreen`**: Displays citizen verification badge, profile completion status chip, quick profile access, and sign-out.
6. **`ProfileViewScreen`**: View and edit citizen details.
7. **`AccountDeletionDialog`**: Confirmation dialog explaining the 30-day data retention period.

### 9.3 Running Flutter Tests
```powershell
cd mobile_app
..\flutter\bin\flutter.bat test
```
All 151 widget and unit tests pass cleanly:
- Citizen authentication, registration, password reset UI & validation
- App launch, splash screen, and navigation routing
- Home screen civic status, profile view, and edit forms
- Scheme discovery, sector category filtering, and detail cards
- Deterministic eligibility evaluation & statutory advisory disclaimers
- Dynamic category rules and category-specific document requirements
- Document Vault upload, file validation, and checklist widgets
- All 8 statutory document guides (Maharashtra, Gujarat, UP, All India)
- Application assistance step checklist & manual application tracking
- Notification inbox & push notification preference handling
- Subscription tiers, quota indicators, and Razorpay checkout adapters

### 9.4 Running Flutter Static Analysis
```powershell
cd mobile_app
..\flutter\bin\flutter.bat analyze
```
Verified **0 issues found**.

---

## 10. Phase 4: Government Scheme Discovery & Eligibility Engine

### 10.1 Deterministic Eligibility Engine
The core rule evaluation engine (`EligibilityEngine` in `backend/app/services/eligibility_service.py`) deterministically checks citizen profile attributes against structured rule conditions:
- **Supported Comparison Operators:** `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `in`, `contains`.
- **Dynamic Age Calculation:** Derived dynamically from citizen `date_of_birth` taking leap years and exact birthday anniversaries into account.
- **Handling Incomplete Profiles:** If a required fact is absent, the condition is classified as `unknown` (never failed), and the overall determination is set to `Insufficient Information` with actionable guidance on missing fields.
- **Explainable Outcomes:** Detailed condition-by-condition analysis with actual vs expected values and plain-language explanations.
- **Criteria Match Percentage:** Calculated on a 0.0% to 100.0% scale representing the proportion of verified conditions satisfied. It explicitly does **NOT** represent official government approval probability.
- **Mandatory Failure Exclusion:** Any failed mandatory eligibility condition excludes the scheme from recommended matches.
- **Statutory Advisory Disclaimer:** All assessments explicitly state they are advisory only and do not replace official government determinations.

### 10.2 Curated Verified Government Schemes (Demo Data)
Includes 5 seed schemes with authentic nodal links, verified supporting documentation notes (`source_verification_details`), and `is_demo_data=True` flags:
1. **PM-KISAN:** Central sector scheme providing ₹6,000/year to landholding farmer families (`https://pmkisan.gov.in/`).
2. **Ayushman Bharat (AB-PMJAY):** Secondary and tertiary healthcare coverage up to ₹5 Lakh/family/year (`https://pmjay.gov.in/`).
3. **PMAY-G (Gramin):** Rural housing assistance for pucca house construction (`https://pmayg.nic.in/`).
4. **NSP Post-Matric Scholarship:** Higher education scholarship for students with family income <= ₹2.5 Lakh (`https://scholarships.gov.in/`).
5. **Maharashtra MJPJAY:** State health scheme providing cashless hospitalisation up to ₹5 Lakh for ration card holders (`https://www.jeevandayee.gov.in/`).

### 10.3 Phase 4 API Endpoint Reference

| Method | Endpoint | Auth Required | Description |
| :--- | :--- | :---: | :--- |
| `GET` | `/api/v1/schemes` | No | Paginated scheme catalog with `q`, `category`, and `state` filters |
| `GET` | `/api/v1/schemes/categories` | No | Sector categories with active scheme counts |
| `GET` | `/api/v1/schemes/recommendations` | Bearer JWT | Profile-based recommendations with match scores & reasons |
| `GET` | `/api/v1/schemes/{id}` | No | Full scheme details, benefits, criteria, required documents, URLs |
| `POST` | `/api/v1/schemes/{id}/assess` | Bearer JWT | Run deterministic eligibility check and persist record |
| `GET` | `/api/v1/schemes/assessments/history` | Bearer JWT | Paginated history of citizen's past assessments |
| `GET` | `/api/v1/schemes/assessments/{id}` | Bearer JWT | Retrieve past assessment run with user ownership validation |

---

## 11. Phase 5: Document Vault & OCR Pipeline

### 11.1 Secure Document Vault Architecture
- **Binary Segregation:** All uploaded files are stored strictly on local storage disk (`storage/documents/<user_id>/<doc_uuid>.<ext>`) and **NEVER** in PostgreSQL.
- **Opaque Storage References:** Prevents user enumeration, URL guessing, and path leaks.
- **Magic Byte Signature Validation:** Verifies file content headers directly:
  - PDF: `%PDF` (`\x25\x50\x44\x46`)
  - JPEG: `\xff\xd8\xff`
  - PNG: `\x89PNG\r\n\x1a\n`
- **File Constraints:** Validates extensions (`pdf, jpg, jpeg, png`) and enforces max file size (10 MB).
- **IDOR Protection:** All vault endpoints verify authenticated citizen ownership using the JWT Bearer token claims.

### 11.2 Google Cloud Vision OCR & Intelligent Extraction
- **Production Integration:** Uses `google-cloud-vision` (`vision.ImageAnnotatorClient`) for document text and layout recognition when credentials are provided:
  - Supports image files (`JPEG`, `PNG`) using `document_text_detection`.
  - Supports PDFs up to 5 pages synchronously using in-memory bytes via `batch_annotate_files` (eliminating Cloud Storage bucket dependencies for standard documents). Multi-page PDFs beyond 5 pages require asynchronous Cloud Storage batching.
- **Production Safety:** `MockOCRAdapter` is strictly forbidden from running in production (`ENVIRONMENT == 'production'` or `DEBUG is False`). Missing Cloud Vision credentials in production immediately transition status to `OCR_FAILED` with an explicit notice and `manual_review_required = True`.
- **Development / Mock Mode:** High-fidelity simulated extraction generating authentic text for Indian government documents (Income Certificate, Caste Certificate, Domicile, NFSA Ration Card, Aadhaar Card, Land Records). Mock metadata is tagged with `is_mock: True`.
- **Confidence Scoring & Manual Review:**
  - Computes weighted extraction confidence score (0.0 to 1.0).
  - Scores below threshold (0.70) or blurred/unreadable scans automatically set `ocr_status = MANUAL_REVIEW_REQUIRED` and flag `manual_review_required = True`.
- **Sensitive Data & Header Protection:**
  - Full OCR text is completely excluded from application log streams.
  - OCR failure error messages sanitize local system paths (`C:\Users\...`).
  - Downloads use sanitized headers with `X-Content-Type-Options: nosniff` and strip CRLF/quotes to prevent HTTP response splitting.
- **Retry Processing:** Citizens can re-trigger OCR extraction on any uploaded document (`POST /api/v1/documents/{id}/retry-ocr`). Rejects duplicate requests with `409 Conflict` if processing is already underway.
- **Terminology & Governance:** Clearly distinguishes *Document Uploaded*, *OCR Completed / Text Extracted*, *Manual Review Required*, and *Official Government Verification*. OCR completion verifies machine text extraction only and never guarantees authenticity or government eligibility.

### 11.3 Phase 5 API Endpoint Reference

| Method | Endpoint | Auth Required | Description |
| :--- | :--- | :---: | :--- |
| `POST` | `/api/v1/documents/upload` | Bearer JWT | Upload document (PDF/JPG/PNG), validate magic bytes, store, and run OCR |
| `GET` | `/api/v1/documents` | Bearer JWT | List citizen's vault documents with optional `document_type` and `ocr_status` filters |
| `GET` | `/api/v1/documents/{id}` | Bearer JWT | Retrieve document metadata, OCR text, confidence, and review status |
| `GET` | `/api/v1/documents/{id}/download` | Bearer JWT | Stream binary file with appropriate MIME type headers |
| `DELETE` | `/api/v1/documents/{id}` | Bearer JWT | Permanently delete document file from disk and remove metadata record |
| `POST` | `/api/v1/documents/{id}/retry-ocr` | Bearer JWT | Re-run OCR processing on existing document file |
| `GET` | `/api/v1/documents/scheme/{scheme_id}/checklist` | Bearer JWT | Check scheme required documents against citizen vault with readiness status |

---

## 12. Phase 6: AI Advisory & Readiness Assessment Engine

### 12.1 Separation of Deterministic Assessment from LLM Reasoning
- **Deterministic Rule Engine (Phase 4):** Evaluates profile demographic facts against statutory conditions and produces the authoritative outcome (`Potentially Eligible`, `Not Eligible Based on Available Information`, `Insufficient Information`) and `Criteria Match Percentage`. The LLM **never overrides** this determination.
- **AI Advisory Engine (Phase 6):** Explains the assessment outcome in citizen-friendly language, explains matched vs unmatched conditions, identifies missing profile and document items, highlights potential name/DOB discrepancies, and outlines actionable preparation steps based on retrieved official guidelines.

### 12.2 RAG Knowledge Retrieval Pipeline
- **Ingestion & Seeding:** Official scheme clauses ingested into `scheme_knowledge_chunks` with metadata (`source_url`, `source_reference`, `source_freshness_status`, `is_demo_data`).
- **Retrieval:** Token-overlap keyword and category ranking retrieves the top-3 most relevant clauses for the evaluated scheme.
- **Factual Grounding:** All claims cite verified nodal sources; prevents hallucination of benefits, income ceilings, age limits, or URLs.

### 12.3 Cloud LLM Provider Adapter & Production Safety
- **Modular Adapter Architecture:** Supports Google Gemini (`GeminiLLMAdapter` via `httpx`) and high-fidelity local simulation (`MockLLMAdapter`).
- **Strict Production Safety:** In production (`ENVIRONMENT == 'production'` or `DEBUG is False`), `MockLLMAdapter` cannot run. Missing API keys or cloud failures return explicit error states rather than silent fallback.
- **Multilingual Support:** Delivers tailored guidance in **English (`en`)**, **Hindi (`hi`)**, and **Gujarati (`gu`)** while preserving official scheme names and document nomenclature.

### 12.4 AI Safety, Prompt Injection Defense & Privacy
- **Prompt Injection Neutralization:** Untrusted inputs (OCR text, retrieved content) are strictly isolated inside XML-like tags (`<citizen_ocr_data>`, `<retrieved_scheme_knowledge>`) with explicit system rules instructing the LLM to treat them as passive data.
- **PII Minimization:** Aadhaar numbers are automatically masked (`XXXX-XXXX-1234`) and phone numbers masked (`XXXXXXX210`) before sending prompts.
- **Log Sanitation:** Extracted OCR text and prompt text are completely excluded from application log streams.

### 12.5 Multi-Dimensional Application Readiness Scoring
- **Composite Readiness Score Formula:**
  $$\text{Readiness Score} = 0.40 \times \text{Criteria Match} + 0.30 \times \text{Doc Coverage} + 0.15 \times \text{Completeness} + 0.15 \times \text{Consistency}$$
- **Document Consistency Cross-Validation:** Cross-checks citizen profile name and birth year against OCR text extracted from identity documents in the vault, flagging `Consistent`, `Discrepancy Detected`, or `Review Required`.
- **Statutory Non-Guarantee Disclaimer:** Prominently states that readiness scores and AI guidance are advisory evaluations, not government approval probabilities.

### 12.6 Phase 6 API Endpoint Reference

| Method | Endpoint | Auth Required | Description |
| :--- | :--- | :---: | :--- |
| `POST` | `/api/v1/advisory/schemes/{id}/assess-and-advise` | Bearer JWT | Run deterministic check, readiness scoring, and AI advisory synthesis (`en`, `hi`, `gu`) |
| `GET` | `/api/v1/advisory/assessments/{id}` | Bearer JWT | Retrieve past AI advisory and readiness report with citizen ownership validation |
| `POST` | `/api/v1/advisory/assessments/{id}/regenerate` | Bearer JWT | Re-generate advisory guidance in a different language or refresh with vault docs |

---

## 13. Common Troubleshooting


### 1. `OperationalError: connection to server at "localhost", port 5432 failed`
- **Cause:** PostgreSQL service is stopped or port 5432 is not listening.
- **Fix:** Open Windows Services (`services.msc`), locate `postgresql-x64-16`, and click **Start**.

### 2. `password authentication failed for user "postgres"`
- **Cause:** The password in `backend/.env` does not match the password specified during PostgreSQL installation.
- **Fix:** Update `POSTGRES_PASSWORD` in `backend/.env` with your configured password.

### 3. `database "janmitra_db" does not exist`
- **Fix:** Create the database using `psql -U postgres -c "CREATE DATABASE janmitra_db;"`.

---

## 14. Critical Audit Remediation & Production Security

During the comprehensive system audit and production security phase, JanMitra Assist underwent strict hardening across ten core pillars:

1. **Beneficiary Analytics Data Integrity:**
   - Completely eradicated synthetic, unsupported, and fabricated caste-wise breakdowns across all schemes.
   - Enforced complete provenance metadata: `report_title`, `geographic_scope`, `metric_definition`, `verification_status`.
   - Clear civic disclaimer displayed when caste data is unavailable: *"Caste-wise beneficiary data is not available from the verified official source."*
   - Unpublished and marked unverified datasets (e.g. Post-Matric Scholarship, MJPJAY) as `Pending Verification`.

2. **Category Rules and Eligibility Accuracy:**
   - Audited 17 category rules across PM-KISAN, PM-JAY, PMAY-G, Post-Matric, and MJPJAY.
   - Added `geographic_scope` and `verification_status` to every rule.
   - Marked unsupported/unverified conditions (e.g. MJPJAY SC fast-track) for review (`Review Required`).

3. **Complete Removal of Aadhaar Remnants:**
   - Removed Aadhaar prompts, input fields, and mock selections from Flutter Document Vault, Scheme Management, and Admin forms.
   - Preserved the privacy boundary: JanMitra does not collect, index, or store Aadhaar numbers as profile attributes.

4. **Document Guide Accuracy & Statutory Disclaimers:**
   - Audited all 8 document guides. Added statutory fee disclaimer: *"Fee and processing time may vary by state and application mode. Please confirm on the official state portal."*
   - Separated state application portals for Maharashtra, Gujarat, Uttar Pradesh, and All India.
   - Replaced commercial bank links with RBI Customer Services, DBT Bharat, and India Post Payments Bank.

5. **Secure Browser Authentication & Dual-Mode Auth:**
   - Eliminated sensitive JWT access and refresh token persistence in browser `localStorage`.
   - Implemented HttpOnly, Secure, SameSite=Lax cookies for web clients (React Admin and Flutter Web).
   - Validated CSRF protection via `X-CSRF-Token` header on state-modifying requests (`POST`, `PUT`, `PATCH`, `DELETE`).
   - Mobile clients (Android/iOS) continue using hardware-backed `FlutterSecureStorage` with Bearer tokens.

6. **Docker & Production Hardening:**
   - Added comprehensive `.dockerignore` files for backend and admin dashboard to exclude local caches, virtual environments, node_modules, and secrets.
   - Bound PostgreSQL to `127.0.0.1:5432` to eliminate unintended external public exposure.
   - Configured backend container entrypoint to automatically execute `alembic upgrade head`.
   - Application startup rejects default JWT secrets, default Razorpay credentials, and localhost CORS in production mode.

7. **Database Migrations & Safety:**
   - Preserved active user data, applications, and documents with pre-audit backups.
   - Authored and verified reversible Alembic migration `f8a9b0c1d2e3_add_analytics_provenance_and_rule_verification.py`.

8. **Test Execution & Quality Metrics:**
   - **Backend:** 301 passed, 10 skipped (dedicated live PostgreSQL container offline), 0 failed in 68.63s across 21 test modules.
   - **Flutter:** 151 passed, 0 failed in 41.0s; static analysis: 0 issues (`flutter analyze` clean in 124.2s).
   - **React Admin:** Production Vite build verified (0 errors, 40 modules transformed in 2.31s).
   - **Real Browser E2E:** 100% passed in Headless Google Chrome (`backend/tests/test_browser_e2e_real.py`) with dynamic ephemeral credentials.
   - **API E2E Workflows:** Citizen and Admin end-to-end audit workflows verified 100% (`backend/tests/test_audit_workflows_e2e.py`).
   - **Alembic Reversible Revision Chain:** All 16 linear revisions verified through a complete round-trip (upgrade to head, downgrade to base, re-upgrade to head).
   - **Credential Remediation:** Administrator credentials (`admin@janmitra.internal`) securely rotated with Argon2id; active sessions revoked; zero plaintext credentials stored or logged.
