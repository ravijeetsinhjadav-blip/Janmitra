# JanMitra Assist – Implementation Progress Tracker

**Project Name:** JanMitra Assist – AI-Powered Government Service Eligibility and Document Intelligence System  
**Academic Target:** MCA Major Project  
**Current Phase:** Phase 2 (Database & Backend Foundation)

---

## 1. Environment & Architecture Dependency Audit

| Tool / Technology | Required For | Status on Machine | Detected Version / Path | Action Taken / Status |
| :--- | :--- | :--- | :--- | :--- |
| **Git** | Version Control | **Installed** | `2.53.0.windows.2` | Initialized repo, tracked Phase 1 & 2 files |
| **Python** | Backend API | **Installed** | `3.13.3` (`pip 25.2`) | Virtual environment active at `backend/venv` |
| **SQLAlchemy** | ORM Engine | **Installed** | `2.1.6` | Configured with Base, pooling & lifecycle |
| **Psycopg 3** | PostgreSQL Driver | **Installed** | `3.3.6` (`psycopg-binary 3.3.6`) | Configured via `postgresql+psycopg://` URL |
| **Alembic** | Database Migrations | **Installed** | `1.20.1` | Configured `alembic.ini`, `env.py`, initial revision created |
| **Node.js** | Admin Dashboard | **Installed** | `v24.14.1` | Initialized Vite + React dashboard |
| **npm** | Package Manager | **Installed** | `11.11.0` | React dependencies installed, build verified |
| **PostgreSQL Server** | Relational Database | **Not Running** | Port 5432 closed / not installed | Setup & startup steps provided; graceful fallback verified |
| **Android SDK** | Mobile App Target | **Installed** | `C:\Users\ravij\AppData\Local\Android\Sdk` | Configured in Android manifest & Gradle |
| **Flutter SDK** | Mobile Client | **Not in PATH** | Not detected | Project scaffolded; installation guide documented |
| **Tesseract OCR** | Document OCR | Not installed | Scheduled for Phase 3 | To be set up in Phase 3 |
| **Ollama** | Local LLM Runtime | Not installed | Scheduled for Phase 3 | To be set up in Phase 3 |

---

## 2. Phase 2 Tasks & Status

- [x] **Task 1: Environment & Dependency Inspection**
  - Inspected existing Phase 1 FastAPI backend, virtual environment, and packages.
  - Checked PostgreSQL service and port 5432 availability (`TcpTestSucceeded: False`).
  - Identified that PostgreSQL is not currently installed or running as a service.
  - Preserved all Phase 1 files, endpoints, and frontend assets.

