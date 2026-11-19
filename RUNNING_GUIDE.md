# JanMitra Assist – Complete Application Running & Operations Guide

## ⚡ Quick 1-Click Launch (MCA Viva Demonstration)

To immediately launch all 3 tiers of JanMitra Assist with a single command or click:

### Option A: Double-Click or Command Prompt
Double-click `run_project.bat` in the repository root, or run:
```cmd
.\run_project.bat
```

### Option B: PowerShell
```powershell
.\run_project.ps1
```

This starts:
1. **FastAPI Backend REST API** on `http://127.0.0.1:8000` (Interactive API Docs: `http://127.0.0.1:8000/docs`)
2. **React Admin Dashboard** on `http://127.0.0.1:3000`
3. **Flutter Citizen Web App** on `http://127.0.0.1:8080`

---

This guide provides end-to-end instructions for launching, developing, testing, and troubleshooting the entire **JanMitra Assist** platform across all components for academic review, viva demonstrations, and production staging:
1. **FastAPI Backend Service** (REST API, SQLAlchemy, Alembic, Email+Password Auth, AI RAG, Payment, Notifications)
2. **React Admin Dashboard** (Vite + React 18, Metrics, Scheme Management, Citizen Oversight, Tracking)
3. **Flutter Mobile Application** (Android & Web, Citizen Journey, Document Vault, Scheme Discovery, Subscriptions)
4. **PostgreSQL Database** (Relational Schema, Transactional Migrations, Docker Isolated Container)

---

## 1. Prerequisites & Host System Verification

| Component | Minimum Version | Host Verified Version | Notes |
| :--- | :--- | :--- | :--- |
| **Operating System** | Windows 10/11, macOS, Linux | Windows 11 x64 | PowerShell 5.1 / 7+ |
| **Python** | 3.11+ | Python 3.12.8 / 3.13 | `backend/venv` virtualenv |
| **Node.js & npm** | Node 18+, npm 9+ | Node v20.18.0, npm 10.8.2 | For Vite Admin Dashboard |
| **Flutter SDK** | 3.22+ | Flutter 3.29.0 / Dart 3.7.0 | In `./flutter` or system PATH |
| **Android Studio / JDK** | OpenJDK 17 or 21 | OpenJDK 21.0.10 (`Android Studio/jbr`) | **Do not use Java 25+ for Gradle** |
| **Docker Desktop / PostgreSQL** | Docker 24+ / PG 15+ | Docker Desktop on Windows | Port 5432 bound to 127.0.0.1 |
| **System Memory** | 8 GB RAM | 8 GB RAM | Gradle heap set to `-Xmx1536M` |

---

## 2. Environment Configuration & Variables

### A. Backend Configuration (`backend/.env`)

Ensure `backend/.env` exists (copied from `backend/.env.example`). Key configuration parameters:

```ini
PROJECT_NAME="JanMitra Assist API"
ENVIRONMENT="development"
DEBUG=True
API_V1_STR="/api/v1"
HOST="127.0.0.1"
PORT=8000
ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000,http://localhost:8080,http://127.0.0.1:8080"

# PostgreSQL Settings
POSTGRES_SERVER="127.0.0.1"
POSTGRES_PORT=5432
POSTGRES_USER="janmitra_test_user"
POSTGRES_PASSWORD="<your_secure_postgres_password>"
POSTGRES_DB="janmitra_test_db"

# Security & Tokens
JWT_SECRET_KEY="janmitra_dev_jwt_secret_key_change_in_production_min_32_chars"
JWT_ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

# AI Advisory & OCR Providers
OCR_PROVIDER="mock"
AI_PROVIDER="mock"

# Razorpay Subscriptions (Test Mode)
RAZORPAY_KEY_ID="rzp_test_janmitra_dev_key"
RAZORPAY_KEY_SECRET="janmitra_razorpay_secret_dev_32char"
RAZORPAY_WEBHOOK_SECRET="janmitra_webhook_secret_dev_32char"
RAZORPAY_DEV_MODE=True

# SMTP & Password Recovery Settings
SMTP_HOST="127.0.0.1"
SMTP_PORT=1025
SMTP_USER=""
SMTP_PASSWORD=""
SMTP_USE_TLS=False
SMTP_FROM_EMAIL="noreply@janmitra.internal"
DEV_MAILBOX_FALLBACK=True
FRONTEND_RESET_PASSWORD_URL="http://127.0.0.1:8080/#/reset-password"
```

### B. Admin Dashboard Configuration (`admin_dashboard/.env`)

