# JanMitra Assist – Implementation Progress Tracker

**Project Name:** JanMitra Assist – AI-Powered Government Service Eligibility and Document Intelligence System  
**Academic Target:** MCA Major Project  
**Current Phase:** Phase 4 (Government Scheme Discovery & Eligibility Engine) – COMPLETED & AUDITED

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

### Task E: Testing & Quality Verification
- **Backend Pytest Suite:**
  - `backend/tests/test_schemes.py`: 18 tests covering operators, birthday boundaries, mixed conditions, source verification, and history isolation (100% passed).
  - Complete backend test suite: **52 passed, 1 skipped (live PostgreSQL network test), 0 failed**.
- **Flutter Testing & Analysis:**
  - `mobile_app/test/scheme_widgets_test.dart`: 4 comprehensive widget tests covering scheme discovery, details, eligibility results, and home screen card.
  - Complete Flutter test suite: **7 passed, 0 failed**.
  - `flutter analyze`: **0 issues found** (clean static analysis).

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
- [ ] **Phase 5:** Document Vault & OCR Pipeline (PENDING USER INITIATION)
- [ ] **Phase 6:** AI Advisory & Readiness Assessment Engine (PENDING USER INITIATION)
- [ ] **Phase 7:** Assisted Service, Subscription & Payment Integration (PENDING USER INITIATION)
- [ ] **Phase 8:** Final Hardening, Integration & Academic Defense Preparation (PENDING USER INITIATION)
