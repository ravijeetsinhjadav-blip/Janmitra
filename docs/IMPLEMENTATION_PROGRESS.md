# JanMitra Assist – Implementation Progress Tracker

**Project Name:** JanMitra Assist – AI-Powered Government Service Eligibility and Document Intelligence System  
**Academic Target:** MCA Major Project  
**Current Phase:** Phase 5 (Document Vault & OCR Pipeline) – COMPLETED & AUDITED


---

## 1. Environment & Architecture Dependency Audit

| Tool / Technology | Required For | Status on Machine | Detected Version / Path | Action Taken / Status |
| :--- | :--- | :--- | :--- | :--- |
| **Git** | Version Control | **Installed** | `2.53.0.windows.2` | Monorepo tracked with clean branch history |
| **Python** | Backend API | **Installed** | `3.13.3` (`pip 25.2`) | Active venv at `backend/venv` |
| **FastAPI** | REST API Framework | **Installed** | `0.115.11` | Phase 1-4 endpoints mounted and active |
| **SQLAlchemy** | ORM Engine | **Installed** | `2.1.6` | Declarative models for users, schemes, assessments |
| **Psycopg 3** | PostgreSQL Driver | **Installed** | `3.3.6` (`psycopg-binary 3.3.6`) | Configured via `postgresql+psycopg://` URL |
| **Alembic** | Database Migrations | **Installed** | `1.20.1` | Migrations `e36378f07849`, `4dcd7dfc601d`, and `7a8e5f3c9102` |
| **PyJWT** | JWT Authentication | **Installed** | `2.10.1` (`pyjwt[crypto]`) | HS256 access tokens with payload verification |
| **Bcrypt** | Cryptographic Hashing | **Installed** | `4.3.0` | Secure hashing for OTPs and secret tokens |
| **Flutter SDK** | Mobile Client | **Installed (Local)**| `3.27.4` / Dart `3.6.2` | Local SDK configured at `.\flutter\bin\flutter.bat` |
| **flutter_secure_storage** | Mobile Token Vault | **Installed** | `^9.2.2` | Hardware-backed keystore/keychain for tokens |
| **Node.js / npm** | Admin Dashboard | **Installed** | `v24.14.1` / `11.11.0` | React dashboard scaffolded in Phase 1 |
| **PostgreSQL Server** | Relational Database | Service Configured | Localhost port 5432 | Psycopg 3 driver & migrations ready |

---

## 2. Phase 4 Implementation & Audit Corrections

### Task A: Scheme Model Extension & Database Migration
- Extended `Scheme` model in `backend/app/models/scheme.py` with structured JSONB and relational fields:
  - `short_description`: Concise summary for mobile cards (VARCHAR 500).
  - `category`: Sector category (Agriculture, Healthcare, Housing, Education, Social Welfare).
  - `benefits`: Structured JSON list of financial and non-financial entitlements.
  - `eligibility_criteria`: Structured rule conditions with target field, operator, expected value, and citizen explanation.
  - `required_profile_fields`: Explicit list of citizen demographic fields needed for automated evaluation.
  - `application_process`: Step-by-step guidance for completing formal portal applications.
  - `required_documents`: Comprehensive list of documents required for the scheme.
  - `source_verification_details`: Supporting government orders, guidelines, and limitation notes.
  - `status`: Lifecycle status (`active`, `inactive`, `discontinued`).
  - `is_demo_data`: Boolean flag clearly distinguishing curated MCA test records from live portal data.
- Authored Alembic migration `7a8e5f3c9102_extend_scheme_model_for_phase_4.py`.
- Verified static SQL compilation for PostgreSQL via `alembic upgrade head --sql` and full reversibility via `alembic downgrade 7a8e5f3c9102:4dcd7dfc601d --sql`.
- **PostgreSQL Status:** Static SQL compatibility verified via `PostgresqlImpl`. Live database migration execution is documented as pending PostgreSQL daemon startup on localhost port 5432.