```ini
VITE_API_BASE_URL="http://127.0.0.1:8000"
VITE_APP_TITLE="JanMitra Assist Admin Dashboard"
```

### C. Mobile App Configuration (`mobile_app/.env`)

- **For Flutter Web**:
  ```ini
  API_BASE_URL="http://127.0.0.1:8000"
  APP_ENVIRONMENT="development"
  ENABLE_MOCK_SERVICES=true
  ```
- **For Android Emulator**: Android emulators route host machine `localhost` via `10.0.2.2`:
  ```ini
  API_BASE_URL="http://10.0.2.2:8000"
  APP_ENVIRONMENT="development"
  ENABLE_MOCK_SERVICES=true
  ```
- **For Physical Device / Local WiFi**: Replace with host LAN IP:
  ```ini
  API_BASE_URL="http://192.168.1.X:8000"
  APP_ENVIRONMENT="development"
  ENABLE_MOCK_SERVICES=true
  ```

---

## 3. PostgreSQL Database Startup & Docker Lifecycle

JanMitra Assist maintains an isolated PostgreSQL container for integration testing and production database staging:

```powershell
# 1. Start the existing PostgreSQL Docker container
docker start janmitra_postgres_test_ci

# 2. Verify container is healthy and listening on port 5432
docker ps -f "name=janmitra_postgres_test_ci"
Get-NetTCPConnection -LocalPort 5432 -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,State

# 3. If creating container from scratch for the first time:
docker run -d `
  --name janmitra_postgres_test_ci `
  -e POSTGRES_DB=janmitra_test_db `
  -e POSTGRES_USER=janmitra_test_user `
  -e POSTGRES_PASSWORD=<your_secure_password> `
  -p 127.0.0.1:5432:5432 `
  postgres:16-alpine
```

*Note: In development and viva offline mode, the backend automatically uses SQLite (`janmitra_dev.db`) when external PostgreSQL is not running, ensuring zero runtime dependencies during demonstrations.*

---

## 4. Database Migration Execution & Linear Alembic Chain

JanMitra Assist strictly enforces schema management exclusively via **Alembic migrations** across 15 linear revisions up to head `e7f8a9b0c1d2`:

```powershell
cd E:\Janmitra\backend

# Verify current database revision
.\venv\Scripts\alembic current

# Apply all migrations to head
.\venv\Scripts\alembic upgrade head
```

### Migration Revision Chain:
- `<base>` → `e36378f07849` (Initial Schema Phase 2)
- `e36378f07849` → `4dcd7dfc601d` (Auth & User Management Tables)
- `4dcd7dfc601d` → `7a8e5f3c9102` (Extend Scheme Model for Phase 4)
- `7a8e5f3c9102` → `e9f8a7b6c5d4` (Extend Document Metadata for Phase 5)
- `e9f8a7b6c5d4` → `f1a2b3c4d5e6` (Add AI Advisory & RAG Tables)
- `f1a2b3c4d5e6` → `b2c3d4e5f6a7` (Payment Transactions Table)
- `b2c3d4e5f6a7` → `c4d5e6f7a8b9` (Webhook Events Table & Scheme Guide Cache)
- `c4d5e6f7a8b9` → `d5e6f7a8b9c0` (User Monthly Quotas Table & Refund Lifecycle)
- `d5e6f7a8b9c0` → `e6f7a8b9c0d1` (Processing Ownership Tokens on Document Metadata)
- `e6f7a8b9c0d1` → `f2a3b4c5d6e7` (Status History & Application Reminders)
- `f2a3b4c5d6e7` → `a3b4c5d6e7f8` (Device Tokens & FCM Push Notification Support)
- `a3b4c5d6e7f8` → `b4c5d6e7f8a9` (Email Password Authentication & password_hash)
- `b4c5d6e7f8a9` → `c5d6e7f8a9b0` (Password Reset Tokens Table)
- `c5d6e7f8a9b0` → `d6e7f8a9b0c1` (Reminder Dispatch Lease & Multi-Worker Tracking)
- `d6e7f8a9b0c1` → `e7f8a9b0c1d2` (Scheme Intelligence & Official Beneficiary Analytics, `head`)

---

## 5. Backend API Service Startup (Port 8000)

Start the FastAPI application via Uvicorn:

```powershell
cd E:\Janmitra\backend
.\venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- **Service Base URL:** `http://127.0.0.1:8000`
- **Interactive Swagger Documentation:** `http://127.0.0.1:8000/docs`
- **ReDoc Technical Schema:** `http://127.0.0.1:8000/redoc`
- **Application Health Check:** `http://127.0.0.1:8000/health`
- **Database Engine Health:** `http://127.0.0.1:8000/health/database`

---

## 6. Flutter Web & Mobile Client Startup (Port 8080 & Android)

### A. Running Flutter Web Client (Recommended for Viva Demo)
```powershell
cd E:\Janmitra\mobile_app
flutter run -d web-server --web-port=8080 --web-hostname=127.0.0.1
```
- **Citizen Web App URL:** `http://127.0.0.1:8080`
- **Password Reset Deep Link Route:** `http://127.0.0.1:8080/#/reset-password?token=<token>`

### B. Running on Android Device / Emulator
Ensure `JAVA_HOME` targets OpenJDK 21 (JDK 25 will fail with Gradle 8.x):
```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
cd E:\Janmitra\mobile_app
flutter run -d <device-id>
```

### C. Building the Android Debug APK
```powershell
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
cd E:\Janmitra\mobile_app
flutter build apk --debug --android-skip-build-dependency-validation
```
- Built APK Location: `mobile_app/build/app/outputs/flutter-apk/app-debug.apk`

---

## 7. React Admin Dashboard Startup (Port 3000)

Start the Vite dev server for the administrative management portal:

```powershell
cd E:\Janmitra\admin_dashboard
npm run dev -- --host 127.0.0.1 --port 3000
```

- **Admin Portal URL:** `http://localhost:3000` (or `http://127.0.0.1:3000`)
- **Production Build Check:**
  ```powershell
  npm run build    # Produces optimized dist/ bundle in ~1.9s with 0 errors
  ```

---

## 8. Demo Account Provisioning (Admin & Synthetic Citizen)

JanMitra Assist enforces strict security: default passwords are NEVER hardcoded into source code, reports, or documentation.

### A. Provisioning an Administrator Account
Run the secure CLI provisioning tool. You will be prompted securely for a password (hidden input via `getpass`):

```powershell
cd E:\Janmitra\backend
.\venv\Scripts\python -m app.cli.admin_create --email admin@janmitra.internal
```

- Passwords must meet complexity policy: min 8 characters, uppercase, lowercase, number, symbol.
- Credentials are encrypted using **Argon2id** (`time_cost=2, memory_cost=65536, parallelism=2`).
- The user is promoted to `role='admin'` immediately upon creation.

### B. Registering a Demo Citizen Account
Citizens register directly in the Flutter Web App (`http://127.0.0.1:8080`) or via REST API:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/auth/register" -Method Post -ContentType "application/json" -Body (@{
    full_name = "Synthetic Citizen Demo"
    email = "citizen_demo@example.com"
    password = "<choose_strong_password>"
    confirm_password = "<choose_strong_password>"
    mobile_number = "+919876543210"
} | ConvertTo-Json)
```

- Public registration hardcodes `role="citizen"` server-side (preventing privilege escalation).

---

## 9. Complete Viva Demonstration Sequence

Follow this step-by-step sequence to demonstrate the complete JanMitra Assist platform during an MCA evaluation:

### Step 1: System Health & Architecture Overview (1-2 mins)
1. Open Chrome and navigate to `http://127.0.0.1:8000/docs` (FastAPI Swagger UI).
2. Execute `GET /health` and `GET /health/database` to demonstrate multi-dialect support (SQLite & PostgreSQL).
3. Open `http://localhost:3000` (React Admin Dashboard) and explain the 3-tier architecture:
   - Tier 1: FastAPI REST API with SQLAlchemy ORM and Alembic linear migrations.
   - Tier 2: React.js administrative oversight and governance control room.
   - Tier 3: Flutter multi-platform client (Android, iOS, Web).

### Step 2: Administrator Governance & Scheme Registry (3 mins)
1. Log in to the Admin Dashboard (`http://localhost:3000`) with `admin@janmitra.internal`.
2. Review the **Overview KPI Cards** (Registered Citizens, Welfare Schemes, Tracked Applications, Revenue).
3. Point out the **Civic Boundary Advisory**: JanMitra Assist is strictly an advisory and document intelligence platform; official submissions occur on official government portals.
4. Navigate to **Schemes Management**:
   - Filter schemes by category (Agriculture, Healthcare, Housing, Education).
   - Click on `[DEMO] PM-KISAN` to view scheme details, official source links, and eligibility criteria.
