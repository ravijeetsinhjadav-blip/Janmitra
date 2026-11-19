# JanMitra Assist – Implementation Progress Tracker

**Project Name:** JanMitra Assist – AI-Powered Government Service Eligibility and Document Intelligence System  
**Academic Target:** MCA Major Project  
**Current Phase:** Phase 7 (Master End-to-End Application Assistance, Subscriptions, Payments & Admin Integration) – COMPLETED & CONDITIONALLY APPROVED


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
- [x] **Phase 6:** AI Advisory & Readiness Assessment Engine
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

---

## 5. Phase 6 Implementation & Verification (AI Advisory & Readiness Assessment Engine)

### Task A: Database Model Extension & Alembic Migration
- **Model `SchemeKnowledgeChunk` (`backend/app/models/scheme_knowledge.py`):**
  - Stores structured, chunked clauses from official government scheme guidelines (`chunk_title`, `chunk_category`, `chunk_content`, `source_url`, `source_title`, `source_reference`, `source_freshness_status`, `is_demo_data`, `embedding`).
- **Extended `Assessment` (`backend/app/models/assessment.py`):**
  - `advisory_guidance`: JSONB storing structured AI-generated synthesis, condition notes, and source citations.
  - `readiness_breakdown`: JSONB storing multi-dimensional component scores and document discrepancy checks.
  - `language`: VARCHAR(10) storing citizen language preference (`en`, `hi`, `gu`).
- **Alembic Migration `f1a2b3c4d5e6`:** Verified static DDL upgrade and downgrade for PostgreSQL.

### Task B: RAG Government Scheme Knowledge Retrieval
- **Service `RAGService` (`backend/app/services/rag_service.py`):**
  - Seeded verified official knowledge excerpts across all 5 demo schemes (PM-KISAN, AB-PMJAY, PMAY-G, NSP Scholarship, Maharashtra MJPJAY).
  - Preserves source citations, guideline references, and freshness states (`Verified Official Source`, `Pending Verification`, `Review Required`, `Stale`).
  - Token-overlap ranking selects top-k most relevant clauses without introducing unapproved vector databases.
  - Factual grounding constraint: AI guidance relies exclusively on retrieved chunks and structured criteria; no hallucination of income/age limits or application URLs.

### Task C: Cloud LLM Provider Adapter & Production Safety
- **Adapter Hierarchy (`backend/app/services/llm_service.py`):**
  - `BaseLLMAdapter`: Abstract interface with `generate_advisory(...)`.
  - `GeminiLLMAdapter`: Production cloud adapter connecting to Google Gemini REST API via `httpx` with configurable timeout and retries.
  - `MockLLMAdapter`: Deterministic mock adapter for development/testing with zero external token costs, outputting authentic civic guidance in English, Hindi, and Gujarati.
- **Production Safety Isolation:** In production (`ENVIRONMENT == 'production'` or `DEBUG is False`), `MockLLMAdapter` cannot execute. Missing cloud credentials raise explicit errors rather than falling back silently.

### Task D: Deterministic Engine Supremacy & AI Safety
- **Strict Separation:** The deterministic eligibility engine (Phase 4) remains the sole source of eligibility classifications (`Potentially Eligible`, `Not Eligible Based on Available Information`, `Insufficient Information`). The LLM **never overrides** this decision.
- **Prompt Injection Defense:** Untrusted citizen OCR text and retrieved external data are encapsulated inside XML delimiters (`<citizen_ocr_data>`, `<retrieved_scheme_knowledge>`) with explicit system instructions prohibiting instruction-following within those tags.
- **PII Minimization:** Masking strips 12-digit Aadhaar numbers (`XXXX-XXXX-1234`) and Indian mobile numbers (`XXXXXXX210`) before prompt transmission. Full OCR text is excluded from logs.

### Task E: Multi-Dimensional Application Readiness Engine
- **Service `ReadinessService` (`backend/app/services/readiness_service.py`):**
  - Computes 4 transparent component scores (0–100%):
    1. `criteria_match_percentage`: From Phase 4 deterministic engine.
    2. `document_coverage_percentage`: Uploaded vs required document types.
    3. `information_completeness_percentage`: Profile completeness against scheme fields.
    4. `consistency_score`: Name and DOB cross-validation between profile and OCR extraction.
  - Calculates composite weighted Readiness Score:
    $$\text{Readiness Score} = 0.40 \times \text{Criteria Match} + 0.30 \times \text{Doc Coverage} + 0.15 \times \text{Completeness} + 0.15 \times \text{Consistency}$$
  - Classifies consistency status (`Consistent`, `Discrepancy Detected`, `Review Required`).
  - Statutory non-guarantee advisory disclaimers displayed on all outputs.

