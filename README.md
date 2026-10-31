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

> **Important Note:** JanMitra Assist **does not replace official government portals**. Citizens submit and finalize their applications on official government websites or through designated state/central touchpoints.

---

## 2. Approved Technology Stack

| Layer | Approved Technology | Purpose / Role |
| :--- | :--- | :--- |
| **Mobile App** | **Flutter (Dart)** | Citizen-facing mobile client (Android target) |
| **Backend** | **Python FastAPI** | High-performance asynchronous REST API |
| **Database** | **PostgreSQL** | Relational data store for schemes, users, and audit logs |
| **Admin Dashboard** | **React.js (Vite)** | Administrator portal for schemes & configuration |
| **OCR Engine** | **Local Tesseract OCR** | Privacy-first local document text extraction |
| **AI Model Runtime** | **Ollama (Llama 3.2 1B)** | Local lightweight LLM for eligibility guidance |
| **Push Notifications**| **Firebase Cloud Messaging** | Scheme alerts and status notifications |
| **Payment Gateway** | **Razorpay Test Mode** | Optional document readiness report checkout |
| **Version Control** | **Git** | Source code management across monorepo |

---

## 3. Monorepo Folder Structure

```
Janmitra/
├── .gitignore                    # Monorepo ignore rules (Python, Node, Flutter)
├── README.md                     # Project documentation & run guides
│
├── backend/                      # Python FastAPI REST API
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/               # API routes (schemes, documents, eligibility)
│   │   ├── core/                 # Config (pydantic-settings), logging
│   │   └── main.py               # FastAPI entry point & CORS configuration
│   ├── tests/                    # Backend unit & integration tests
│   ├── venv/                     # Python 3.13 virtual environment
│   ├── .env.example              # Environment variables template
│   ├── requirements.txt          # Phase 1 backend dependencies
│   └── run.py                    # Direct runner script
│
├── mobile_app/                   # Flutter Citizen Mobile Client
│   ├── android/                  # Android native project files & manifests
│   ├── assets/                   # Images and icons
│   ├── lib/
│   │   ├── core/                 # App constants, civic theme, API routes
│   │   ├── features/             # Feature modules (home, schemes, docs, etc.)
│   │   └── main.dart             # Flutter app entry point
│   ├── test/                     # Widget tests
│   ├── .env.example              # Mobile environment configuration
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

## 4. Environment Prerequisites & Required Software

Before running all components locally, ensure the following software is installed on Windows:

1. **Python 3.11+** (Detected: `Python 3.13.3` installed).
2. **Node.js 18+ and npm** (Detected: Node `v24.14.1`, npm `11.11.0` installed).
3. **Git** (Detected: `git 2.53.0` installed).
4. **Android SDK** (Detected at `C:\Users\<user>\AppData\Local\Android\Sdk`).
5. **Flutter SDK (3.24+)** *(Required for mobile development)*:
   - Download the official Flutter Windows bundle from: [flutter.dev/docs/get-started/install/windows](https://flutter.dev/docs/get-started/install/windows)
   - Extract to `C:\src\flutter`.
   - Add `C:\src\flutter\bin` to your Windows User Environment `PATH`.
   - Run `flutter doctor` in PowerShell to verify.
6. **PostgreSQL 15+** *(Required in Phase 2)*:
   - Install via Windows Package Manager:
     ```powershell
     winget install PostgreSQL.PostgreSQL
     ```
   - Or download installer from [postgresql.org](https://www.postgresql.org/download/windows/).

---

## 5. Quickstart & Component Run Instructions

### 5.1 Backend (FastAPI) Setup & Run

The virtual environment is already initialized at `backend/venv`.

1. **Activate the Virtual Environment**:
   ```powershell
   .\backend\venv\Scripts\Activate.ps1
   ```
   *(If script execution is restricted in PowerShell, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`)*.

2. **Configure Environment Variables**:
   ```powershell
   Copy-Item backend\.env.example backend\.env
   ```

3. **Install Dependencies** (if updating):
   ```powershell
   & .\backend\venv\Scripts\pip.exe install -r backend\requirements.txt
   ```

4. **Start the FastAPI Backend Server**:
   ```powershell
   & .\backend\venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --port 8000
   ```
   Or simply:
   ```powershell
   & .\backend\venv\Scripts\python.exe backend\run.py
   ```

5. **Verify the Health Check**:
   Open a browser or PowerShell:
   ```powershell
   Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"
   ```
   Interactive Swagger documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

6. **Run Backend Tests**:
   ```powershell
   & .\backend\venv\Scripts\pytest.exe .\backend\tests
   ```

---

### 5.2 Admin Dashboard (React + Vite) Setup & Run

1. **Navigate to the admin dashboard directory**:
   ```powershell
   cd admin_dashboard
   ```

2. **Install dependencies** (already installed in Phase 1):
   ```powershell
   npm install
   ```

3. **Start the local development server**:
   ```powershell
   npm run dev
   ```
   Open your browser at: [http://localhost:3000](http://localhost:3000)

4. **Test production build**:
   ```powershell
   npm run build
   ```

---

### 5.3 Mobile App (Flutter) Setup & Run

Once Flutter SDK is added to `PATH`:

1. **Navigate to the mobile app directory**:
   ```powershell
   cd mobile_app
   ```

2. **Fetch Flutter packages**:
   ```powershell
   flutter pub get
   ```

3. **Verify Flutter toolchain & connected devices**:
   ```powershell
   flutter doctor
   flutter devices
   ```

4. **Run the mobile app** (on connected Android device or emulator):
   ```powershell
   flutter run
   ```

5. **Run mobile unit/widget tests**:
   ```powershell
   flutter test
   ```

---

## 6. Common Setup Errors & Troubleshooting

### Issue 1: `flutter : The term 'flutter' is not recognized`
- **Cause:** Flutter SDK has not been downloaded or its `bin` directory is missing from the Windows `PATH` environment variable.
- **Fix:**
  1. Download Flutter SDK from [flutter.dev](https://flutter.dev/docs/get-started/install/windows).
  2. Extract it (e.g., `C:\src\flutter`).
  3. Search Windows for "Environment Variables" -> Edit Environment Variables -> Under User variables, select `Path` -> Edit -> Add `C:\src\flutter\bin`.
  4. Restart your terminal and run `flutter doctor`.

### Issue 2: PowerShell Script Execution Error (`running scripts is disabled on this system`)
- **Cause:** Windows PowerShell execution policy restricts scripts.
- **Fix:** Run this once in PowerShell:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

### Issue 3: Port 8000 or Port 3000 Already in Use
- **Cause:** A previous instance of the server or another app is holding the port.
- **Fix:**
  Check the active port:
  ```powershell
  Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
  ```
  Or change the port in `backend/.env` (`PORT=8001`) or `admin_dashboard/vite.config.js` (`port: 3001`).

### Issue 4: Android Emulator Cannot Connect to FastAPI Backend
- **Cause:** `localhost` inside the Android Emulator refers to the emulator itself, not your Windows machine.
- **Fix:** Use the special alias `http://10.0.2.2:8000` from the Android emulator. This is pre-configured in `mobile_app/lib/core/network/api_endpoints.dart`.

---

## 7. Implementation Roadmap & Phases

- **Phase 1: Project Setup & Foundation** *(Completed)*
- **Phase 2: Database Schema & Scheme Discovery Module** *(Pending Approval)*
- **Phase 3: Document Upload & Local OCR Processing**
- **Phase 4: AI-Powered Eligibility Evaluation Engine**
- **Phase 5: Readiness Reports & Application Guidance**
- **Phase 6: Integration, Polish & Submission Preparation**