### Task B: Deterministic Eligibility Engine & Score Renaming
- Implemented `EligibilityEngine` in `backend/app/services/eligibility_service.py`:
  - **Score Clarification:** Renamed readiness score to **`Criteria Match Percentage`** (`criteria_match_percentage`). Represents the proportion of verified conditions satisfied. Explicitly documented that this is **NOT an official government approval likelihood or probability**.
  - **Score Interpretation:** Added `score_interpretation` text to every evaluation output clearly explaining condition compliance and stating the non-guarantee disclaimer.
  - **Condition Status Separation:** Strictly partitions conditions into `satisfied_count`, `not_satisfied_count`, and `unknown_count`.
  - **Missing Profile Data Rule:** If a required fact is absent or null, condition status is classified as `unknown` (never auto-failed), and the scheme overall status is set to `Insufficient Information` with actionable `missing_fields` alerts.
  - **Mandatory Failure Enforcement:** Any failed mandatory criterion immediately classifies the scheme as `Not Eligible Based on Available Information` and excludes it from recommendations.
  - **Operators Audited & Hardened:**
    - `eq`: Case-insensitive stripped normalized matching for strings; handles universal state match (`All India`).
    - `neq`: Case-insensitive stripped inequality for controlled fields.
    - `gt`, `gte`, `lt`, `lte`: Strict numeric validation; non-numeric values fail safely without unhandled exceptions; checks for NaN/Infinity.
    - `in`: Normalizes collections; safe lookup across lists, sets, and tuples.
    - `contains`: Validates non-empty substring and non-empty target; empty strings never match.
  - **Arbitrary Expression Execution Prevention:** No `eval()`, `exec()`, or dynamic code execution. Operator dispatch is restricted to `SUPPORTED_OPERATORS`.
  - **Birthday Boundary Age Calculation:** Tested on exact birthday anniversary, day before, day after, and leap year Feb 29. Future dates and invalid formats safely return `None`.

### Task C: Curated Verified Government Seed Schemes
- Seeded 5 verified official demo schemes with authentic nodal links in `backend/app/services/scheme_service.py`:
  1. **PM-KISAN (Central):** ₹6,000/year income support for farmer families (`https://pmkisan.gov.in/`).
  2. **AB-PMJAY (Ayushman Bharat):** ₹5 Lakh annual secondary/tertiary health cover for vulnerable families (`https://pmjay.gov.in/`).
  3. **PMAY-G (Pradhan Mantri Awaas Yojana - Gramin):** Financial assistance for rural pucca house construction (`https://pmayg.nic.in/`).
  4. **NSP Post-Matric Scholarship:** Higher education tuition support for students with annual family income <= ₹2.5 Lakh (`https://scholarships.gov.in/`).
  5. **Maharashtra MJPJAY (State Welfare):** Up to ₹5 Lakh cashless critical illness hospitalization for Maharashtra ration card holders (`https://www.jeevandayee.gov.in/`).
- All seed records clearly flagged with `is_demo_data = True` and documented with `source_verification_details`.

### Task D: Recommendation Match Score & UI Advisory Labeling
- Recommendations exclude any scheme with `not_satisfied_count > 0`.
- Missing profile fields are classified as unknown and not treated as confirmed matches.
- Recommendations include specific match reasons and an explicit advisory notice.
- Flutter UI displays an advisory disclaimer banner above recommendations.

### Task E: Final Logic Audit, Hardening & Verification
- **Invalid Eligibility Rule Handling:**
  - Audited numeric operators (`gt`, `gte`, `lt`, `lte`).
  - Distinctly partitions invalid scheme configuration expected values (`None`, non-numeric strings, `NaN`, `Infinity`) $\to$ returns safe `status="unknown"` with explicit `"Invalid scheme rule configuration"` error message. Never incorrectly penalizes a citizen as `not_satisfied`.
  - Missing citizen profile data $\to$ returns safe `status="unknown"` with `"Missing from citizen profile: <field>"`.
  - Non-numeric or invalid actual citizen profile values for numeric operators $\to$ returns safe `status="unknown"` with `"Cannot evaluate condition: citizen profile field <field> is not a valid number"`.
  - Validated type safety for collection operators (`in` requires collections/strings) and text operators (`contains` requires non-empty strings/collections).
- **Age Calculation & Leap Year Birthday Handling:**
  - Scheme-specific official cutoff dates take priority wherever defined in government notifications.
  - Acknowledges that neither convention is a universal Indian legal rule. Section 9 of the General Clauses Act, 1897 concerns the commencement and termination of time periods (excluding/including boundary days in statutory intervals) and does not establish a direct legal rule for leap-year birthdays.
  - Supported technical default conventions via configurable `feb29_convention` parameter:
    - `"statutory_anniversary"` (default technical convention): Anniversary deemed on March 1 after 365 complete calendar days elapse in common years.
    - `"end_of_february"`: Administrative convention where the anniversary is deemed to occur on the final day of February (February 28 in common years).
  - Supported scheme-specific official cutoff dates (`reference_date` / `cutoff_date`) for age determination (e.g. January 1 or July 1 of recruitment/academic years).