### Task F: Flutter Citizen Client Integration
- **Models & Service:** `AdvisoryAssessmentModel`, `ReadinessBreakdownModel`, and `AdvisoryService` in `features/readiness`.
- **`AIAdvisoryScreen`:**
  - Multilingual language toggle chips (`EN`, `हिंदी`, `ગુજરાતી`) with live re-generation.
  - Circular readiness gauge and 4-bar progress indicator.
  - Discrepancy warning banner with specific field mismatch alerts.
  - Uploaded vs Missing document type chips with one-click navigation to Document Vault.
  - Step-by-step actionable preparation checklist.
  - Official government portal guidance and clipboard copy button.
  - Verified source references with freshness badges.
- **Cross-Screen Integration:** Added "View AI Advisory & Readiness Report" button to `EligibilityResultScreen` and activated the Phase 6 feature card on `HomeScreen`.

### Task G: Phase 6 Independent Final Audit & Security Hardening
- **Readiness Reliability Corrections (`readiness_service.py`):**
  - Excluded `OCR_FAILED` documents from coverage (0% credit, flagged as failed in missing documents list).
  - Granted partial credit (0.5 / 50%) for `MANUAL_REVIEW_REQUIRED` and low-confidence scans (<0.70).
  - Proportional consistency score instead of arbitrary 75%/50% (deductions of -20% per discrepancy and -10% per review item).
  - When citizen has uploaded 0 documents, set status to `"Not Evaluated (No Documents)"` and consistency score to `0.0`.
  - Eligibility status capping: Capped overall readiness at max 35.0% if status is `Not Eligible Based on Available Information`, and at max 50.0% if `Insufficient Information`.
- **RAG Source Authenticity (`rag_service.py`, `advisory_service.py`):**
  - Handled freshness states (`Pending Verification`, `Stale`, `Review Required`) with explicit `[WARNING: ...]` tags in citations and prompt guidance.
  - Tagged all demo chunks with `is_demo_data=True`. Handled empty chunks state with explicit anti-hallucination prompt guidance.
- **Prompt Injection & Output Validation (`llm_service.py`):**
  - Stripped XML breakout boundary tags (`</citizen_ocr_data>`, `</retrieved_scheme_knowledge>`, `</system>`, backticks) via `sanitize_untrusted_prompt_text`.
  - Enforced strict output validation against Pydantic schema `AdvisoryLLMOutputSchema` for Gemini responses.
- **PII Minimization (`llm_service.py`):**
  - Excluded raw citizen names and exact dates of birth from LLM payloads via `sanitize_conditions_breakdown_for_llm` (`[MASKED_CITIZEN_NAME]`, `[MASKED_DOB]`, `[MASKED_PHONE]`).
  - Minimized discrepancy strings via `sanitize_discrepancies_for_llm`. Full raw OCR text is excluded from prompt payloads.
- **Flutter UI Enhancements (`ai_advisory_screen.dart`):**
  - Dynamic status styling for `Not Evaluated (No Documents)`, `Discrepancy Detected`, `Review Required`, and `Consistent`.
  - Freshness badge color cues for official citations.
- **Testing & Quality Metrics:**
  - **Backend Pytest Suite:** **99 passed, 1 skipped (live PostgreSQL), 0 failed** across 100 tests (including 17 dedicated Phase 6 advisory, RAG, readiness, prompt injection, and PII tests).
  - **Flutter Test Suite:** **18 passed, 0 failed** across `advisory_widgets_test.dart`, `document_widgets_test.dart`, `scheme_widgets_test.dart`, and `widget_test.dart`.
  - **Flutter Analysis:** **0 issues found** via `flutter analyze`.
  - **Alembic Static SQL:** Verified clean generation through migration `f1a2b3c4d5e6`.

---

## 3. Phase 7.1 Implementation: Application Assistance Module

### Task A: Data Models & API Schemas
- Implemented comprehensive Pydantic schemas in `backend/app/schemas/assistance.py`:
  - `DocumentPreparationStatusItem`: Status classification (`Ready for Application Preparation`, `Available`, `Missing`, `Manual Review Required`, `Needs Correction`, `Processing Failed`).
  - `ChecklistItem`: Actionable requirement tracking (`document`, `profile_field`, `declaration`, `portal_action`), mandatory flag, and completion state.
  - `ApplicantInfoRequirement`: Detailed demographic/administrative portal fields.
  - `SupportingDocumentSpecification`: Acceptable formats, file sizes, validity periods, and recognized issuing authorities.
  - `PortalStepInstruction`: Sequence of steps on the official government portal.
  - `ApplicationInfoGuide`: Complete scheme-specific preparation guide with common mistakes and precautions.
  - `ApplicationAssistanceResponse`: Aggregated response connecting scheme discovery, eligibility assessment, readiness score, document vault statuses, interactive checklist, and official portal directions.
  - `ChecklistUpdateResponse`: Interactive toggle response with progress metrics.