5. Navigate to **Citizen User Administration**:
   - Demonstrate citizen search and profile modal.
   - Show account status toggling (Activate / Deactivate).
6. Navigate to **Document Intelligence**:
   - Review OCR processing metrics, pipeline architecture, and privacy safeguards (Aadhaar redaction).
7. Navigate to **System Configuration**:
   - Click "Ping Live Services" to demonstrate real-time microservice latency and connectivity.

### Step 3: Citizen Journey on Flutter Client (5 mins)
1. Open Flutter Citizen Web (`http://127.0.0.1:8080`).
2. **Citizen Registration**:
   - Click "Register", enter Full Name, Email, Password, and Mobile Number.
   - Submit and show immediate transition to authenticated state (Email + Password standard).
3. **Profile Setup**:
   - Fill in demographic data (State: Maharashtra, Annual Income, Social Category, Land Holding).
4. **Scheme Discovery & AI Matching**:
   - Navigate to Scheme Discovery tab.
   - Search for schemes and run Eligibility Assessment against PM-KISAN or Ayushman Bharat.
   - Note the **Readiness Score** indicator and statutory advisory disclaimer.
5. **Document Vault & OCR Intelligence**:
   - Navigate to Document Vault.
   - Demonstrate document upload (Aadhaar / Income Certificate / Land Record).
   - Review extracted OCR text, confidence bar, and checklist status.
6. **Application Assistance & Tracking**:
   - Open Application Assistance for PM-KISAN.
   - Review pre-application document checklist.
   - Add a self-reported application record to track submission.
   - Update application status (Draft → Submitted → Under Review).
   - Create a task reminder (e.g., "Verify bank DBT linkage") and toggle completion.
7. **Premium Subscriptions & Razorpay Test Checkout**:
   - Open Subscription Plans.
   - View Free vs Premium tier benefits and monthly quotas.
   - Demonstrate subscription upgrade in dev/test mode.

### Step 4: Security & Password Recovery Flow (2 mins)
1. In the Flutter App, click "Logout".
2. Click "Forgot Password?" and enter the citizen email address.
3. Submit and observe the anti-enumeration response ("If an account exists, instructions have been sent").
4. Explain the backend security architecture:
   - Reset tokens are single-use and expire after 15 minutes.
   - Reset tokens are stored in the database hashed with SHA-256 (never stored in plaintext).
   - Password reset immediately revokes all active refresh sessions.
   - Consumed tokens cannot be replayed (returns 400 Bad Request).

---

## 10. Common Errors & Troubleshooting Solutions

### 1. Java 25 vs Gradle Incompatibility
- **Symptom:** Gradle crashes with `Error resolving plugin [id: 'dev.flutter.flutter-plugin-loader', version: '1.0.0'] > 25.0.1`.
- **Cause:** Gradle 8.x does not support Java 25.
- **Solution:** Set `$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"` in PowerShell before launching Flutter.

### 2. Gradle JVM Native Memory Allocation Failures
- **Symptom:** Gradle daemon crashes with `hs_err_pid*.log` or `Native memory allocation (malloc) failed`.
- **Cause:** Host system has 8 GB total RAM; excessive heap triggers memory exhaustion.
- **Solution:** In `mobile_app/android/gradle.properties`, keep heap pinned to `org.gradle.jvmargs=-Xmx1536M -XX:MaxMetaspaceSize=512M`.

### 3. OneDrive NTFS File Locking on Build Output
- **Symptom:** `Unable to delete directory ...\build\classes\kotlin\main`.
- **Cause:** OneDrive background sync locks files while Gradle tries to clean or overwrite them.
- **Solution:** Pause OneDrive sync during continuous APK compilation.

### 4. CORS Missing Origin Rejection
- **Symptom:** Flutter Web on `http://127.0.0.1:8080` receives `XMLHttpRequest error` or `CORS policy` block.
- **Cause:** Starlette/FastAPI CORS requires exact matching of IP and localhost origins.
- **Solution:** Both `http://localhost:8080` and `http://127.0.0.1:8080` are declared in `ALLOWED_ORIGINS` in `backend/app/core/config.py`.

### 5. PostgreSQL Test Connection Skipped
- **Symptom:** Pytest displays `15 skipped` in `test_postgres_integration.py`.
- **Cause:** Docker container is paused or `TEST_POSTGRES_URL` environment variable is not passed.
- **Solution:** Start the container via `docker start janmitra_postgres_test_ci` and provide the connection string:
  ```powershell
  $env:TEST_POSTGRES_URL="postgresql+psycopg://janmitra_test_user:janmitra_test_password_2026@127.0.0.1:5432/janmitra_test_db"
  ```