- **Harden the `in` Operator:**
  - Accepts only valid collections: `list`, `tuple`, or `set`.
  - Rejects plain strings (`str`) as expected collections with an explicit configuration error (`status="unknown"`).
  - Eliminates substring-related false positives (e.g. `"SC"` in `"MISC"`, `"Maha"` in `"Maharashtra"`).
- **Review of the `contains` Operator:**
  - Prevents ambiguous substring matching for controlled demographic fields (`residence_type`, `state`, `gender`, `category`, `occupation`) by enforcing normalized exact matching.
  - Prevents substring false positives (e.g. `"ur"` matching `"rural"` or `"urban"`, `"art"` matching `"Cart driver"`, `"SC"` matching `"MISC"`).
  - Retains substring matching only where explicitly justified on free-form descriptive text fields.
- **Correct Source Freshness Defaults:**
  - Newly created schemes default to `Pending Verification`, not `Verified Official Source`.
  - Verification timestamps are never invented (`source_last_verified_at` defaults to `None` until an actual source review occurs).
  - Supports lifecycle freshness statuses: `Pending Verification`, `Verified Official Source`, `Review Required`, and `Stale`.
- **Scheme Source Verification & Demo Integrity:**
  - Extended scheme metadata to persist `source_freshness_status`, `eligibility_source_reference`, `benefits_source_reference`, and `source_verification_details`.
  - All 5 seeded schemes verified against authentic central and state portals:
    1. PM-KISAN: Ministry of Agriculture & Farmers Welfare, GoI (Section 3 Eligibility, Section 2 DBT).
    2. Ayushman Bharat PM-JAY: National Health Authority / MoHFW (SECC 2011 Deprivation Guidelines, Benefit Package 2.2).
    3. PMAY-G: Ministry of Rural Development, GoI (Chapter 3 Beneficiary Selection, Chapter 2 Financial Grants).
    4. National Post-Matric Scholarship: Ministry of Social Justice / Ministry of Education, GoI (NSP Guidelines).
    5. Maharashtra MJPJAY: Public Health Department, Govt. of Maharashtra (GR No. MJPJAY-2023/CR-142/PH-4).
  - All 5 schemes clearly marked as `is_demo_data = True` and labeled with `[DEMO]` and `DEMO / TEST DATA` limitation notices.
- **Recommendation Match Score & Advisory Safeguards:**
  - Match scores are labeled as advisory `Criteria Match Percentage` and never represented as government approval probability.
  - Missing profile fields are classified as unknown, not treated as confirmed matches.
  - Schemes with any clearly failed mandatory conditions are strictly excluded from recommendations.
  - UI displays an advisory disclaimer above recommendations.
- **Testing & Verification:**
  - **Backend Pytest Suite:** **63 passed, 1 skipped (live PostgreSQL network test), 0 failed** across 64 tests.
  - **Flutter Widget & Unit Tests:** **7 passed, 0 failed** (including responsiveness and mobile card tests).
  - **Flutter Analysis:** **0 issues found** via `flutter analyze`.
  - **Alembic Database Migrations:** Static SQL upgrade and downgrade validated via `PostgresqlImpl`. Live execution documented as pending PostgreSQL local daemon availability.

---

## 3. Approved Subscription Pricing (Locked)
- **Monthly Plan:** ₹99
- **Yearly Plan:** ₹799
- *Note:* No six-month plan exists or is authorized.

---

## 4. Phase Roadmap
- [x] **Phase 1:** Project Setup & Foundation
- [x] **Phase 2:** Database & Backend Foundation
- [x] **Phase 3:** Authentication & User Management
- [x] **Phase 4:** Government Scheme Discovery & Eligibility Engine
- [x] **Phase 5:** Document Vault & OCR Pipeline
- [ ] **Phase 6:** AI Advisory & Readiness Assessment Engine (PENDING USER INITIATION)
- [ ] **Phase 7:** Assisted Service, Subscription & Payment Integration (PENDING USER INITIATION)
- [ ] **Phase 8:** Final Polish, Security Audit & Academic Packaging (PENDING USER INITIATION)

---

## 3. Phase 5 Implementation & Verification (Document Vault & OCR Pipeline)