### Task B: Assistance Service & Preparation Logic
- Created `AssistanceService` in `backend/app/services/assistance_service.py`:
  - `generate_or_get_assistance`: Synthesizes scheme information, citizen profile, uploaded vault documents, readiness scores, and AI/RAG guide into a personalized application preparation packet.
  - **Document Classification Logic:**
    - `Ready for Application Preparation`: Document uploaded with high OCR confidence (>=0.70) and no manual review flag.
    - `Manual Review Required`: Document flagged for manual inspection or has OCR confidence <0.70.
    - `Processing Failed`: Document encountered `OCR_FAILED`.
    - `Needs Correction`: Document has unresolved profile-vault inconsistencies.
    - `Missing`: Required document not found in citizen's vault.
  - **Normalized Civic Document Matching:** Added `_match_doc_types` to normalize whitespace, underscores, and common civic document root tokens (`aadhaar`, `ration`, `caste`, `domicile`, `residence`, `income`, `land`, `passbook`, `bank`).
  - **Checklist State Persistence:** Maintained per-citizen, per-scheme checklist completion state in `Assessment.result_data["completed_checklist_items"]` (JSONB) without requiring database migrations.
  - `toggle_checklist_item`: Safely adds/removes item IDs in `completed_checklist_items` with IDOR validation (verifying user ownership of the assessment).

### Task C: Multilingual LLM Application Guide Generation
- Extended `BaseLLMAdapter`, `GeminiLLMAdapter`, and `MockLLMAdapter` in `backend/app/services/llm_service.py`:
  - `ApplicationGuideLLMOutputSchema`: Strict Pydantic schema validation for LLM responses.
  - Multilingual support: Authentic civic guidance in English (`en`), Hindi (`hi`), and Gujarati (`gu`).
  - Common Mistakes Highlights: Outdated IFSC codes for merged public sector banks (e.g., Allahabad Bank, Syndicate Bank, Corporation Bank), spelling discrepancies between Aadhaar and bank passbooks, expired income/caste certificates, and land area unit conversions (Bigha/Guntha to Hectares/Acres).
  - Security hardening: Prompt injection defense via XML delimiters and PII minimization (masking Aadhaar and phone numbers).
  - Production safety: Strict block preventing mock LLM execution in production mode.

### Task D: API Endpoints
- Mounted under prefix `/api/v1/assistance` in `backend/app/api/v1/endpoints/assistance.py`:
  - `POST /api/v1/assistance/schemes/{scheme_id}/prepare`: Prepares or retrieves personalized assistance for authenticated citizen.
  - `PATCH /api/v1/assistance/schemes/{scheme_id}/checklist/{item_id}`: Toggles interactive preparation checklist item completion.
  - `GET /api/v1/assistance/schemes/{scheme_id}/guide`: Public/authenticated retrieval of scheme information guide.

### Task E: Flutter Application Assistance Client
- Built Flutter client feature under `mobile_app/lib/features/assistance/`:
  - `models/assistance_models.dart`: Complete deserialization and data structures for assistance responses, checklists, guides, and status items.
  - `services/assistance_service.dart`: API client methods with JWT token headers.
  - `presentation/screens/application_assistance_screen.dart`:
    - Statutory Non-Submission Advisory Banner at the top.
    - Scheme header with category, department, and demo data badge.
    - Multilingual language toggle chips (`English`, `हिंदी`, `ગુજરાતી`) with immediate reloading.
    - Readiness Overview with Criteria Match % and Overall Readiness Score.
    - Interactive Preparation Checklist with progress bar ("X of Y done"), individual checkboxes, and non-submission alert.
    - Document Preparation Status list with visual badges and "Open Vault" navigation.
    - Scheme Information Guide with expandable cards: Common Mistakes to Avoid, Submission Precautions, Required Info, Document Specs, Declarations, and Portal Filing Sequence.
    - Official Government Portal card with verified URL and clipboard copy action.
