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
   - Approved pricing tiers:
     - Premium Monthly: ₹99 / month
     - Premium Yearly: ₹799 / year

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
& .\backend\venv\Scripts\pytest.exe .\backend\tests -v
```
Executes 30 comprehensive unit and integration tests covering:
- Metadata table registrations for all domain entities
- Column constraints, UUID types, and JSONB schemas
- OTP challenge generation, rate limiting, and verification
- Citizen registration, login, and non-elevation security
- JWT token issuing, expiry, and refresh token rotation
- Logout and session revocation
- Profile creation, updating, retrieval, and isolation
- Account deletion requests with 30-day retention
- Health check endpoints and safe error handling

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
All 3 widget tests pass:
- App launch & splash screen verification
- Citizen sign-in & validation UI
- Home screen citizen status & navigation

### 9.4 Running Flutter Static Analysis
```powershell
cd mobile_app
..\flutter\bin\flutter.bat analyze
```
Verified **0 issues found**.

---

## 10. Common Troubleshooting

### 1. `OperationalError: connection to server at "localhost", port 5432 failed`
- **Cause:** PostgreSQL service is stopped or port 5432 is not listening.
- **Fix:** Open Windows Services (`services.msc`), locate `postgresql-x64-16`, and click **Start**.

### 2. `password authentication failed for user "postgres"`
- **Cause:** The password in `backend/.env` does not match the password specified during PostgreSQL installation.
- **Fix:** Update `POSTGRES_PASSWORD` in `backend/.env` with your configured password.

### 3. `database "janmitra_db" does not exist`
- **Fix:** Create the database using `psql -U postgres -c "CREATE DATABASE janmitra_db;"`.