### Task A: Privacy-Centric Document Storage & Security Architecture
- **Binary Segregation:** Document binaries are stored exclusively on secure local filesystem storage (`storage/documents/<user_id>/<doc_uuid>.<ext>`) and **NEVER in PostgreSQL**.
- **Opaque Storage References:** Opaque UUID keys prevent filename leaks, user enumeration, and direct file probing.
- **Path Traversal Protection:** Base storage directories are strictly resolved, and any attempt to navigate parent directories (`..`) is rejected with 403 Forbidden.
- **Magic Byte Verification:** File signatures are strictly validated for accepted formats before persistence:
  - PDF: `%PDF` (`\x25\x50\x44\x46`)
  - JPEG: `\xff\xd8\xff`
  - PNG: `\x89PNG\r\n\x1a\n`
  - Prevents extension spoofing (e.g. executable renamed as `.pdf`).
- **File Size & Extension Controls:** Enforces maximum limit of 10 MB and limits uploads to `pdf, jpg, jpeg, png`.
- **IDOR Protection:** Every document API endpoint enforces authenticated citizen ownership checks via JWT `sub` claims, preventing Insecure Direct Object References.

### Task B: Database Schema & Alembic Migration
- **Model Extension:** Extended `DocumentMetadata` (`backend/app/models/document.py`) with Phase 5 fields:
  - `ocr_status`: Column(String(50), default="UPLOADED", nullable=False, index=True)
  - `ocr_extracted_text`: Column(Text, nullable=True)
  - `ocr_confidence`: Column(Float, nullable=True)
  - `ocr_metadata`: Column(JSONB, nullable=False, default=dict)
  - `ocr_completed_at`: Column(DateTime(timezone=True), nullable=True)
  - `manual_review_required`: Column(Boolean, default=False, nullable=False, index=True)
  - `ocr_error_message`: Column(String(500), nullable=True)
- **Alembic Migration:** Authored `e9f8a7b6c5d4_extend_document_metadata_for_phase_5.py`.
- **Static DDL Verification:** Verified `alembic upgrade head --sql` and `alembic downgrade e9f8a7b6c5d4:7a8e5f3c9102 --sql` under `PostgresqlImpl`.

### Task C: Google Cloud Vision OCR Pipeline & Mock Fallback Adapter
- **Adapter Pattern:** Implemented `BaseOCRAdapter`, `GoogleCloudVisionAdapter`, and `MockOCRAdapter` in `backend/app/services/ocr_service.py`.
- **Production Adapter:** Connects to Google Cloud Vision API using `vision.ImageAnnotatorClient` for document text detection when credentials are provided.
- **Development/Test Adapter:** Deterministic, high-fidelity mock adapter generating authentic Indian government certificate text (Income Certificate, Caste Certificate, Domicile, NFSA Ration Card, Aadhaar Card, Land Records).
- **Edge-Case & Review Trigger:**
  - Automated threshold enforcement: confidence score < 0.70 or unreadable/blurred scan sets `ocr_status = MANUAL_REVIEW_REQUIRED` and `manual_review_required = True`.
- **Retry Capability:** Citizen can re-run OCR extraction through `POST /api/v1/documents/{document_id}/retry-ocr`.

### Task D: Scheme Document Readiness Checklist
- Implemented `GET /api/v1/documents/scheme/{scheme_id}/checklist` comparing a scheme's required documents against citizen's uploaded documents.
- Includes statutory non-guarantee disclaimer: *"Document presence in your JanMitra vault verifies readiness for official submission, but does not replace government verification or guarantee scheme approval."*

### Task E: Flutter Mobile Application (Vault Feature)
- **Models & Service:** `DocumentMetadataModel`, `SchemeDocumentChecklistModel`, and `DocumentService` handling multipart HTTP uploads and vault operations.
- **DocumentVaultScreen:** Modern citizen vault with total file counters, OCR completed count, review needed count, category filter chips, document cards with status badges and confidence chips, and floating action button.
- **UploadDocumentDialog:** Bottom sheet supporting Camera, Gallery, and Custom File Picker (PDF/Image) with live progress indicators.
- **DocumentDetailScreen:** Complete view of document metadata, extraction confidence progress bar, manual review warning banner, selectable monospace OCR text with copy-to-clipboard, retry OCR button, and delete document confirmation.
- **SchemeDocumentChecklistWidget:** Embedded in `SchemeDetailsScreen` to show document readiness checklist with one-click upload for missing documents.

### Task F: Testing & Quality Metrics
- **Backend Pytest Suite:** **82 passed, 1 skipped (live PostgreSQL test), 0 failed** across 83 tests (including 19 dedicated vault, OCR, security, and terminology audit tests).
- **Flutter Test Suite:** **14 passed, 0 failed** across `document_widgets_test.dart`, `scheme_widgets_test.dart`, and `widget_test.dart`.
- **Flutter Analysis:** **0 issues found** via `flutter analyze`.