---

## 11. Safe Shutdown, Cleanup & Service Restart Procedures

### A. Stopping All Services Safely
```powershell
# Stop FastAPI backend daemon / task
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "*uvicorn*" } | Stop-Process -Force

# Stop React Vite dev server
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force

# Stop Flutter Web dev server
Get-Process dart -ErrorAction SilentlyContinue | Stop-Process -Force

# Stop PostgreSQL Docker container (preserves all data in volume)
docker stop janmitra_postgres_test_ci
```

### B. Restarting All Services in Order
1. **Start PostgreSQL:** `docker start janmitra_postgres_test_ci`
2. **Start FastAPI:** `cd backend; .\venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
3. **Start React Admin:** `cd admin_dashboard; npm run dev -- --host 127.0.0.1 --port 3000`
4. **Start Flutter Web:** `cd mobile_app; flutter run -d web-server --web-port=8080 --web-hostname=127.0.0.1`

---

## 12. Git Safety Rules & Preservation Policy
- Do NOT run `git checkout -- .` or `git reset --hard`.
- Working changes are tracked across all modules. Keep staged files clean (`git diff --cached` must show 0 staged files).
- Zero commits or pushes are executed without explicit user permission.

---

## 13. Scheme Intelligence & Official Beneficiary Analytics REST API Reference

The Scheme Intelligence engine delivers category-wise rules, dynamic document checklists, clickable document guidance, and official government beneficiary statistics.

### Public & Citizen Endpoints (`/api/v1/schemes/`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/schemes/{scheme_id}/categories` | Returns all applicable social categories (e.g., General, OBC, SC, ST, EWS) for a scheme. |
| `GET` | `/api/v1/schemes/{scheme_id}/category-rules` | Retrieves specific criteria (income limit, land limit, quota %, concessions) per category. |
| `GET` | `/api/v1/schemes/{scheme_id}/documents` | Dynamic category-aware document checklist. Query param: `?category=OBC`. |
| `GET` | `/api/v1/schemes/{scheme_id}/analytics` | Published official government beneficiary dataset, breakdowns (by category, gender, region), source citations, and civic disclaimers. |
| `POST` | `/api/v1/schemes/{scheme_id}/evaluate-category` | **Privacy-Preserving On-Demand Rule Assessment**. Accepts citizen profile in payload, evaluates eligibility against category rules dynamically without persistently saving caste data. |
| `GET` | `/api/v1/schemes/document-guides/{doc_type}` | Comprehensive multi-state issuing guide for 8 core documents. Query param: `?state=Maharashtra` (or Gujarat, Uttar Pradesh, All India). |

### Administrator Analytics Lifecycle Endpoints (`/api/v1/admin/analytics/`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/admin/analytics/datasets` | List all beneficiary datasets across all statuses (`draft`, `validated`, `published`, `archived`). Filter by `?scheme_id=...` and `?status=...`. |
| `POST` | `/api/v1/admin/analytics/datasets/import` | Import a new official government dataset (JSON payload with scheme metrics and breakdown items). Initial status: `draft`. |
| `POST` | `/api/v1/admin/analytics/datasets/{id}/validate` | Execute data integrity validations (sum check on breakdowns vs total, date sequence verification, official source URL check). |
| `POST` | `/api/v1/admin/analytics/datasets/{id}/publish` | Transition validated dataset to `published`. Automatically unpublishes any prior published dataset for that scheme to maintain single source of truth. |
| `POST` | `/api/v1/admin/analytics/datasets/{id}/unpublish` | Revert published dataset back to `draft` (e.g. if official ministry revises data). |
| `GET` | `/api/v1/admin/analytics/datasets/{id}/audit-logs` | Retrieve full immutable audit trail for the dataset (action, user ID, IP address, timestamp, notes). |

---

## 14. Administrator Scheme Analytics Management Lifecycle

The React Admin Dashboard includes a dedicated **Scheme Analytics & Intelligence Modal** (`SchemeAnalyticsModal.jsx`) embedded in **Schemes Management**:

1. **Accessing Analytics Modal:**
   - Log in as admin (`admin@janmitra.internal`) at `http://127.0.0.1:3000`.
   - Go to **Scheme Management**.
   - Click the blue **"Analytics & Rules"** button on any scheme row (e.g., PM-KISAN, PM-JAY, PMAY-G).