- Integrated Navigation:
  - Added "Application Preparation & Checklists" card to `home_screen.dart`.
  - Added "Prepare Application with Checklist" button to `ai_advisory_screen.dart`.
  - Added "Prepare Application & Interactive Checklist" button to `eligibility_result_screen.dart`.
  - Added "Prepare Application Guide & Checklist" button to `scheme_details_screen.dart`.

### Task F: Verification & Quality Assurance
- **Backend Tests:** **108 passed, 1 skipped (live PostgreSQL), 0 failed** across 109 tests:
  - 9 dedicated Phase 7.1 assistance tests covering preparation, missing/available document classification, OCR failed/review statuses, interactive checklist toggling, IDOR access protection, 404 validation, multilingual Hindi/Gujarati outputs, and public guide endpoints.
- **Flutter Tests:** **24 passed, 0 failed** across `assistance_widgets_test.dart`, `advisory_widgets_test.dart`, `document_widgets_test.dart`, `scheme_widgets_test.dart`, and `widget_test.dart`.
- **Flutter Analysis:** **0 issues found** via `flutter analyze`.
- **Database Migrations:** Clean static SQL generation verified via `alembic upgrade head --sql`.

---

---

## 3. Phase 7.2 Implementation: Assisted Service & Payments Module

### Task A: Data Models & Database Migrations
- Created `PaymentTransaction` database model in `backend/app/models/payment.py`:
  - Columns: `id` (UUID pk), `user_id` (FK users), `subscription_id` (FK subscriptions, nullable), `razorpay_order_id` (unique), `razorpay_payment_id` (unique, nullable), `razorpay_signature`, `amount`, `currency` (INR), `plan_type` (premium), `billing_cycle` (monthly/yearly), `payment_status` (created, captured, failed, refunded), `payment_method` (upi, card, netbanking, qr), `error_code`, `error_description`, `idempotency_key` (unique), `payment_metadata` (JSONB), `created_at`, `updated_at`.
  - Added relationships in `User` and `Subscription` models (`user.payments`, `subscription.payments`).
- Authored Alembic migration `b2c3d4e5f6a7_add_phase_7_2_payment_transactions.py`.
- Verified static SQL compilation for PostgreSQL via `alembic upgrade head --sql` confirming foreign keys, indexes, and column comments.

### Task B: Cryptographic Payment Gateway & Security Service
- Implemented `PaymentService` in `backend/app/services/payment_service.py`:
  - **Secure Order Creation:** Generates Razorpay orders with server-controlled amount (₹99 for monthly, ₹799 for yearly) in paise; prevents client price tampering.
  - **Cryptographic Signature Verification:** Computes HMAC-SHA256 signature using `RAZORPAY_KEY_SECRET` over `${order_id}|${payment_id}` and compares using timing-attack safe `hmac.compare_digest`.
  - **Idempotent Webhook Processing:** Validates Razorpay webhook signatures via `RAZORPAY_WEBHOOK_SECRET`; enforces uniqueness on `idempotency_key` (`webhook_event_id` or `payment_id:event`) to prevent replay attacks and duplicate subscription extensions.
  - **Failure Handling:** Captures `payment.failed` webhooks and records error codes and descriptions while leaving subscription state untouched.
  - **Dev Mode Emulation:** In development/testing environments (`RAZORPAY_DEV_MODE=True`), simulates order creation and signature verification without calling external APIs.

### Task C: Subscription Lifecycle & Quota Enforcement
- Implemented `SubscriptionService` in `backend/app/services/subscription_service.py`:
  - **Plan Catalog:** Free Plan (₹0) and Premium Plan (₹99/month, ₹799/year - 33% discount).
  - **Quota Calculation:**
    - Free Plan: Up to 3 document analyses/month and 5 AI guidance sessions/month.
    - Premium Plan: Up to 30 document analyses/month and 100 AI guidance sessions/month.
    - Calendar-month dynamic calculation: computes usage from `DocumentMetadata` and `Assessment` records created within the current calendar month cycle.
  - **Quota Guards:**
    - `POST /api/v1/documents/upload` enforces `enforce_document_analysis_quota`: returns HTTP 403 Forbidden with detailed upgrade requirement when monthly quota is exhausted.
    - `POST /api/v1/advisory/schemes/{scheme_id}/assess` enforces `enforce_ai_guidance_quota`: returns HTTP 403 Forbidden when guidance sessions are exhausted.
  - **Activation & Extension:** Updates existing active subscriptions or provisions new ones with accurate start/end dates (30 days for monthly, 365 days for yearly).