---

## 4. Phase 5 Final Security & OCR Reliability Audit

### 4.1 Mock OCR Production Safety
- **Strict Environment Guard:** Evaluated via `is_production()`, inspecting `ENVIRONMENT == "production"` and `DEBUG is False`.
- **Zero Silent Fallback:** In production, any attempt to invoke `MockOCRAdapter` fails with an explicit error.
- **Missing Cloud Vision Credentials Handling:** In production, if Cloud Vision credentials are absent or the service is unavailable, document status transitions to `OCR_FAILED` with an explicit, sanitized error message (`"OCR extraction unavailable in production: Cloud Vision credentials not configured."`) and sets `manual_review_required = True`.
- **Simulated Text Disclaimer:** Mock-generated output is never presented as actual extracted text; it explicitly tags metadata with `is_mock: True` and an advisory note.
- **Automated Test Coverage:** Verified via `test_production_mode_strictly_disables_mock_ocr`.

### 4.2 UI & Response Terminology Alignment
- **Term Clarification:**
  - Replaced misleading `"OCR Verified"` with `"OCR Completed"` across backend status mappings, Flutter screens, models, and test assertions.
  - Replaced checklist header `"Required Documents Prepared"` with `"Required Document Types Uploaded"`.
- **Four-Way Distinction Enforced:**
  1. *Document Uploaded:* File received, magic bytes verified, stored on disk.
  2. *OCR Completed / Text Extracted:* Machine reading finished; text available for evaluation.
  3. *Manual Review Required:* Machine confidence below threshold (<0.70) or unreadable document.
  4. *Official Government Verification:* Outside app scope; never claimed or guaranteed.
- **Statutory Non-Guarantee Notice:** Prominently displayed across Flutter screens and API responses to prevent user misconceptions regarding official scheme eligibility.

### 4.3 Secure File Storage & Path Traversal Protections
- **Storage Confinement:** Base directory path canonicalization ensures all uploads resolve strictly under configured `storage/documents/<user_id>/`. Path traversal payloads (`../`, `..\\`) are rejected with 403 Forbidden.
- **Header Injection & Response Splitting Defense:** Implemented `sanitize_header_filename` stripping carriage returns (`\r`), line feeds (`\n`), quotes, semicolons, and control characters in `Content-Disposition: inline; filename="..."`. Added `X-Content-Type-Options: nosniff`.
- **Transaction Rollback & Deletion Consistency:**
  - In `upload_document`: Any database or OCR failure triggers disk unlink to prevent orphaned files.
  - In `delete_document`: Database transaction rollback is enforced if an error occurs before filesystem unlink.
- **Encryption-at-Rest Architecture:** Transparently documented that application-level file encryption is not implemented; filesystem confidentiality relies on OS/volume-level BitLocker/LUKS encryption.

### 4.4 Sensitive OCR Data Protection
- **Log Sanitation:** Full OCR extracted text and raw document strings are excluded from application loggers. Verified via caplog inspection in `test_no_sensitive_ocr_text_in_logs`.
- **Error Message Sanitation:** Implemented `sanitize_ocr_error_message(msg)` to strip local Windows/Unix absolute paths (`C:\Users\...`, `/home/...`) from failure messages stored in the database.
- **Owner-Only Access (IDOR Prevention):** All endpoints verify `document.user_id == current_user.id`.
- **Purge on Deletion:** Deletion permanently unlinks the physical file from disk and zeroes metadata/text from PostgreSQL.

### 4.5 Google Cloud Vision PDF Processing
- **Format-Specific Extraction:** Synchronous `batch_annotate_files` handles multi-page PDFs (pages 1 to 5) directly using in-memory byte payloads, avoiding external GCS bucket requirements for standard applications.
- **Architectural Boundary:** Documented that PDFs exceeding 5 pages require asynchronous batch annotation (`async_batch_annotate_files`) with Google Cloud Storage staging.
- **Concurrent Processing Protection:** `retry_ocr` endpoint returns `409 Conflict` if the document is already in `PROCESSING` status.

### 4.6 Verification Summary
- **Backend Tests:** 82 passed, 1 skipped, 0 failed in 14.93s.
- **Flutter Widget Tests:** 14 passed, 0 failed.
- **Flutter Analyze:** 0 issues found.
- **Alembic Static SQL:** Verified PostgreSQL DDL upgrade/downgrade.

- [ ] **Phase 8:** Final Hardening, Integration & Academic Defense Preparation (PENDING USER INITIATION)
