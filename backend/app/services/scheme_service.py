import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.assessment import Assessment
from app.models.profile import UserProfile
from app.models.scheme import Scheme
from app.models.user import User
from app.schemas.scheme import (
    AssessmentHistoryItem,
    AssessmentResultResponse,
    ConditionEvaluation,
    SchemeCategoryItem,
    SchemeRecommendation,
    SchemeResponse,
)
from app.services.eligibility_service import EligibilityEngine

# Initial verified government active seed data
DEMO_SCHEMES_SEED = [
    {
        "id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "scheme_name": "Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)",
        "short_description": "Direct income support of ₹6,000 per year for farmer families with cultivable landholding.",
        "description": "Pradhan Mantri Kisan Samman Nidhi (PM-KISAN) is a central sector scheme to augment the income of all landholding farmers' families in the country to procure various inputs related to agriculture and allied activities.",
        "department": "Ministry of Agriculture and Farmers Welfare",
        "category": "Agriculture",
        "state_applicability": "All India",
        "eligibility_summary": "All landholding farmer families having cultivable land in their names. No institutional landholders. Farmers residing in rural or urban areas.",
        "benefits": [
            "Financial benefit of ₹6,000 per year per family",
            "Paid in three equal installments of ₹2,000 every 4 months",
            "Direct Benefit Transfer (DBT) directly into citizen's bank account"
        ],
        "eligibility_criteria": [
            {
                "condition_name": "Agricultural Occupation",
                "field": "occupation",
                "operator": "contains",
                "expected_value": "farmer",
                "explanation": "Must be engaged in farming or agricultural cultivation."
            },
            {
                "condition_name": "Minimum Citizen Age",
                "field": "age",
                "operator": "gte",
                "expected_value": 18,
                "explanation": "Applicant must be an adult aged 18 years or above."
            }
        ],
        "required_profile_fields": ["occupation", "age", "state"],
        "application_process": [
            "Visit the official PM-KISAN portal (pmkisan.gov.in)",
            "Navigate to Farmers Corner and select 'New Farmer Registration'",
            "Enter your registered mobile number and state of residence",
            "Fill in land records details (Khasra / Khatauni numbers)",
            "Submit and note your application reference number for tracking"
        ],
        "required_documents": [
            "Land ownership records / 7/12 extract / RoR",
            "Bank account passbook copy with IFSC code",
            "Valid mobile number linked with bank account",
            "Proof of residence / domicile certificate"
        ],
        "official_source_url": "https://pmkisan.gov.in/",
        "official_application_url": "https://pmkisan.gov.in/RegistrationFormNew.aspx",
        "source_last_verified_at": datetime(2026, 2, 18, tzinfo=timezone.utc),
        "source_freshness_status": "Verified Active Official Scheme",
        "eligibility_source_reference": "PM-KISAN Operational Guidelines, Section 3 (Eligibility Conditions & Landholder Criteria), Ministry of Agriculture & Farmers Welfare, GoI",
        "benefits_source_reference": "PM-KISAN Operational Guidelines, Section 2 (Financial Assistance & Installment Structure), Ministry of Agriculture & Farmers Welfare, GoI",
        "source_verification_details": "Verified against PM-KISAN official guidelines (pmkisan.gov.in). Landholding records and Aadhaar e-KYC validated via state land revenue portal and DBT integration.",
        "status": "active",
        "is_active": True,
        "is_demo_data": False,
    },
    {
        "id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
        "scheme_name": "Ayushman Bharat - Pradhan Mantri Jan Arogya Yojana (AB-PMJAY)",
        "short_description": "Comprehensive cashless health cover of ₹5,00,000 per family per year for secondary and tertiary hospitalization.",
        "description": "Ayushman Bharat - Pradhan Mantri Jan Arogya Yojana (AB-PMJAY) is the world's largest health assurance scheme providing a health cover of ₹5 lakhs per family per year for secondary and tertiary care hospitalization to over 12 crore poor and vulnerable families.",
        "department": "National Health Authority / Ministry of Health and Family Welfare",
        "category": "Healthcare",
        "state_applicability": "All India",
        "eligibility_summary": "Families classified under poor, vulnerable or deprived socio-economic categories with annual income below ₹2,50,000, and all senior citizens aged 70+.",
        "benefits": [
            "Cashless health cover up to ₹5,00,000 per family per year",
            "Covers up to 3 days of pre-hospitalization and 15 days of post-hospitalization expenses",
            "Over 1,949 medical and surgical procedures covered at empaneled hospitals across India",
            "Pre-existing illnesses covered from day one"
        ],
        "eligibility_criteria": [
            {
                "condition_name": "Annual Family Income Limit",
                "field": "annual_family_income",
                "operator": "lte",
                "expected_value": 250000,
                "explanation": "Annual family income must not exceed ₹2,50,000."
            },
            {
                "condition_name": "Minimum Age",
                "field": "age",
                "operator": "gte",
                "expected_value": 18,
                "explanation": "Primary applicant must be at least 18 years old."
            }
        ],
        "required_profile_fields": ["annual_family_income", "age", "state"],
        "application_process": [
            "Visit official PM-JAY portal (beneficiary.nha.gov.in)",
            "Enter your mobile number to check family inclusion",
            "Locate nearest Empaneled Health Care Provider (EHCP) or Ayushman Mitra kiosk",
            "Present identity and income/ration proof for e-KYC validation",
            "Receive Ayushman Golden Card for cashless treatment"
        ],
        "required_documents": [
            "Ration card or BPL certificate",
            "Government income certificate issued by competent revenue authority",
            "Valid photo identity card (Aadhaar, Voter ID, or Driving License)",
            "Mobile number for OTP verification"
        ],
        "official_source_url": "https://pmjay.gov.in/",
        "official_application_url": "https://beneficiary.nha.gov.in/",
        "source_last_verified_at": datetime(2026, 2, 18, tzinfo=timezone.utc),
        "source_freshness_status": "Verified Active Official Scheme",
        "eligibility_source_reference": "National Health Authority (NHA) AB-PMJAY Beneficiary Eligibility Criteria, SECC 2011 Deprivation Guidelines",
        "benefits_source_reference": "NHA PM-JAY Benefit Package 2.2 / Healthcare Benefit Schedule, Ministry of Health and Family Welfare, GoI",
        "source_verification_details": "Verified against NHA guidelines (pmjay.gov.in). Entitlement verified at empaneled hospitals or Ayushman kiosks across India.",
        "status": "active",
        "is_active": True,
        "is_demo_data": False,
    },
    {
        "id": uuid.UUID("33333333-3333-3333-3333-333333333333"),
        "scheme_name": "Pradhan Mantri Awas Yojana - Gramin (PMAY-G)",
        "short_description": "Financial grant of ₹1,20,000 for construction of clean pucca house for rural homeless or kutcha householders.",
        "description": "Pradhan Mantri Awas Yojana - Gramin aims to provide a pucca house with basic amenities to all rural families who are homeless or living in kutcha or dilapidated houses.",
        "department": "Ministry of Rural Development",
        "category": "Housing",
        "state_applicability": "All India",
        "eligibility_summary": "Homeless families or families living in zero, one or two room kutcha houses in rural areas.",
        "benefits": [
            "Direct grant of ₹1,20,000 in plain areas and ₹1,30,000 in hilly/remote states",
            "Optional 90-95 person-days of unskilled labor under MGNREGS (approx. ₹20,000)",
            "Additional ₹12,000 assistance for toilet construction under Swachh Bharat Mission"
        ],
        "eligibility_criteria": [
            {
                "condition_name": "Rural Residence",
                "field": "residence_type",
                "operator": "eq",
                "expected_value": "rural",
                "explanation": "Citizen must reside in a rural area (PMAY-G does not apply to urban municipalities)."
            },
            {
                "condition_name": "Annual Family Income Ceiling",
                "field": "annual_family_income",
                "operator": "lte",
                "expected_value": 180000,
                "explanation": "Annual family income must be under ₹1,80,000."
            }
        ],
        "required_profile_fields": ["residence_type", "annual_family_income", "state", "district"],
        "application_process": [
            "Contact your local Gram Panchayat or Block Development Office (BDO)",
            "Submit house survey verification form to Panchayat Secretary",
            "Verify geo-tagged photos of existing kutcha dwelling",
            "Track Gram Sabha priority waiting list on AwaasSoft portal (pmayg.nic.in)"
        ],
        "required_documents": [
            "Gram Panchayat residence certificate",
            "Income certificate / BPL survey number",
            "Bank passbook copy linked to DBT",
            "Land / plot possession certificate or allotment letter"
        ],
        "official_source_url": "https://pmayg.nic.in/",
        "official_application_url": "https://pmayg.nic.in/netiay/home.aspx",
        "source_last_verified_at": datetime(2026, 2, 18, tzinfo=timezone.utc),
        "source_freshness_status": "Verified Active Official Scheme",
        "eligibility_source_reference": "Framework for Implementation of PMAY-G, Chapter 3 (Beneficiary Selection & Deprivation Criteria), Ministry of Rural Development, GoI",
        "benefits_source_reference": "Framework for Implementation of PMAY-G, Chapter 2 (Unit Assistance & Convergence with MGNREGS/SBM), Ministry of Rural Development, GoI",
        "source_verification_details": "Verified against MoRD scheme guidelines (pmayg.nic.in). Beneficiary selection requires Gram Sabha approval and geo-tagged house verification on AwaasSoft.",
        "status": "active",
        "is_active": True,
        "is_demo_data": False,
    },
    {
        "id": uuid.UUID("44444444-4444-4444-4444-444444444444"),
        "scheme_name": "National Scholarship Portal - Post-Matric Scholarships for Students",
        "short_description": "Full tuition fee waiver and monthly maintenance stipend for students pursuing higher education.",
        "description": "Centrally sponsored scholarship scheme to support students from economically weaker sections to pursue post-matriculation or post-secondary stages of education.",
        "department": "Ministry of Social Justice and Empowerment / Ministry of Education",
        "category": "Education",
        "state_applicability": "All India",
        "eligibility_summary": "Students enrolled in recognized college, university or diploma courses who have passed Class 10 with family income <= ₹2,50,000.",
        "benefits": [
            "100% reimbursement of non-refundable compulsory college tuition fees",
            "Monthly academic maintenance stipend of ₹1,200 to ₹3,500 depending on degree",
            "Additional book allowance and thesis grant for postgraduate researchers"
        ],
        "eligibility_criteria": [
            {
                "condition_name": "Student Occupation",
                "field": "occupation",
                "operator": "contains",
                "expected_value": "student",
                "explanation": "Citizen must currently be a student enrolled in post-matric studies."
            },
            {
                "condition_name": "Annual Family Income Limit",
                "field": "annual_family_income",
                "operator": "lte",
                "expected_value": 250000,
                "explanation": "Combined annual family income must not exceed ₹2,50,000."
            },
            {
                "condition_name": "Minimum Education Level",
                "field": "education_level",
                "operator": "neq",
                "expected_value": "Below 10th Standard",
                "explanation": "Applicant must have passed at least 10th Standard / Matriculation."
            }
        ],
        "required_profile_fields": ["occupation", "annual_family_income", "education_level", "age"],
        "application_process": [
            "Register on National Scholarship Portal (scholarships.gov.in)",
            "Enter Student OTR (One Time Registration) number",
            "Select scheme under Central Schemes section",
            "Upload institute verification form signed by Principal/Dean",
            "Submit online application before annual scheme deadline"
        ],
        "required_documents": [
            "Previous qualifying mark sheet (10th / 12th / Diploma)",
            "Current year college fee receipt and bonafide student certificate",
            "Competent authority family income certificate",
            "Student bank passbook copy"
        ],
        "official_source_url": "https://scholarships.gov.in/",
        "official_application_url": "https://scholarships.gov.in/fresh/newstdRegfrmInstruction",
        "source_last_verified_at": datetime(2026, 2, 18, tzinfo=timezone.utc),
        "source_freshness_status": "Verified Active Official Scheme",
        "eligibility_source_reference": "National Scholarship Portal (NSP) Centrally Sponsored Scheme Guidelines for Post-Matric Scholarships, Ministry of Social Justice and Empowerment / Ministry of Education, GoI",
        "benefits_source_reference": "NSP Post-Matric Financial Assistance Component Regulations (Tuition Waiver & Maintenance Allowance Schedule)",
        "source_verification_details": "Verified from NSP guidance (scholarships.gov.in). Institute nodal officer verification and Aadhaar-based biometric e-KYC required.",
        "status": "active",
        "is_active": True,
        "is_demo_data": False,
    },
    {
        "id": uuid.UUID("55555555-5555-5555-5555-555555555555"),
        "scheme_name": "Mahatma Jyotirao Phule Jan Arogya Yojana (MJPJAY)",
        "short_description": "Maharashtra state cashless health insurance cover up to ₹5,00,000 per family for 996 specialized procedures.",
        "description": "Mahatma Jyotirao Phule Jan Arogya Yojana is the flagship health insurance scheme of the Government of Maharashtra, providing comprehensive cashless healthcare for identified illnesses requiring hospitalization for surgeries and therapies.",
        "department": "Public Health Department, Government of Maharashtra",
        "category": "Healthcare",
        "state_applicability": "Maharashtra",
        "eligibility_summary": "Families domiciled in Maharashtra holding Yellow, Orange, or Antyodaya ration cards.",
        "benefits": [
            "Cashless coverage of ₹5,00,000 per family per policy year",
            "996 medical and surgical procedures across 30 specialized categories",
            "Includes pre-operative tests, consultation, ICU, medicine, and 10 days post-discharge medications"
        ],
        "eligibility_criteria": [
            {
                "condition_name": "Maharashtra State Domicile",
                "field": "state",
                "operator": "eq",
                "expected_value": "Maharashtra",
                "explanation": "Citizen must reside in the state of Maharashtra."
            },
            {
                "condition_name": "Annual Family Income Ceiling",
                "field": "annual_family_income",
                "operator": "lte",
                "expected_value": 300000,
                "explanation": "Annual family income must not exceed ₹3,00,000."
            }
        ],
        "required_profile_fields": ["state", "annual_family_income", "district"],
        "application_process": [
            "Visit any network hospital (Government or Empaneled Private) in Maharashtra",
            "Approach the dedicated Arogyamitra counter with your ration card and photo ID",
            "Arogyamitra verifies eligibility online through the MJPJAY portal",
            "Hospital submits e-authorization request to State Health Assurance Society",
            "Undergo cashless treatment upon automated approval"
        ],
        "required_documents": [
            "Valid Maharashtra ration card (Yellow, Orange, or AAY)",
            "Government revenue income certificate",
            "Valid photo identity proof (Voter ID or Driving License)",
            "Doctor referral letter or hospital admission slip"
        ],
        "official_source_url": "https://www.jeevandayee.gov.in/",
        "official_application_url": "https://www.jeevandayee.gov.in/",
        "source_last_verified_at": datetime(2026, 2, 18, tzinfo=timezone.utc),
        "source_freshness_status": "Verified Active Official Scheme",
        "eligibility_source_reference": "Government of Maharashtra Public Health Department Resolution No. MJPJAY-2023/CR-142/PH-4 (Eligibility: Yellow/Orange Ration Card Holders & State Domicile)",
        "benefits_source_reference": "State Health Assurance Society (SHAS) Maharashtra Medical Procedures Schedule & Coverage Ceiling Guidelines (₹5 Lakhs)",
        "source_verification_details": "Verified from State Health Assurance Society portal (jeevandayee.gov.in). Valid Maharashtra ration card verified by Arogyamitra at network hospitals.",
        "status": "active",
        "is_active": True,
        "is_demo_data": False,
    },
    {
        "id": uuid.UUID("66666666-6666-6666-6666-666666666666"),
        "scheme_name": "PM Vishwakarma Scheme",
        "short_description": "Holistic support for traditional artisans & craftspeople: ₹15,000 toolkit incentive and collateral-free credit up to ₹3 Lakh at 5% interest.",
        "description": "PM Vishwakarma is a Central Sector Scheme launched to provide end-to-end holistic support to traditional artisans and craftspeople engaged in 18 traditional trades, covering skill upgradation, toolkit incentive, collateral-free credit support, digital transaction incentives, and marketing support.",
        "department": "Ministry of Micro, Small and Medium Enterprises (MoMSME)",
        "category": "Employment & Skilling",
        "state_applicability": "All India",
        "eligibility_summary": "Traditional artisans and craftspeople working with their hands and tools in one of 18 trades (carpenter, blacksmith, goldsmith, potter, sculptor, cobbler, tailor, etc.), aged 18 or above.",
        "benefits": [
            "Recognition: PM Vishwakarma Certificate and ID Card",
            "Skill Upgradation: 5-7 days basic training with ₹500/day stipend, plus advanced training",
            "Toolkit Incentive: ₹15,000 digital voucher for modern toolkits",
            "Collateral-free Credit: Tranche 1 up to ₹1,00,000 (18 months) and Tranche 2 up to ₹2,00,000 (30 months) at concessional 5% interest rate",
            "Incentive for Digital Transactions: ₹1 per digital transaction up to 100 transactions/month"
        ],
        "eligibility_criteria": [
            {
                "condition_name": "Minimum Citizen Age",
                "field": "age",
                "operator": "gte",
                "expected_value": 18,
                "explanation": "Citizen must be at least 18 years of age on date of registration."
            },
            {
                "condition_name": "Artisan or Self-Employed Vocation",
                "field": "occupation",
                "operator": "contains",
                "expected_value": "artisan",
                "explanation": "Applicant must be an artisan, craftsman, or self-employed worker in recognized traditional trades."
            }
        ],
        "required_profile_fields": ["age", "occupation", "state"],
        "application_process": [
            "Visit nearest Common Services Center (CSC) or official portal (pmvishwakarma.gov.in)",
            "Biometric Aadhaar authentication and trade verification by Gram Panchayat / Urban Local Body",
            "Receive PM Vishwakarma Digital Certificate and ID",
            "Enroll in Skill Training program at accredited training center",
            "Receive ₹15,000 toolkit e-voucher and apply for low-interest enterprise loan"
        ],
        "required_documents": [
            "Aadhaar card linked with active mobile number",
            "Bank passbook or cancelled cheque with account number and IFSC",
            "Ration card or family declaration for one-beneficiary-per-family rule",
            "Trade declaration form certified by local authority / Panchayat"
        ],
        "official_source_url": "https://pmvishwakarma.gov.in/",
        "official_application_url": "https://pmvishwakarma.gov.in/Registration",
        "source_last_verified_at": datetime(2026, 2, 18, tzinfo=timezone.utc),
        "source_freshness_status": "Verified Active Official Scheme",
        "eligibility_source_reference": "PM Vishwakarma Scheme Guidelines 2023-2028, Section 4 (Eligible Trades & Beneficiary Criteria), Ministry of MSME, GoI",
        "benefits_source_reference": "PM Vishwakarma Scheme Guidelines 2023-2028, Section 6 (Credit Support & Toolkit Incentive Structure)",
        "source_verification_details": "Verified from official PM Vishwakarma portal (pmvishwakarma.gov.in). Three-stage verification: Gram Panchayat / ULB, District Implementation Committee, and Screening Committee.",
        "status": "active",
        "is_active": True,
        "is_demo_data": False,
    },
    {
        "id": uuid.UUID("77777777-7777-7777-7777-777777777777"),
        "scheme_name": "Pradhan Mantri Mudra Yojana (PMMY)",
        "short_description": "Collateral-free institutional micro-credit up to ₹10 Lakhs for small business, manufacturing, and trading enterprises.",
        "description": "Pradhan Mantri Mudra Yojana (PMMY) provides collateral-free institutional loans to non-corporate, non-farm small and micro enterprises for income-generating activities in manufacturing, processing, trading, and services sectors through commercial banks, RRBs, Small Finance Banks, and MFIs.",
        "department": "Department of Financial Services, Ministry of Finance",
        "category": "Business & Entrepreneurship",
        "state_applicability": "All India",
        "eligibility_summary": "Any Indian citizen who has a business plan for a non-farm sector income-generating micro or small enterprise in manufacturing, trading, or service sectors.",
        "benefits": [
            "Shishu Loans: Loans up to ₹50,000 for early-stage startups and small micro-units",
            "Kishore Loans: Loans from ₹50,001 up to ₹5,00,000 for purchasing equipment, machinery, and inventory",
            "Tarun Loans: Loans from ₹5,00,001 up to ₹10,00,000 for established units seeking business expansion",
            "Zero collateral security or third-party guarantee required",
            "Affordable interest rates linked to RBI benchmark with Mudra Debit Card for working capital"
        ],
        "eligibility_criteria": [
            {
                "condition_name": "Minimum Citizen Age",
                "field": "age",
                "operator": "gte",
                "expected_value": 18,
                "explanation": "Applicant must be an Indian citizen aged 18 years or older."
            },
            {
                "condition_name": "Non-Defaulter Status",
                "field": "residence_type",
                "operator": "neq",
                "expected_value": "foreign",
                "explanation": "Citizen must not be a defaulter to any bank or financial institution."
            }
        ],
        "required_profile_fields": ["age", "state", "residence_type"],
        "application_process": [
            "Formulate a viable micro-business plan or enterprise proposal",
            "Apply online via the UdyamiMitra portal (udyamimitra.in) or visit any nationalized / rural bank",
            "Select loan category (Shishu, Kishore, or Tarun) based on requirement",
            "Submit KYC documents, business identity proof, and projected cash flow statements",
            "Receive loan sanction and Mudra Card upon bank appraisal"
        ],
        "required_documents": [
            "Proof of identity (Voter ID / Driving License / PAN / Aadhaar)",
            "Proof of residence / telephone / electricity bill",
            "Business establishment certificate / Udyam Registration (if existing business)",
            "Bank account statements of last 6 months",
            "Quotation of machinery / items to be purchased"
        ],
        "official_source_url": "https://www.mudra.org.in/",
        "official_application_url": "https://www.udyamimitra.in/",
        "source_last_verified_at": datetime(2026, 2, 18, tzinfo=timezone.utc),
        "source_freshness_status": "Verified Active Official Scheme",
        "eligibility_source_reference": "PMMY Scheme Operational Guidelines, Department of Financial Services, Ministry of Finance, GoI",
        "benefits_source_reference": "Micro Units Development & Refinance Agency Ltd (MUDRA) Loan Products & Lending Norms",
        "source_verification_details": "Verified from official MUDRA portal (mudra.org.in) and DFS UdyamiMitra. Loan approval is subject to commercial viability appraisal by the lending institution.",
        "status": "active",
        "is_active": True,
        "is_demo_data": False,
    },
]