### Task D: API Endpoints
- Mounted endpoints in `backend/app/api/v1/endpoints/`:
  - `GET /api/v1/subscriptions/plans`: Public subscription plans catalog.
  - `GET /api/v1/subscriptions/me`: Authenticated citizen's current subscription, status, validity, and remaining usage quotas.
  - `POST /api/v1/payments/create-order`: Authenticated order generation.
  - `POST /api/v1/payments/verify`: Authenticated cryptographic signature verification and instant Premium activation.
  - `POST /api/v1/payments/webhook`: Server-to-server webhook callback with signature validation and idempotency protection.
  - `GET /api/v1/payments/history`: Authenticated user transaction history.

### Task E: Flutter Mobile Application
- Built subscription feature under `mobile_app/lib/features/subscription/`:
  - `models/subscription_models.dart`: JSON models for plans, quotas, citizen subscription, orders, and payment transactions.
  - `services/subscription_service.dart`: API client methods with JWT token headers.
  - `presentation/screens/subscription_plans_screen.dart`:
    - Current plan and active status badge.
    - Monthly Quota indicators with live progress bars.
    - Monthly (₹99) vs Annual (₹799, "Save 33%") billing cycle toggle.
    - Free vs Premium feature comparison cards.
    - Razorpay payment bottom-sheet modal supporting UPI, QR code, and Debit/Credit cards.
    - Statutory Non-Government preparation disclaimer notice.
  - `presentation/screens/payment_success_screen.dart`:
    - Confirmation receipt with transaction ID, plan tier, validity period, and quota breakdown.
  - `presentation/screens/payment_failure_screen.dart`:
    - Failure explanation, order ID, retry button, and support contact navigation.
  - `presentation/screens/payment_history_screen.dart`:
    - Chronological list of user transactions with status badges (CAPTURED, FAILED), payment methods, and timestamps.
- Navigation integration:
  - Added "JanMitra Premium & Assisted Service" card on `home_screen.dart`.

### Task F: Verification & Quality Assurance
- **Backend Tests:** **122 passed, 1 skipped (live PostgreSQL), 0 failed** across 123 tests:
  - 14 dedicated Phase 7.2 tests covering plans catalog, quota calculation, document upload quota enforcement (HTTP 403), AI guidance quota enforcement (HTTP 403), order creation, signature verification, payment activation, webhook processing, webhook idempotency, payment failure handling, and payment history.
- **Flutter Tests:** All tests passing across `subscription_widgets_test.dart`, `assistance_widgets_test.dart`, `advisory_widgets_test.dart`, `document_widgets_test.dart`, `scheme_widgets_test.dart`, and `widget_test.dart`.
- **Flutter Analysis:** **0 issues found** via `flutter analyze`.
- **Database Migrations:** Clean static SQL generation verified via `alembic upgrade head --sql`.

---

- [x] **Phase 7.1:** Application Assistance Module (COMPLETED & VERIFIED)
- [x] **Phase 7.2:** Assisted Service, Subscription & Payment Integration (COMPLETED & VERIFIED)
- [x] **Phase 7 Master:** End-to-End Application Assistance, Subscriptions, Payments & Admin Integration (COMPLETED & CONDITIONALLY APPROVED)
- [ ] **Phase 8:** Final Hardening, Integration & Academic Defense Preparation (PENDING USER INITIATION)


---

## 4. Phase 7.2 Security Audit & Remediation (SEC-01 to SEC-10)

Following an independent security audit of commit `ac81e1c`, comprehensive technical remediation was executed and verified for all findings **SEC-01 through SEC-10**:

### Remediated Security Findings & Verified Architectural Controls

1. **Client-Side Secret Elimination (`SEC-01`, `SEC-02`):**
   - Removed all hardcoded test secrets (`devSecret`) and client-side HMAC signature computations from `mobile_app/lib/features/subscription/presentation/screens/subscription_plans_screen.dart`.
   - Removed `import 'package:crypto/crypto.dart'` from Flutter payment workflows.
   - Integrated official `razorpay_flutter: ^1.4.7` SDK with a decoupled adapter pattern (`RazorpayCheckoutAdapter`).
   - `LiveRazorpayAdapter` delegates to native Razorpay checkout on Android/iOS; `MockRazorpayAdapter` provides deterministic test execution for headless CI without platform channel errors.
   - Mobile client only receives `(paymentId, orderId, signature)` from the gateway callback and forwards them to `POST /api/v1/payments/verify`.