2. **Reviewing Published Government Data:**
   - View official government metrics (Total Beneficiaries, Disbursed Amount, Target Population, Active Status).
   - Inspect Category Breakdown (General, OBC, SC, ST) with percentage distribution bars.
   - Inspect State / Regional and Gender breakdowns.
   - Review official source citation link (e.g., `https://pmkisan.gov.in/`).
3. **Importing New Government Datasets:**
   - Switch to the **"Import Official Dataset"** tab in the modal.
   - Enter reporting period (e.g., `FY 2024-2025 Q3`), total beneficiary count, total disbursed amount, source name, and official portal URL.
   - Add structured breakdowns (Category, Gender, State).
   - Click **"Import Dataset"** — record is created in `draft` state and an audit log entry is written.
4. **Validation & Publishing Workflow:**
   - Click **"Validate Dataset"**: system checks that category breakdowns do not exceed total beneficiaries and verifies URL format.
   - Click **"Approve & Publish"**: status transitions to `published`. The citizen mobile app immediately reflects the updated statistics upon next fetch.
5. **Audit History Review:**
   - Switch to the **"Audit History"** tab to view the complete immutable lifecycle log (`IMPORT`, `VALIDATE`, `PUBLISH`, `UNPUBLISH`).

---

## 15. Clickable Document Guidance & Issuing Authorities

JanMitra Assist bridges document intelligence with real-world administrative navigation across 8 core certificate types:

### Supported Document Types:
1. `income_certificate` – Income Certificate (तहसीलदार / Revenue Department)
2. `caste_certificate` – Caste / Community Certificate (Sub-Divisional Magistrate / SDO)
3. `domicile_certificate` – Domicile / Residence Certificate (District Magistrate / Tehsildar)
4. `ews_certificate` – Economically Weaker Section (EWS) Certificate
5. `non_creamy_layer` – Non-Creamy Layer (NCL) Certificate for OBC
6. `land_record` – Digital Land Record / 7/12 Extract (Bhulekh / Mahabhulekh)
7. `ration_card` – Ration Card / NFSA Card (Food & Civil Supplies Department)
8. `bank_passbook` – Bank Passbook with DBT / Aadhaar Seeded Account

### Features Available to Citizens:
- **State Switcher:** Toggle instructions between Maharashtra (`Aaple Sarkar`), Gujarat (`Digital Gujarat`), Uttar Pradesh (`e-District UP`), and All India Central Portals.
- **Issuing Authority Information:** Direct names, designation of sanctioning authority, and official portal link (e.g. `https://aaplesarkar.mahaonline.gov.in/`).
- **Prerequisite Checklist:** Checklist of mandatory supporting documents required before applying (e.g. Ration Card, Electricity Bill, Self-Declaration, School Leaving Certificate).
- **Step-by-Step Procedure:** Clear numbered instructions for both **Online Portal** application and **CSC / Seva Kendra** offline submission.
- **Fees & SLA Timelines:** Statutory government application fees (e.g., ₹20 - ₹50) and official processing SLA (typically 15 to 21 working days).
- **Direct Vault Integration:** A **"Upload to Document Vault"** action button that directly opens the camera/file picker to upload and analyze the document via OCR.

---

## 16. Docker Compose Multi-Container Production Deployment

JanMitra Assist provides production-ready containerization for the entire stack.

### Architecture Overview:
- **`postgres` container:** Official PostgreSQL 16 Alpine with healthcheck and persistent volume (`janmitra_pgdata`).
- **`backend` container:** Multi-stage Python 3.12 slim image with non-root security user, automated migrations via Alembic on entrypoint, and Uvicorn production server.
- **`admin_dashboard` container:** Multi-stage Node 20 builder + Nginx 1.25 Alpine reverse proxy with gzip compression, security headers, and client-side routing fallback.

### Production Deployment Steps:

```powershell
cd E:\Janmitra

# 1. Build and start all 3 containers in background
docker compose up -d --build

# 2. Check container status
docker compose ps

# 3. View service logs
docker compose logs -f backend

# 4. Access live production endpoints:
#    - FastAPI Backend REST API: http://localhost:8000
#    - FastAPI Swagger Documentation: http://localhost:8000/docs
#    - React Admin Dashboard: http://localhost:3000
#    - PostgreSQL Database: localhost:5432
```

For comprehensive deployment instructions, SSL/TLS reverse proxy configurations, automated backup scripts, and disaster recovery procedures, refer to [`DEPLOYMENT_GUIDE.md`](file:///E:/Janmitra/DEPLOYMENT_GUIDE.md).
