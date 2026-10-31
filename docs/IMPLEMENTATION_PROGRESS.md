# JanMitra Assist – Implementation Progress Tracker

**Project Name:** JanMitra Assist – AI-Powered Government Service Eligibility and Document Intelligence System  
**Academic Target:** MCA Major Project  
**Current Phase:** Phase 4 (Government Scheme Discovery & Eligibility Engine) – COMPLETED

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

## 2. Phase 4 Implementation & Completion Status

### Task A: Scheme Model Extension & Database Migration
- Extended `Scheme` model in `backend/app/models/scheme.py` with structured JSONB fields:
  - `short_description`: Concise summary for mobile cards (VARCHAR 500).
  - `category`: Sector category (Agriculture, Healthcare, Housing, Education, Social Welfare).
  - `benefits`: Structured JSON list of financial and non-financial entitlements.
  - `eligibility_criteria`: Structured rule conditions with target field, operator, expected value, and citizen explanation.
  - `required_profile_fields`: Explicit list of citizen demographic fields needed for automated evaluation.
  - `application_process`: Step-by-step guidance for completing formal portal applications.
  - `required_documents`: Comprehensive list of documents required for the scheme.
  - `status`: Lifecycle status (`active`, `inactive`, `discontinued`).
  - `is_demo_data`: Boolean flag clearly distinguishing curated MCA test records from live portal data.
- Authored Alembic migration `7a8e5f3c9102_extend_scheme_model_for_phase_4.py`.
- Verified static SQL compilation for PostgreSQL via `alembic upgrade head --sql`.

### Task B: Deterministic Eligibility Engine
- Implemented `EligibilityEngine` in `backend/app/services/eligibility_service.py`:
  - **Operators Supported:** `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `in`, `contains`.
  - **Dynamic Fact Extraction:** Safely extracts citizen facts from `UserProfile` including dynamic age calculation from `date_of_birth`.
  - **Missing Profile Data Rule:** If a required fact is absent or null, condition status is classified as `unknown` (never auto-failed), and the scheme overall status is set to `Insufficient Information` with actionable `missing_fields` alerts.
  - **Explainable Outcomes:** Produces condition-by-condition evaluation (`satisfied`, `not_satisfied`, `unknown`) with actual vs expected values and plain-language citizen explanations.
  - **Strict Advisory Nature:** Result status values are strictly non-authoritative: `Potentially Eligible`, `Not Eligible Based on Available Information`, or `Insufficient Information`.
  - **Advisory Readiness Score:** Calculates an advisory readiness index (0.0% to 100.0%) indicating application preparedness.

### Task C: Curated Verified Government Seed Schemes
- Seeded 5 verified official demo schemes with authentic nodal links in `backend/app/services/scheme_service.py`:
  1. **PM-KISAN (Central):** ₹6,000/year income support for farmer families (`https://pmkisan.gov.in/`).
  2. **AB-PMJAY (Ayushman Bharat):** ₹5 Lakh annual secondary/tertiary health cover for vulnerable families (`https://pmjay.gov.in/`).
  3. **PMAY-G (Pradhan Mantri Awaas Yojana - Gramin):** Financial assistance for rural pucca house construction (`https://pmayg.nic.in/`).
  4. **NSP Post-Matric Scholarship:** Higher education tuition support for students with annual family income <= ₹2.5 Lakh (`https://scholarships.gov.in/`).
  5. **Maharashtra MJPJAY (State Welfare):** Up to ₹5 Lakh cashless critical illness hospitalization for Maharashtra ration card holders (`https://www.jeevandayee.gov.in/`).
- All seed records clearly flagged with `is_demo_data = True`.

### Task D: Backend REST API Endpoints
- Mounted scheme router under `/api/v1/schemes` in `backend/app/api/v1/api.py`:
  - `GET /api/v1/schemes`: Paginated catalog with multi-field search (`q`), sector category, and state filtering.
  - `GET /api/v1/schemes/categories`: Unique sector categories with active scheme counts.
  - `GET /api/v1/schemes/recommendations`: Profile-based scheme matching with match scores and explainability reasons.
  - `GET /api/v1/schemes/{scheme_id}`: Full scheme details including benefits, criteria, required documents, and verified portal URLs.
  - `POST /api/v1/schemes/{scheme_id}/assess`: Authenticated assessment execution that evaluates rules, computes readiness score, and persists record in `assessments` table.
  - `GET /api/v1/schemes/assessments/history`: Paginated history of citizen's past assessments.
  - `GET /api/v1/schemes/assessments/{assessment_id}`: Detailed retrieval of a past assessment run.
- **Strict Citizen Data Isolation:** Assessment history and detail queries enforce `assessment.user_id == current_user.id`; cross-citizen access returns `404 Not Found`.
- **Privacy Enforcement:** Aadhaar numbers are never requested, stored, or processed.

### Task E: Flutter Mobile Application Implementation
- Built mobile presentation layer under `mobile_app/lib/features/schemes/`:
  1. `scheme_discovery_screen.dart`:
     - Live keyword search bar across titles and descriptions.
     - State scope filter dropdown.
     - Horizontal sector category filter chips with counts.
     - Scheme cards with `[DEMO]` indicator, category pill, state pill, and navigation.
     - Top navigation for Recommendations and Assessment History.
  2. `scheme_details_screen.dart`:
     - Complete overview, department, and category metadata.
     - Key benefits bullet points.
     - Structured eligibility requirements breakdown.
     - Informational checklist of required documents.
     - Step-by-step official application process.
     - Verified official government portal link with copy button.
     - Prominent "Check My Eligibility" action with real-time feedback.
  3. `eligibility_result_screen.dart`:
     - Prominent statutory advisory disclaimer banner.
     - Advisory status badge (`Potentially Eligible`, `Insufficient Information`, `Not Eligible Based on Available Information`).
     - Readiness score gauge (0-100%).
     - Missing profile field alert box with direct "Update Profile Now" action.
     - Rule-by-rule condition evaluation cards with green ticks, red crosses, and amber warning icons.
     - Verified official application portal link and copy button.
  4. `recommended_schemes_screen.dart`:
     - Personalized recommendations list matching citizen profile attributes.
     - Displays match score percentage and specific match reasons (state match, occupation match, age match).
  5. `assessment_history_screen.dart`:
     - Chronological list of citizen's past assessments with status badge and score.
     - Tap to view full assessment analysis.
  6. `HomeScreen`:
     - Integrated interactive "Explore Welfare Schemes" card with quick actions for "Browse All Schemes", "My Matches", and "Assessments".
     - Upcoming modules (Phases 5-8) preserved and clearly marked as future.

### Task F: Testing & Quality Verification
- **Backend Pytest Suite:**
  - `backend/tests/test_schemes.py`: 12 tests covering all operators, missing profile handling, discovery pagination, keyword search, category filtering, user recommendations, assessment execution, and strict cross-citizen isolation (100% passed).
  - Complete backend test suite: **46 passed, 1 skipped (live PostgreSQL network test), 0 failed**.
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