2. **Authoritative Gateway-Side Verification (`SEC-03`):**
   - In `backend/app/services/payment_service.py` (`verify_and_capture_payment`):
   - In production mode (`not settings.RAZORPAY_DEV_MODE`), directly queries `GET https://api.razorpay.com/v1/payments/{payment_id}` via `httpx.Client(timeout=10.0)` with HTTP Basic Auth.
   - Validates that:
     - Gateway status is strictly `"captured"` (rejecting `"authorized"` or `"failed"`).
     - Gateway amount matches expected plan price in paise (9,900 for monthly, 79,900 for yearly).
     - Gateway currency is strictly `"INR"`.
     - Gateway order ID matches local `tx.razorpay_order_id`.

3. **Webhook Concurrency, Deduplication & Pessimistic Row Locking (`SEC-04`):**
   - Created dedicated `webhook_events` table tracking `event_id` (unique index), `event_type`, `order_id`, `payment_id`, `status`, `payload_summary`, and receipt timestamp.
   - In `PaymentService.process_webhook`:
     - Checks `WebhookEvent.event_id`; immediately returns `idempotent_duplicate` on replay.
     - Acquires pessimistic exclusive row lock on `PaymentTransaction` using `db.query(PaymentTransaction).with_for_update()`.
     - Prevents simultaneous webhook deliveries from executing duplicate subscription extensions.

4. **Fair Quota Filtering (`SEC-05`):**
   - Updated `SubscriptionService.get_quota_status` to count only usable OCR outcomes:
     `DocumentProcessingStatus.OCR_COMPLETED` and `DocumentProcessingStatus.MANUAL_REVIEW_REQUIRED`.
   - Explicitly excludes `DocumentProcessingStatus.OCR_FAILED` and pending states, ensuring citizens are never unfairly penalized for failed OCR scans.

5. **Application Assistance Quota Enforcement & LLM Guide Caching (`SEC-06`):**
   - In `backend/app/api/v1/endpoints/assistance.py`: Enforced `SubscriptionService.enforce_ai_guidance_quota(db=db, user_id=current_user.id)` on `POST /schemes/{scheme_id}/prepare`, returning HTTP 403 Forbidden when quota is exhausted.
   - Added `application_guide_cache = Column(JSONB, server_default="{}", nullable=False)` to `Scheme` model.
   - In `AssistanceService.get_scheme_guide`: Serves static general scheme guides directly from PostgreSQL cache, eliminating unauthenticated LLM API consumption.

6. **Full vs. Partial Refund Semantics (`SEC-07`):**
   - In `PaymentService.process_webhook`:
     - Handled `refund.processed` and `refund.created` events.
     - **Full Refund** (`refund_amount >= full_amount`): Sets `payment_status = "refunded"`, revokes active Premium subscription (`status = "refunded"`, `is_active = False`, `end_date = now()`), reverting citizen to Free tier.
     - **Partial Refund** (`refund_amount < full_amount`): Retains active subscription until natural expiry while logging sanitized audit telemetry in `payment_metadata`.

7. **Production Configuration Model Validation (`SEC-08`):**
   - In `backend/app/core/config.py`: Added Pydantic `model_validator(mode="after")` to `Settings` that fails startup with explicit error if `ENVIRONMENT == "production"` and `RAZORPAY_DEV_MODE = True` or default test keys are configured.

8. **Safety Ceiling Documentation (`SEC-09`):**
   - Formalized `PREMIUM_MONTHLY_AI_GUIDANCE_LIMIT = 100` as an approved safety ceiling against LLM exhaustion.

9. **PII Minimization (`SEC-10`):**
   - Implemented `_mask_string` and `_sanitize_payment_entity` in `payment_service.py`.
   - Contact numbers, emails, and VPAs in webhook payloads are masked before storage in PostgreSQL.

### Verified Test Results

- **Backend Test Suite:** **135 passed, 3 skipped (live PostgreSQL), 0 failed** across 138 tests:
  - 26 dedicated tests in `tests/test_payments_and_subscriptions.py` verifying catalog, quotas, exclusions, gateway checks, webhook deduplication, full/partial refunds, dispute state machine, PII masking, config validation, assistance caching, failed OCR zero-quota consumption, invalid upload zero-quota consumption, retry OCR quota semantics, and stale processing self-healing.
  - 7 tests in `tests/test_postgres_integration.py` verifying PostgreSQL DDL dialect compilation and multi-threaded concurrency locking (`TestPostgresConcurrencyLive`).
- **Flutter Test Suite:** **35 passed, 0 failed** across all test suites:
  - 11 dedicated tests in `test/subscription_widgets_test.dart` verifying models, `MockRazorpayAdapter` callbacks, and UI flows.