- [x] **Task 2: Database Configuration & Connection Management**
  - Updated `backend/requirements.txt` with `sqlalchemy>=2.0.36`, `psycopg[binary]>=3.2.3`, `alembic>=1.14.0`, and installed into `backend/venv`.
  - Configured Pydantic Settings in `backend/app/core/config.py` with PostgreSQL environment variables (`POSTGRES_SERVER`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_URL`).
  - Formatted connection string using Psycopg 3 driver: `postgresql+psycopg://user:password@host:port/dbname`.
  - Created `backend/app/core/database.py` with connection pooling (`pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`, `connect_args={"connect_timeout": 3}`).
  - Implemented `get_db()` generator with automatic session cleanup and rollback handling.
  - Implemented `check_database_connection()` executing `SELECT 1` without leaking credentials.

- [x] **Task 3: Domain Models Definition**
  Created modular SQLAlchemy models under `backend/app/models/`:
  1. **User** (`users`): UUID PK, role (`citizen`/`admin`), email (unique), mobile_number (unique), is_active, created_at, updated_at.
  2. **UserProfile** (`user_profiles`): UUID PK, user_id (FK to users.id, unique, ondelete=CASCADE), full_name, date_of_birth, state, district, residence_type (`rural`/`urban`), annual_family_income, occupation, education_level. *Privacy Rule: Aadhaar is strictly excluded from general profile storage.*
  3. **Scheme** (`schemes`): UUID PK, scheme_name, description, department, state_applicability, eligibility_summary, official_source_url, official_application_url, source_last_verified_at, is_active.
  4. **DocumentMetadata** (`document_metadata`): UUID PK, user_id (FK to users.id, ondelete=CASCADE), document_type, original_filename, storage_reference, mime_type, file_size, upload_status. *Architecture Rule: Document binaries are stored on filesystem/object storage, never in DB.*
  5. **Assessment** (`assessments`): UUID PK, user_id (FK to users.id, ondelete=CASCADE), scheme_id (FK to schemes.id, ondelete=SET NULL), assessment_type, result_data (PostgreSQL JSONB), overall_readiness_score. *Advisory Rule: Results are explicitly advisory, not official government decisions.*
  6. **Application** (`applications`): UUID PK, user_id (FK to users.id, ondelete=CASCADE), scheme_id (FK to schemes.id, ondelete=CASCADE), application_reference_number, submission_date, status. *Tracking Rule: Manual tracking with approved statuses (Submitted, Under Review, Pending, Document Verification, Approved, Rejected, Completed).*
  7. **Subscription** (`subscriptions`): UUID PK, user_id (FK to users.id, ondelete=CASCADE), plan_type (`free`/`premium`), billing_cycle (`monthly`/`six_months`/`yearly`), status, start_date, end_date. Approved pricing: ₹99/mo, ₹499/6mo, ₹899/yr.
  8. **Notification** (`notifications`): UUID PK, user_id (FK to users.id, ondelete=CASCADE), title, message, notification_type, scheduled_at, is_read.

- [x] **Task 4: Alembic Migrations Configuration**
  - Created `backend/alembic.ini` and `backend/alembic/env.py` connecting `Base.metadata` and dynamic Psycopg 3 connection URL.
  - Generated initial migration revision: `backend/alembic/versions/e36378f07849_initial_schema_phase_2.py`.
  - Implemented complete `upgrade()` and `downgrade()` DDL with indexes, foreign keys, and comments.
  - Verified static SQL compilation via `alembic upgrade head --sql` (generated clean PostgreSQL DDL).

- [x] **Task 5: Database Health Check API**
  - Preserved existing `GET /health` endpoint.
  - Implemented `GET /health/database`:
    - Executes `SELECT 1` query.
    - Returns HTTP 200 with `status: healthy` when database is reachable.
    - Returns HTTP 503 with `status: unhealthy` and safe generic error when database is unreachable.
    - Validated that database passwords and credentials are never exposed in responses or logs.

- [x] **Task 6: Testing & Verification**
  - Created comprehensive test suite in `backend/tests/test_database.py`.
  - Executed tests: 14 tests collected across `test_database.py` and `test_health.py` (100% passed).
  - Verified live HTTP endpoints over local Uvicorn process.

---

## 3. Verification Commands & Actual Results

### 1. Pytest Test Suite Execution
```powershell
& .\backend\venv\Scripts\pytest.exe .\backend\tests
```
**Output:**
```
============================= test session starts =============================
platform win32 -- Python 3.13.3, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\ravij\OneDrive\Desktop\Janmitra\backend
configfile: pytest.ini
collected 14 items

backend\tests\test_database.py ............                              [ 85%]
backend\tests\test_health.py ..                                          [100%]

======================= 14 passed, 1 warning in 15.70s ========================
```

### 2. Alembic Static SQL Generation
```powershell
Set-Location backend; & .\venv\Scripts\alembic.exe upgrade head --sql
```
**Output:** Successfully emitted static transactional PostgreSQL DDL creating `alembic_version`, `users`, `user_profiles`, `schemes`, `document_metadata`, `assessments`, `applications`, `subscriptions`, and `notifications`.

### 3. Live General Health Endpoint
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get
```
**Output:**
```json
{
  "status": "healthy",
  "message": "JanMitra Assist backend is running successfully",
  "environment": "development",
  "version": "1.0.0"
}
```

### 4. Live Database Health Check Endpoint (PostgreSQL Offline)
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health/database" -Method Get
```
**Output:** `HTTP 503 Service Unavailable`
```json
{
  "status": "unhealthy",
  "database": "disconnected",
  "database_type": "PostgreSQL",
  "driver": "psycopg3",
  "error": "Database server unreachable or credentials rejected.",
  "environment": "development"
}
```
*(No passwords, secrets, or internal connection strings were exposed).*

---

## 4. Pending Environment Prerequisites for Phase 3

To apply migrations online to a live PostgreSQL database:
1. **Install PostgreSQL** (see README.md section 4.2).
2. Create database: `CREATE DATABASE janmitra_db;`
3. Configure password in `backend/.env`.
4. Run: `Set-Location backend; .\venv\Scripts\alembic.exe upgrade head`