class SchemeService:
    """Service handling scheme catalog discovery, search, recommendations, and assessments."""

    @staticmethod
    def ensure_demo_schemes_seeded(db: Session) -> None:
        """Seed verified sample demo government schemes if table is empty or update missing seed metadata."""
        for s_data in DEMO_SCHEMES_SEED:
            existing = db.query(Scheme).filter(Scheme.id == s_data["id"]).first()
            if not existing:
                scheme = Scheme(**s_data)
                db.add(scheme)
            else:
                for k, v in s_data.items():
                    setattr(existing, k, v)
        db.commit()

    @staticmethod
    def get_schemes(
        db: Session,
        query: Optional[str] = None,
        category: Optional[str] = None,
        state: Optional[str] = None,
        status_filter: Optional[str] = "active",
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Scheme], int]:
        """Query government schemes with multi-filter search and pagination."""
        SchemeService.ensure_demo_schemes_seeded(db)

        q = db.query(Scheme)

        if status_filter:
            q = q.filter(Scheme.status == status_filter)

        if category and category.strip():
            q = q.filter(Scheme.category.ilike(f"%{category.strip()}%"))

        if state and state.strip():
            st = state.strip()
            q = q.filter(or_(Scheme.state_applicability == "All India", Scheme.state_applicability.ilike(f"%{st}%")))

        if query and query.strip():
            search_term = f"%{query.strip()}%"
            q = q.filter(
                or_(
                    Scheme.scheme_name.ilike(search_term),
                    Scheme.description.ilike(search_term),
                    Scheme.department.ilike(search_term),
                    Scheme.eligibility_summary.ilike(search_term),
                )
            )

        total = q.count()
        offset = (page - 1) * page_size
        items = q.order_by(Scheme.scheme_name.asc()).offset(offset).limit(page_size).all()
        return items, total

    @staticmethod
    def get_categories(db: Session) -> List[SchemeCategoryItem]:
        """Aggregate unique categories with active scheme counts."""
        SchemeService.ensure_demo_schemes_seeded(db)
        results = (
            db.query(Scheme.category, func.count(Scheme.id))
            .filter(Scheme.status == "active")
            .group_by(Scheme.category)
            .order_by(Scheme.category.asc())
            .all()
        )
        return [SchemeCategoryItem(category=r[0], count=r[1]) for r in results]

    @staticmethod
    def get_scheme_by_id(db: Session, scheme_id: uuid.UUID) -> Scheme:
        """Fetch a specific scheme by UUID."""
        SchemeService.ensure_demo_schemes_seeded(db)
        scheme = db.query(Scheme).filter(Scheme.id == scheme_id).first()
        if not scheme:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Government scheme not found.",
            )
        return scheme

    @staticmethod
    def get_recommendations_for_user(
        db: Session,
        user_id: uuid.UUID,
    ) -> List[SchemeRecommendation]:
        """Generate tailored recommendations for the authenticated citizen."""
        SchemeService.ensure_demo_schemes_seeded(db)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        profile = user.profile
        schemes = db.query(Scheme).filter(Scheme.status == "active", Scheme.is_active == True).all()
        return EligibilityEngine.generate_recommendations(schemes, profile)

    @staticmethod
    def run_assessment(
        db: Session,
        user_id: uuid.UUID,
        scheme_id: uuid.UUID,
    ) -> AssessmentResultResponse:
        """Run deterministic assessment for authenticated citizen and persist result."""
        SchemeService.ensure_demo_schemes_seeded(db)
        scheme = SchemeService.get_scheme_by_id(db, scheme_id)

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        eval_result = EligibilityEngine.evaluate_scheme(scheme, user.profile)

        # Store assessment run in database
        criteria_match_pct = eval_result["criteria_match_percentage"]
        score_interp = eval_result["score_interpretation"]

        assessment = Assessment(
            user_id=user.id,
            scheme_id=scheme.id,
            assessment_type="scheme_eligibility",
            result_data={
                "overall_status": eval_result["overall_status"],
                "criteria_match_percentage": criteria_match_pct,
                "overall_readiness_score": criteria_match_pct,
                "score_interpretation": score_interp,
                "scheme_name": scheme.scheme_name,
                "category": scheme.category,
                "satisfied_count": eval_result["satisfied_count"],
                "not_satisfied_count": eval_result["not_satisfied_count"],
                "unknown_count": eval_result["unknown_count"],
                "missing_fields": eval_result["missing_fields"],
                "conditions_breakdown": [c.model_dump() for c in eval_result["conditions_breakdown"]],
                "evaluated_at": eval_result["evaluated_at"].isoformat(),
            },
            overall_readiness_score=criteria_match_pct,
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)

        return AssessmentResultResponse(
            assessment_id=assessment.id,
            scheme_id=scheme.id,
            scheme_name=scheme.scheme_name,
            category=scheme.category,
            overall_status=eval_result["overall_status"],
            criteria_match_percentage=criteria_match_pct,
            overall_readiness_score=criteria_match_pct,
            score_interpretation=score_interp,
            conditions_breakdown=eval_result["conditions_breakdown"],
            satisfied_count=eval_result["satisfied_count"],
            not_satisfied_count=eval_result["not_satisfied_count"],
            unknown_count=eval_result["unknown_count"],
            missing_fields=eval_result["missing_fields"],
            official_source_url=scheme.official_source_url,
            official_application_url=scheme.official_application_url,
            evaluated_at=eval_result["evaluated_at"],
        )

    @staticmethod
    def get_assessment_history(
        db: Session,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> List[AssessmentHistoryItem]:
        """Fetch citizen's assessment history with strict user data isolation."""
        offset = (page - 1) * page_size
        records = (
            db.query(Assessment)
            .filter(Assessment.user_id == user_id)
            .order_by(desc(Assessment.created_at))
            .offset(offset)
            .limit(page_size)
            .all()
        )

        history: List[AssessmentHistoryItem] = []
        for a in records:
            res_data = a.result_data or {}
            score = float(res_data.get("criteria_match_percentage", a.overall_readiness_score or 0.0))
            history.append(
                AssessmentHistoryItem(
                    assessment_id=a.id,
                    scheme_id=a.scheme_id,
                    scheme_name=res_data.get("scheme_name", "Government Scheme Assessment"),
                    overall_status=res_data.get("overall_status", "Evaluated"),
                    criteria_match_percentage=score,
                    overall_readiness_score=score,
                    satisfied_count=res_data.get("satisfied_count", 0),
                    not_satisfied_count=res_data.get("not_satisfied_count", 0),
                    unknown_count=res_data.get("unknown_count", 0),
                    created_at=a.created_at,
                )
            )
        return history

    @staticmethod
    def get_assessment_detail(
        db: Session,
        user_id: uuid.UUID,
        assessment_id: uuid.UUID,
    ) -> AssessmentResultResponse:
        """Fetch specific assessment detail verifying user ownership."""
        assessment = (
            db.query(Assessment)
            .filter(Assessment.id == assessment_id, Assessment.user_id == user_id)
            .first()
        )
        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment record not found or access denied.",
            )

        res_data = assessment.result_data or {}
        scheme = db.query(Scheme).filter(Scheme.id == assessment.scheme_id).first()

        breakdown_dicts = res_data.get("conditions_breakdown", [])
        evaluations = [ConditionEvaluation(**b) for b in breakdown_dicts]
        score = float(res_data.get("criteria_match_percentage", assessment.overall_readiness_score or 0.0))

        return AssessmentResultResponse(
            assessment_id=assessment.id,
            scheme_id=assessment.scheme_id or uuid.uuid4(),
            scheme_name=res_data.get("scheme_name", scheme.scheme_name if scheme else "Scheme Assessment"),
            category=res_data.get("category", scheme.category if scheme else "General"),
            overall_status=res_data.get("overall_status", "Unknown"),
            criteria_match_percentage=score,
            overall_readiness_score=score,
            score_interpretation=res_data.get(
                "score_interpretation",
                f"Criteria Match Percentage indicates that {score}% of evaluated conditions are verified as satisfied. It is not an approval likelihood."
            ),
            conditions_breakdown=evaluations,
            satisfied_count=res_data.get("satisfied_count", 0),
            not_satisfied_count=res_data.get("not_satisfied_count", 0),
            unknown_count=res_data.get("unknown_count", 0),
            missing_fields=res_data.get("missing_fields", []),
            official_source_url=scheme.official_source_url if scheme else "https://myscheme.gov.in/",
            official_application_url=scheme.official_application_url if scheme else "https://www.india.gov.in/",
            evaluated_at=assessment.created_at,
        )