- **Dart Analysis:** **0 issues found** via `dart analyze lib/features/subscription`.
- **Database Migrations:** Migrations `c4d5e6f7a8b9` and `d5e6f7a8b9c0` verified via `alembic upgrade head --sql`.

---

## Phase 7.2 Critical Security & Quota Remediation Summary

1. **Document Quota Lifecycle & Concurrency (SEC-05, SEC-06):**
   - Implemented three-phase reservation/finalization/release lifecycle in `DocumentService`:
     - Phase 0: File size, format, and magic byte validation execute before quota checks. Invalid files return HTTP 400 with 0 quota consumed.
     - Phase 1: `SubscriptionService.reserve_document_analysis_quota` checks `completed + in_flight < limit` under row-level lock `with_for_update()`, creating `DocumentMetadata` in `PROCESSING` status.
     - Phase 2: OCR runs with structured exception handling.
     - Phase 3: Successful OCR (`OCR_COMPLETED`, `MANUAL_REVIEW_REQUIRED`) invokes `finalize_document_analysis` (1 quota unit consumed). Failed OCR or exceptions invoke `release_document_analysis_quota`, setting `ocr_status = OCR_FAILED` (0 quota units consumed).
   - In `DocumentService.retry_ocr`: Retrying a failed document reserves quota and only finalizes on success; retrying an already completed document updates results without double-charging.
   - Built self-healing crash recovery (`auto_heal_stale_processing_documents`): Stale records in `PROCESSING` status older than 5 minutes (300s) are automatically transitioned to `OCR_FAILED`, preventing orphaned in-flight reservations from locking citizen quotas indefinitely.

2. **Payment Concurrency & Webhook Idempotency (SEC-04):**
   - Implemented row-level pessimistic locking (`with_for_update()`) on `payment_transactions` across `/payments/verify` and `/payments/webhook`.
   - Prevented race conditions between simultaneous user verification and webhook processing.
   - Handled duplicate webhooks via `WebhookEvent.event_id` unique constraint with `IntegrityError` rollback.

3. **Cumulative Refund & Dispute State Machine (SEC-07):**
   - Tracked all refunds in `tx.refunds_log` with paise-to-INR conversions (`round(paise / 100.0, 2)`).
   - Handled full vs. partial refunds: full refunds (`amount_refunded >= amount`) revoke subscriptions immediately, while partial refunds retain active subscriptions.
   - Implemented dispute state transitions (`created`, `under_review`, `won`, `lost`, `closed`), automatically revoking subscriptions with `status = "revoked_chargeback"` on lost disputes.

4. **Webhook Financial Privacy Allowlists (SEC-10):**
   - Enforced strict allowlists (`PAYMENT_ENTITY_ALLOWLIST`, `REFUND_ENTITY_ALLOWLIST`, `DISPUTE_ENTITY_ALLOWLIST`).
   - Stripped all customer names, billing addresses, acquirer data, and notes. Contact numbers, emails, and VPAs are masked to show only trailing 4 characters.

---

## 5. Phase 7 Master Implementation & Verification Audit (Sections A – J)

Completed the comprehensive Phase 7 Master Implementation across the full-stack architecture (FastAPI backend, PostgreSQL database, React admin dashboard, and Flutter mobile client):

### 5.1 Architecture & Implementation Highlights
- **Section A (Application Preparation Packet Export):**
  - Added `ApplicationPreparationPacketResponse` schema in `backend/app/schemas/assistance.py`.
  - Implemented `export_preparation_packet` in `backend/app/services/assistance_service.py` aggregating scheme summary, criteria match percentage, document readiness breakdown, actionable checklist, verified nodal portal steps, common mistakes, and mandatory statutory disclaimer.
  - Mounted `GET /api/v1/assistance/schemes/{scheme_id}/packet-export` with active citizen authentication.
  - Strict PII minimization verified: Aadhaar/financial numbers excluded from exported payloads.
- **Section B (Dynamic Vault & Checklist Synchronization):**
  - Refactored `generate_or_get_assistance` in `assistance_service.py` to decouple readiness from completion: `category == "document"` checklist items use `is_completed = is_ready`.
  - Automatic synchronization on document deletion: removing a document from Document Vault reverts its readiness to `Missing` and unchecks the corresponding checklist item.
- **Section C (Multilingual Guidance & Dev Fallback):**
  - Supported localized guidance in English, Hindi (Devanagari script), and Gujarati.
  - Hardened non-production runtime: wrapped `generate_application_guide` in `assistance_service.py` with safe fallback to `MockLLMAdapter` when `GEMINI_API_KEY` is unset in development mode, eliminating unhandled HTTP 500 errors.
- **Section D (Subscription Quotas & Fair Enforcement):**
  - Free Tier: 3 document OCR analyses and 5 AI guidance sessions.
  - Premium Tier: 30 document OCR analyses and 100 AI guidance sessions safety ceiling.
  - Failed OCR scans and unparseable uploads consume zero quota units (`reserve` $\to$ `release` lifecycle).
- **Section E (Payment Concurrency & Webhook Deduplication):**
  - Production-grade Razorpay lifecycle with server-authoritative pricing (₹99 monthly, ₹799 yearly).
  - Pessimistic row locking (`with_for_update()`) on `PaymentTransaction` prevents race conditions between client-initiated `/payments/verify` and gateway webhook callbacks.
  - Webhook deduplication via `WebhookEvent.event_id` unique index.
- **Section F (Admin Dashboard Server-Side Pagination):**
  - Upgraded `admin_dashboard/src/components/SubscriptionMonitoring.jsx` to consume backend pagination (`page`, `page_size=25`, `search`, `status`).
  - Added accessible pagination controls with Prev/Next buttons, page indicators, and automatic reset to page 1 on search or filter adjustments.
  - Built production bundle cleanly with `npm run build` in 1.49s.
- **Section G (Playwright Headless Chrome Browser E2E Suite):**
  - Expanded `backend/tests/test_browser_e2e_real.py` with Steps 9B & 9C:
    - Step 9B: Navigated to Subscriptions & Revenue panel, validated KPI metric cards (MRR, Total Revenue, Active Subscriptions), and verified subscription audit table pagination.
    - Step 9C: Switched to Razorpay Transactions tab, verified transaction audit table, search filtering, and pagination.
- **Section H (Live PostgreSQL Payment vs Webhook Race Test):**
  - Implemented `test_live_postgres_concurrent_payment_verification_and_webhook_race` in `tests/test_postgres_integration.py`.
  - Used `threading.Barrier(2)` and `ThreadPoolExecutor(max_workers=2)` to race `verify_and_capture_payment` against `process_webhook` under `with_for_update()`.
  - Confirmed exactly one activation, idempotent response, transaction `captured`, active subscription, and premium quota status (`UsageQuotaStatus`). Strict cleanup in `try...finally:`.

### 5.2 Multi-Platform Verification Summary Table

| Test Suite / Inspection | Command Executed | Result / Metrics | Status |
| :--- | :--- | :--- | :--- |
| **Backend Full Discovery Suite** | `pytest tests -q` | **371 passed, 5 skipped, 0 failed** (187.42s) | **PASSED** |
| **PostgreSQL Integration Suite** | `pytest tests/test_postgres_integration.py -v` | **17 passed, 0 failed** (2.48s) | **PASSED** |
| **Assistance & Preparation Packet** | `pytest tests/test_assistance.py -v` | **13 passed, 0 failed** (8.62s) | **PASSED** |
| **Real Browser E2E (Chrome)** | `pytest tests/test_browser_e2e_real.py -v -s` | **1 passed, 0 failed** (21.35s) | **PASSED** |
| **Admin Production Build** | `npm run build` (`admin_dashboard`) | Built in 1.49s, exit code 0 | **PASSED** |
| **Flutter Analysis** | `flutter analyze` (`mobile_app`) | **No issues found!** (ran in 274.8s) | **PASSED** |
| **Flutter Test Suite** | `flutter test` (`mobile_app`) | **151 passed, 0 failed** (54s) | **PASSED** |
| **Git Hygiene Check** | `git diff --check` | 0 whitespace/patch errors, exit code 0 | **PASSED** |
| **Live Third-Party Cloud Tests** | `pytest tests/test_real_providers.py -v` | **5 skipped** (cleanly skipped due to unset cloud credentials) | **SKIPPED (BY DESIGN)** |

### 5.3 Formal Phase 7 Status: CONDITIONALLY APPROVED
- All core business logic, database migrations, security controls, admin pagination, browser workflows, and mobile client logic are **100% PASSED**.
- The 5 live third-party cloud tests (`test_live_gemini_advisory_call_english`, `test_live_gemini_advisory_call_hindi`, `test_live_gemini_application_guide_call`, `test_live_cloud_vision_image_ocr_call`, `test_live_cloud_vision_pdf_ocr_call`) intentionally skip in offline / unconfigured environments.
- Therefore, the Phase 7 sign-off is formally designated **CONDITIONALLY APPROVED** until production credentials for Gemini and Google Cloud Vision are supplied in the production deployment pipeline.
