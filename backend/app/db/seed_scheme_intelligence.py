import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.models.scheme import Scheme
from app.models.scheme_intelligence import (
    SchemeCategoryRule,
    SchemeCategoryDocument,
    DocumentGuide,
    SchemeAnalyticsDataset,
    SchemeAnalyticsBreakdown,
    SchemeAnalyticsAuditLog,
)

# Known Scheme UUIDs
PM_KISAN_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
PM_JAY_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
PMAY_G_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
POST_MATRIC_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
MJPJAY_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")


# ============================================================================
# 1. VERIFIED CATEGORY RULES
# ============================================================================
CATEGORY_RULES_SEED: List[Dict[str, Any]] = [
    # PM-KISAN (Central Sector Scheme)
    {
        "scheme_id": PM_KISAN_ID,
        "category": "All",
        "condition_name": "Cultivable Landholding Ownership",
        "field": "landholding",
        "operator": "gte",
        "expected_value": 0.01,
        "special_conditions": "All landholding farmer families holding cultivable land in their names qualify equally across all social categories (General, OBC, SC, ST). Forest Rights Act (FRA) patta holders qualify.",
        "exceptions": "Institutional landholders, constitutional post holders, income tax payees of last assessment year, retired pension recipients of >= ₹10,000/mo.",
        "official_source_reference": "PM-KISAN Operational Guidelines 2023, Clause 3 (Eligibility & Exclusions), MoA&FW, GoI",
    },
    {
        "scheme_id": PM_KISAN_ID,
        "category": "SC",
        "condition_name": "Priority Saturation Drive",
        "field": "age",
        "operator": "gte",
        "expected_value": 18,
        "special_conditions": "100% saturation priority under Special SC/ST saturation drive. Fast-track physical verification by District Agriculture Officer.",
        "exceptions": "Standard statutory exclusions apply.",
        "official_source_reference": "PM-KISAN Special Saturation Campaign Guidelines 2024",
    },
    {
        "scheme_id": PM_KISAN_ID,
        "category": "ST",
        "condition_name": "Tribal Land Rights & FRA Verification",
        "field": "age",
        "operator": "gte",
        "expected_value": 18,
        "special_conditions": "FRA (Forest Rights Act) patta certificates explicitly accepted in lieu of standard revenue records in ITDA / Schedule V tribal blocks.",
        "exceptions": "Standard statutory exclusions apply.",
        "official_source_reference": "PM-KISAN Tribal Affairs Coordination Circular 2023",
    },

    # Ayushman Bharat PM-JAY
    {
        "scheme_id": PM_JAY_ID,
        "category": "General",
        "condition_name": "SECC Deprivation / Income Limit",
        "field": "annual_family_income",
        "operator": "lte",
        "expected_value": 250000,
        "special_conditions": "Eligibility determined by SECC 2011 deprivation criteria (D1-D7) or verified NFSA / State BPL ration card.",
        "exceptions": "Households possessing 3 or 4 wheeler, mechanized fishing boat, or paying income tax.",
        "official_source_reference": "NHA AB-PMJAY Beneficiary Identification Guidelines v3.2",
    },
    {
        "scheme_id": PM_JAY_ID,
        "category": "EWS",
        "condition_name": "EWS Ceiling Verification",
        "field": "annual_family_income",
        "operator": "lte",
        "expected_value": 250000,
        "special_conditions": "EWS certificate holders with income <= ₹2.5 Lakhs qualify for Ayushman Bharat state-extended pools in participating states.",
        "exceptions": "Standard exclusion filters.",
        "official_source_reference": "NHA State Health Agency (SHA) MoUs 2023-24",
    },
    {
        "scheme_id": PM_JAY_ID,
        "category": "OBC",
        "condition_name": "OBC SECC Deprivation Criteria",
        "field": "annual_family_income",
        "operator": "lte",
        "expected_value": 250000,
        "special_conditions": "Non-Creamy Layer OBC families registered on state Food Security portals (NFSA) qualify automatically.",
        "exceptions": "Creamy layer and government servants excluded.",
        "official_source_reference": "NHA Operational Handbook for Empaneled Hospitals",
    },
    {
        "scheme_id": PM_JAY_ID,
        "category": "SC",
        "condition_name": "Automatic Inclusion Criteria",
        "field": "annual_family_income",
        "operator": "lte",
        "expected_value": 300000,
        "special_conditions": "Automatic inclusion under SECC deprivation category D1 (Only one room with kuccha walls and roof) and D2 (No adult member between age 16 to 59).",
        "exceptions": "Government employees and income tax payers excluded.",
        "official_source_reference": "MoHFW Ayushman Bharat Guidelines, Annexure 1 (Target Beneficiaries)",
    },
    {
        "scheme_id": PM_JAY_ID,
        "category": "ST",
        "condition_name": "Particularly Vulnerable Tribal Groups (PVTG) Priority",
        "field": "annual_family_income",
        "operator": "lte",
        "expected_value": 300000,
        "special_conditions": "100% saturation for PVTG and tribal households residing in designated tribal scheduled areas.",
        "exceptions": "Standard exclusions apply.",
        "official_source_reference": "PM-JANMAN & AB-PMJAY Saturation Guidelines 2024",
    },

    # PMAY-G (Housing)
    {
        "scheme_id": PMAY_G_ID,
        "category": "SC",
        "condition_name": "60% Earmarking & Priority Score",
        "field": "annual_family_income",
        "operator": "lte",
        "expected_value": 150000,
        "special_conditions": "Statutory minimum 60% of all annual housing allocations earmarked for SC and ST beneficiaries within every Gram Panchayat.",
        "exceptions": "Pucca house owners, two-wheeler/four-wheeler owners, Kisan Credit Card >= ₹50,000 limit.",
        "official_source_reference": "PMAY-G Framework for Implementation, Section 4 (Beneficiary Selection), MoRD, GoI",
    },
    {
        "scheme_id": PMAY_G_ID,
        "category": "ST",
        "condition_name": "Tribal Priority Allocation",
        "field": "annual_family_income",
        "operator": "lte",
        "expected_value": 150000,
        "special_conditions": "Relaxed land patta requirements in tribal areas; assistance of ₹1,30,000 for hilly/difficult terrain vs ₹1,20,000 in plains.",
        "exceptions": "Standard 13 exclusion criteria under SECC 2011.",
        "official_source_reference": "MoRD Rural Housing Operational Guidelines, Para 4.2",
    },
    {
        "scheme_id": PMAY_G_ID,
        "category": "OBC",
        "condition_name": "SECC Deprivation Ranking",
        "field": "annual_family_income",
        "operator": "lte",
        "expected_value": 150000,
        "special_conditions": "Ranked in Gram Sabha Permanent Wait List (PWL) based on SECC deprivation score.",
        "exceptions": "Standard 13 exclusion parameters.",
        "official_source_reference": "PMAY-G Implementation Framework, Section 5",
    },
    {
        "scheme_id": PMAY_G_ID,
        "category": "General",
        "condition_name": "General Houseless / Kutcha House Criteria",
        "field": "annual_family_income",
        "operator": "lte",
        "expected_value": 150000,
        "special_conditions": "Must be genuinely houseless or living in zero/one/two room kutcha wall and kutcha roof dwelling as verified by Gram Sabha.",
        "exceptions": "Standard exclusions apply.",
        "official_source_reference": "PMAY-G Operational Manual 2023",
    },

    # Post-Matric Scholarship
    {
        "scheme_id": POST_MATRIC_ID,
        "category": "SC",
        "condition_name": "SC Post-Matric Income Ceiling & 100% Tuition Waiver",
        "field": "annual_family_income",
        "operator": "lte",
        "expected_value": 250000,
        "special_conditions": "Complete compulsory non-refundable fees reimbursed + monthly maintenance allowance up to ₹13,500/year for hostellers. No minimum qualifying percentage in previous exam.",
        "exceptions": "Students studying through correspondence/distance education without regular attendance receive only book allowance.",
        "official_source_reference": "Centrally Sponsored Scheme of Post-Matric Scholarships to SC Students, MSJE, GoI (2021-2026 Guidelines)",
    },
    {
        "scheme_id": POST_MATRIC_ID,
        "category": "ST",
        "condition_name": "ST Post-Matric Income Ceiling & Full Coverage",
        "field": "annual_family_income",
        "operator": "lte",
        "expected_value": 250000,
        "special_conditions": "Full fee waiver and living allowance. Administered by Ministry of Tribal Affairs with DBT direct to student's bank account.",
        "exceptions": "Second failure in degree course terminates scholarship.",
        "official_source_reference": "Scheme Guidelines for Post-Matric Scholarship for ST Students, Ministry of Tribal Affairs",
    },
    {
        "scheme_id": POST_MATRIC_ID,
        "category": "OBC",
        "condition_name": "OBC Non-Creamy Layer Ceiling",
        "field": "annual_family_income",
        "operator": "lte",
        "expected_value": 250000,
        "special_conditions": "Valid Non-Creamy Layer certificate required. Maintenance allowance and fee reimbursement subject to state government fee ceilings.",
        "exceptions": "Students whose parental income exceeds ₹2.50 Lakhs per annum.",
        "official_source_reference": "MSJE Guidelines for Post-Matric Scholarship for OBC Students",
    },
    {
        "scheme_id": POST_MATRIC_ID,
        "category": "EWS",
        "condition_name": "EWS Merit-cum-Means Ceiling",
        "field": "annual_family_income",
        "operator": "lte",
        "expected_value": 250000,
        "special_conditions": "Valid EWS certificate for current financial year required. Minimum 50% marks in previous qualifying board/university examination.",
        "exceptions": "Professional degree cap applies under state quotas.",
        "official_source_reference": "National Scholarship Portal Merit-cum-Means Guidelines",
    },

    # MJPJAY (Maharashtra)
    {
        "scheme_id": MJPJAY_ID,
        "category": "All",
        "condition_name": "Maharashtra Domicile & Ration Card Category",
        "field": "state",
        "operator": "eq",
        "expected_value": "Maharashtra",
        "geographic_scope": "State: Maharashtra",
        "verification_status": "Verified",
        "special_conditions": "Eligible families: Yellow Ration Card (BPL), Antyodaya Anna Yojana (AAY), Orange Ration Card (APL up to ₹1 Lakh income), White Card holders in 14 agrarian distress districts of Vidarbha and Marathwada.",
        "exceptions": "Government employees covered under Maharashtra State Government Employees Medical Scheme (MGGHIS).",
        "official_source_reference": "Government Resolution No. MJPJAY-2023/CR-142/PH-4, Public Health Dept, Govt of Maharashtra",
    },
    {
        "scheme_id": MJPJAY_ID,
        "category": "SC",
        "condition_name": "Fast-Track Arogyamitra Facilitation (Review Required)",
        "field": "state",
        "operator": "eq",
        "expected_value": "Maharashtra",
        "geographic_scope": "State: Maharashtra",
        "verification_status": "Review Required",
        "special_conditions": "Under review: Maharashtra GR No. MJPJAY-2023/CR-142/PH-4 establishes universal coverage based on eligible ration cards. Caste certificate provides expedited Arogyamitra counter facilitation and is not an independent statutory eligibility barrier.",
        "exceptions": "Non-domiciled citizens of Maharashtra not covered.",
        "official_source_reference": "SHAS Maharashtra Hospital Operational Guidelines (Under Statutory Review)",
    },
]


# ============================================================================
# 2. VERIFIED CATEGORY DOCUMENTS
# ============================================================================
CATEGORY_DOCUMENTS_SEED: List[Dict[str, Any]] = [
    # General Category Documents
    {
        "scheme_id": PM_KISAN_ID,
        "category": "General",
        "document_name": "Land Record (7/12 Extract / Khasra Khatauni)",
        "document_type": "land_record",
        "is_mandatory": True,
        "conditions_description": "Must establish ownership of cultivable agricultural land.",
        "issuing_authority": "Revenue Department / Talati / Patwari / e-Dharti",
        "accepted_formats": "PDF, JPG, PNG",
        "validity_rules": "Current financial year / up to date mutation entry",
    },
    {
        "scheme_id": PM_KISAN_ID,
        "category": "General",
        "document_name": "Bank Passbook Copy",
        "document_type": "bank_passbook",
        "is_mandatory": True,
        "conditions_description": "DBT-enabled bank account with IFSC code for Direct Benefit Transfer.",
        "issuing_authority": "Public Sector / Scheduled Commercial Bank",
        "accepted_formats": "PDF, JPG, PNG",
        "validity_rules": "Active operational account",
    },
    {
        "scheme_id": PM_JAY_ID,
        "category": "General",
        "document_name": "Ration Card (NFSA / BPL / State Card)",
        "document_type": "ration_card",
        "is_mandatory": True,
        "conditions_description": "Required to prove household composition and SECC deprivation status.",
        "issuing_authority": "Food and Civil Supplies Department",
        "accepted_formats": "PDF, JPG, PNG",
        "validity_rules": "Valid active digital ration card",
    },
    {
        "scheme_id": PM_JAY_ID,
        "category": "General",
        "document_name": "Revenue Income Certificate",
        "document_type": "income_certificate",
        "is_mandatory": True,
        "conditions_description": "Certifying family income <= ₹2,50,000 per annum.",
        "issuing_authority": "Tahsildar / Sub-Divisional Magistrate (SDM)",
        "accepted_formats": "PDF, JPG, PNG",
        "validity_rules": "Issued within last 12 months",
    },
    {
        "scheme_id": POST_MATRIC_ID,
        "category": "General",
        "document_name": "Domicile Certificate",
        "document_type": "domicile_certificate",
        "is_mandatory": True,
        "conditions_description": "Proves permanent residency in the awarding state/UT.",
        "issuing_authority": "Tahsildar / Mamlatdar / Executive Magistrate",
        "accepted_formats": "PDF, JPG, PNG",
        "validity_rules": "Permanent",
    },

    # OBC Category Documents
    {
        "scheme_id": POST_MATRIC_ID,
        "category": "OBC",
        "document_name": "OBC Caste Certificate",
        "document_type": "caste_certificate",
        "is_mandatory": True,
        "conditions_description": "Must cite Central or State Other Backward Classes notification number.",
        "issuing_authority": "SDM / Tahsildar / Mamlatdar",
        "accepted_formats": "PDF, JPG, PNG",
        "validity_rules": "Permanent caste identification",
    },
    {
        "scheme_id": POST_MATRIC_ID,
        "category": "OBC",
        "document_name": "Non-Creamy Layer (NCL) Certificate",
        "document_type": "non_creamy_layer",
        "is_mandatory": True,
        "conditions_description": "Mandatory to prove family income falls below the statutory Creamy Layer threshold (₹8 Lakhs/year).",
        "issuing_authority": "Tahsildar / Mamlatdar / Sub-Divisional Officer",
        "accepted_formats": "PDF, JPG, PNG",
        "validity_rules": "Valid for the current financial year (April to March)",
    },
    {
        "scheme_id": PM_JAY_ID,
        "category": "OBC",
        "document_name": "Non-Creamy Layer / Income Certificate",
        "document_type": "income_certificate",
        "is_mandatory": True,
        "conditions_description": "Proves family income <= ₹2,50,000 for hospital insurance entitlement.",
        "issuing_authority": "Revenue Authority / Tahsildar",
        "accepted_formats": "PDF, JPG, PNG",
        "validity_rules": "Valid for current financial year",
    },

    # SC Category Documents
    {
        "scheme_id": POST_MATRIC_ID,
        "category": "SC",
        "document_name": "Scheduled Caste (SC) Certificate",
        "document_type": "caste_certificate",
        "is_mandatory": True,
        "conditions_description": "Digital barcoded caste certificate certifying membership in a notified Scheduled Caste under Constitution Order 1950.",
        "issuing_authority": "Sub-Divisional Magistrate / District Welfare Officer",
        "accepted_formats": "PDF, JPG, PNG",
        "validity_rules": "Permanent",
    },
    {
        "scheme_id": POST_MATRIC_ID,
        "category": "SC",
        "document_name": "Competent Authority Income Certificate",
        "document_type": "income_certificate",
        "is_mandatory": True,
        "conditions_description": "Certifying parental annual income <= ₹2,50,000.",
        "issuing_authority": "Tahsildar / Mamlatdar",
        "accepted_formats": "PDF, JPG, PNG",
        "validity_rules": "Issued for current academic/financial year",
    },
    {
        "scheme_id": PMAY_G_ID,
        "category": "SC",
        "document_name": "SC Certificate for Priority Allocation",
        "document_type": "caste_certificate",
        "is_mandatory": True,
        "conditions_description": "Required to claim the 60% statutory SC/ST reservation quota in Gram Panchayat housing list.",
        "issuing_authority": "Competent Revenue Authority",
        "accepted_formats": "PDF, JPG, PNG",
        "validity_rules": "Permanent",
    },

    # ST Category Documents
    {
        "scheme_id": POST_MATRIC_ID,
        "category": "ST",
        "document_name": "Scheduled Tribe (ST) Certificate & Validity",
        "document_type": "caste_certificate",
        "is_mandatory": True,
        "conditions_description": "Certificate issued by competent authority along with Tribe Scrutiny Committee Validity in states where applicable (e.g. Maharashtra, Gujarat).",
        "issuing_authority": "SDM / Project Officer ITDP / Scrutiny Committee",
        "accepted_formats": "PDF, JPG, PNG",
        "validity_rules": "Permanent",
    },
    {
        "scheme_id": PM_KISAN_ID,
        "category": "ST",
        "document_name": "Forest Rights Act (FRA) Patta / Land Record",
        "document_type": "land_record",
        "is_mandatory": True,
        "conditions_description": "Title deed or Patta under Scheduled Tribes and Other Traditional Forest Dwellers (Recognition of Forest Rights) Act, 2006.",
        "issuing_authority": "District Level Committee / Collector / ITDP",
        "accepted_formats": "PDF, JPG, PNG",
        "validity_rules": "Permanent title deed",
    },

    # EWS Category Documents
    {
        "scheme_id": POST_MATRIC_ID,
        "category": "EWS",
        "document_name": "Economically Weaker Section (EWS) Certificate",
        "document_type": "ews_certificate",
        "is_mandatory": True,
        "conditions_description": "Income and Asset Certificate issued in accordance with DoPT Office Memorandum No. 36039/1/2019-Estt (Res).",
        "issuing_authority": "District Magistrate / Additional DM / Tahsildar",
        "accepted_formats": "PDF, JPG, PNG",
        "validity_rules": "Valid strictly for the current financial year",
    },
    {
        "scheme_id": PM_JAY_ID,
        "category": "EWS",
        "document_name": "EWS Certificate",
        "document_type": "ews_certificate",
        "is_mandatory": True,
        "conditions_description": "Verifying household family income <= ₹2,50,000 and asset compliance.",
        "issuing_authority": "Tahsildar / Sub-Divisional Officer",
        "accepted_formats": "PDF, JPG, PNG",
        "validity_rules": "Current financial year",
    },

    # MJPJAY Documents
    {
        "scheme_id": MJPJAY_ID,
        "category": "All",
        "document_name": "Maharashtra Ration Card (Yellow / Orange / AAY)",
        "document_type": "ration_card",
        "is_mandatory": True,
        "conditions_description": "Primary document for cashless hospital admission across 1,000+ empaneled hospitals in Maharashtra.",
        "issuing_authority": "Food, Civil Supplies and Consumer Protection Dept, Maharashtra",
        "accepted_formats": "PDF, JPG, PNG",
        "validity_rules": "Active family ration card",
    },
    {
        "scheme_id": MJPJAY_ID,
        "category": "All",
        "document_name": "Maharashtra Domicile Certificate",
        "document_type": "domicile_certificate",
        "is_mandatory": True,
        "conditions_description": "Proves 15+ years residency in Maharashtra if required by Arogyamitra.",
        "issuing_authority": "Tahsildar / Aaple Sarkar Portal",
        "accepted_formats": "PDF, JPG, PNG",
        "validity_rules": "Permanent",
    },
]


# ============================================================================
# 3. VERIFIED DETAILED DOCUMENT GUIDES (8 Core Documents)
# ============================================================================
DOCUMENT_GUIDES_SEED: List[Dict[str, Any]] = [
    {
        "document_type": "income_certificate",
        "document_name": "Income Certificate (Aamdani Praman Patra / Aavak Dakhlo)",
        "description": "An official government certificate issued by the Revenue Department stating the annual family income of a citizen from all sources. Essential for claiming welfare subsidies, educational scholarships, and healthcare exemptions.",
        "issuing_department": "Revenue and Land Reforms Department",
        "state_specific_authority": {
            "Maharashtra": "Tahsildar / Sub-Divisional Officer (SDO) via Aaple Sarkar Portal (aaplesarkar.mahaonline.gov.in)",
            "Gujarat": "Mamlatdar / Taluka Development Officer (TDO) via Digital Gujarat Portal (digitalgujarat.gov.in)",
            "Uttar Pradesh": "Tahsildar / Sub-Divisional Magistrate via eDistrict UP (edistrict.up.gov.in)",
            "All India": "Tahsildar / Sub-Divisional Magistrate / Revenue Circle Officer",
        },
        "required_supporting_documents": [
            "Proof of Identity: Voter ID / Driving License / PAN Card / Passport",
            "Proof of Address: Electricity Bill / Water Bill / Telephone Bill / Rent Agreement",
            "Proof of Income: Salary Slip / Form 16 / Income Tax Return / Employer Letter / Talati/Patwari Panchnama",
            "Ration Card copy showing all family members",
            "Self-declaration / Affidavit of annual family income on stamp paper or digital e-sign",
        ],
        "online_steps": {
            "en": [
                "1. Visit your state's official service portal (e.g., Aaple Sarkar in Maharashtra, Digital Gujarat in Gujarat, or eDistrict in UP).",
                "2. Register an account with your mobile number and email ID, then log in.",
                "3. Search for 'Revenue Department' and select 'Issue of Income Certificate'.",
                "4. Fill out the application form with personal details, family members' occupations, and annual income from all sources.",
                "5. Upload scanned copies of required proofs (Identity proof, Address proof, Income proof, and Ration card).",
                "6. Pay the statutory government processing fee (₹20 - ₹50) online via UPI/Net Banking.",
                "7. Download the acknowledgement receipt with the application tracking number. Upon verification by the Talati/Tahsildar, download your digitally signed certificate.",
            ],
            "hi": [
                "1. अपने राज्य के आधिकारिक ई-डिस्ट्रिक्ट पोर्टल (जैसे महाराष्ट्र में Aaple Sarkar, गुजरात में Digital Gujarat, या UP में eDistrict) पर जाएं।",
                "2. अपने मोबाइल नंबर से नया खाता पंजीकृत करें और लॉगिन करें।",
                "3. 'राजस्व विभाग' में जाकर 'आय प्रमाण पत्र (Income Certificate)' सेवा चुनें।",
                "4. परिवार के सभी सदस्यों की आय, व्यवसाय और व्यक्तिगत विवरण दर्ज करें।",
                "5. आवश्यक दस्तावेज (पहचान प्रमाण, निवास प्रमाण, आय प्रमाण, राशन कार्ड) अपलोड करें।",
                "6. निर्धारित सरकारी शुल्क (₹20 - ₹50) का ऑनलाइन भुगतान करें।",
                "7. आवेदन पावती रसीद प्राप्त करें। सत्यापन के बाद डिजिटल हस्ताक्षरित प्रमाण पत्र डाउनलोड करें।",
            ],
            "gu": [
                "1. તમારા રાજ્યના સત્તાવાર પોર્ટલ (જેમ કે ગુજરાતમાં digitalgujarat.gov.in) પર જાઓ.",
                "2. તમારા મોબાઈલ નંબર સાથે નોંધણી કરો અને લોગિન કરો.",
                "3. મહેસૂલ વિભાગમાં 'આવકનો દાખલો (Income Certificate)' પસંદ કરો.",
                "4. કુટુંબના તમામ સભ્યોની આવક અને વ્યક્તિગત વિગતો ભરો.",
                "5. જરૂરી પુરાવા (ઓળખ કાર્ડ, સરનામાનો પુરાવો, તલાટી પંચનામું/પગાર સ્લિપ) અપલોડ કરો.",
                "6. નિયત સરકારી ફીનું ઓનલાઇન ચુકવણી કરો.",
                "7. અરજી રસીદ મેળવો અને મામલતદાર મંજૂરી બાદ ડિજિટલ સહી થયેલ દાખલો ડાઉનલોડ કરો.",
            ],
        },
        "offline_steps": {
            "en": [
                "1. Visit the nearest Tahsil Office, Taluka Mamlatdar Office, or Citizen Service Center (CSC / Maha e-Seva Kendra / Jan Seva Kendra).",
                "2. Obtain the official physical Income Certificate Application Form from the citizen facilitation window.",
                "3. Obtain an income inquiry panchnama / verification report signed by your local Talati, Patwari, or Village Revenue Officer.",
                "4. Attach self-attested copies of your identity proof, address proof, ration card, and income documents.",
                "5. Submit the docket at the submission counter and pay the nominal statutory counter fee in cash (₹20 - ₹40).",
                "6. Collect the stamped acknowledgment slip containing your reference number and scheduled delivery date.",
                "7. Collect the original physical certificate bearing the official seal and signature of the Tahsildar / Executive Magistrate after 7-15 working days.",
            ],
            "hi": [
                "1. निकटतम तहसील कार्यालय, जन सेवा केंद्र (CSC) या महा ई-सेवा केंद्र पर जाएं।",
                "2. आय प्रमाण पत्र का आवेदन पत्र प्राप्त करें।",
                "3. अपने स्थानीय पटवारी या लेखपाल से आय सत्यापन आख्या (पंचनामा) प्राप्त करें।",
                "4. पहचान, निवास, राशन कार्ड और आय प्रमाण की स्व-प्रमाणित प्रतियां संलग्न करें।",
                "5. काउंटर पर फॉर्म जमा करें और निर्धारित सरकारी शुल्क का भुगतान करें।",
                "6. पावती रसीद प्राप्त करें और 7 से 15 कार्य दिवसों के भीतर सील बंद प्रमाण पत्र प्राप्त करें।",
            ],
            "gu": [
                "1. નજીકની મામલતદાર કચેરી અથવા જન સેવા કેન્દ્ર (CSC) ની મુલાકાત લો.",
                "2. આવકના દાખલા માટેનું અરજી ફોર્મ મેળવો.",
                "3. સ્થાનિક તલાટી કમ મંત્રી પાસેથી આવકનું પંચનામું કરાવો.",
                "4. ઓળખ, સરનામું, રેશનકાર્ડ અને આવકના પુરાવા જોડો.",
                "5. અરજી કાઉન્ટર પર જમા કરાવો અને નિર્ધારિત સરકારી ફી ચૂકવો.",
                "6. રસીદ મેળવો અને 7 થી 15 કામકાજના દિવસોમાં સીલવાળો દાખલો મેળવો.",
            ],
        },
        "fees_and_timelines": {
            "fee_disclaimer": "Fee and processing time may vary by state and application mode. Please confirm on the official state portal.",
            "statutory_fee_inr": 33,
            "csc_service_charge_inr": 20,
            "statutory_delivery_days": 15,
            "right_to_services_act": "Fee and processing time may vary by state and application mode. Please confirm on the official state portal. SLA governed under State Public Services Guarantee Acts (typically 15-21 working days).",
        },
        "official_links": {
            "all_india_portal": "https://services.india.gov.in",
            "maharashtra_portal": "https://aaplesarkar.mahaonline.gov.in",
            "gujarat_portal": "https://www.digitalgujarat.gov.in",
            "uttar_pradesh_portal": "https://edistrict.up.gov.in",
        },
        "languages_supported": ["en", "hi", "gu"],
    },

    {
        "document_type": "caste_certificate",
        "document_name": "Caste Certificate (Jati Praman Patra / Jati Dakhlo)",
        "description": "An official constitutional proof of membership in a Scheduled Caste (SC), Scheduled Tribe (ST), or Other Backward Class (OBC). Mandatory for availing affirmative action benefits, reserved educational seats, quota relaxations, and targeted welfare schemes.",
        "issuing_department": "Social Welfare Department / Revenue Department",
        "state_specific_authority": {
            "Maharashtra": "Sub-Divisional Officer (SDO) / Deputy Collector via Aaple Sarkar Portal",
            "Gujarat": "Taluka Development Officer (TDO) / Mamlatdar / District Social Welfare Officer via Digital Gujarat",
            "Uttar Pradesh": "Tahsildar / Sub-Divisional Magistrate via eDistrict UP",
            "All India": "Sub-Divisional Magistrate (SDM) / Deputy Commissioner / District Magistrate",
        },
        "required_supporting_documents": [
            "Proof of Applicant Identity: Voter ID / Passport / School Leaving Certificate",
            "Proof of Residence: Domicile certificate or electricity bill establishing continuous residence in the state",
            "Paternal Caste Evidence: Father's / Grandfather's School Leaving Certificate or primary school admission extract showing caste and date of admission before the statutory cut-off date (e.g., 1950 for SC/ST, 1967 for OBC in Maharashtra)",
            "Family tree genealogy affidavit (Vanshavali) attested by Notary or Executive Magistrate",
            "Caste certificate of father, paternal uncle, or blood relative from the father's side if already issued",
        ],
        "online_steps": {
            "en": [
                "1. Access the state citizen portal (e.g. Aaple Sarkar in Maharashtra, Digital Gujarat in Gujarat, or eDistrict in UP).",
                "2. Log in and select 'Social Justice and Special Assistance' -> 'Caste Certificate'.",
                "3. Select your category: Scheduled Caste (SC), Scheduled Tribe (ST), or Other Backward Classes (OBC).",
                "4. Enter genealogical details: father's name, grandfather's birthplace, native village, and family history.",
                "5. Upload mandatory paternal pre-cut-off records (Father's LC/T.C., Village Form 14 birth extract, or historical land documents).",
                "6. Complete online authentication / e-signature and pay the statutory state portal application fee.",
                "7. Track your application status online. Revenue authorities will conduct field verification before issuing the digital barcoded certificate.",
            ],
            "hi": [
                "1. राज्य पोर्टल (Aaple Sarkar, Digital Gujarat या eDistrict UP) पर जाएं।",
                "2. लॉगिन करें और 'सामाजिक न्याय एवं अधिकारिता विभाग' -> 'जाति प्रमाण पत्र' चुनें।",
                "3. अपनी श्रेणी (SC, ST, OBC) का चयन करें।",
                "4. पैतृक विवरण, पिता का नाम, पैतृक गांव और वंशावली की जानकारी भरें।",
                "5. कट-ऑफ तिथि से पूर्व के पैतृक दस्तावेज (पिता का स्कूल लीविंग सर्टिफिकेट, जन्म प्रमाण, आदि) अपलोड करें।",
                "6. ऑनलाइन आवेदन शुल्क का भुगतान करें और रसीद प्राप्त करें।",
                "7. स्थलीय सत्यापन (Field Inquiry) के बाद बारकोडेड डिजिटल जाति प्रमाण पत्र डाउनलोड करें।",
            ],
            "gu": [
                "1. રાજ્યના ડિજિટલ પોર્ટલ (digitalgujarat.gov.in) પર લોગિન કરો.",
                "2. સમાજ કલ્યાણ વિભાગમાંથી 'જાતિ પ્રમાણપત્ર (Caste Certificate)' સેવા પસંદ કરો.",
                "3. તમારી શ્રેણી (SC, ST, SEBC/OBC) પસંદ કરો.",
                "4. પિતાનું નામ, મૂળ વતન અને વંશાવળીની વિગતો દાખલ કરો.",
                "5. કટ-ઓફ તારીખ પહેલાના પિતૃ પક્ષના ઐતિહાસિક પુરાવા (શાળા છોડ્યાનું પ્રમાણપત્ર) અપલોડ કરો.",
                "6. સરકારી ફી ઓનલાઈન ભરો અને અરજી સબમિટ કરો.",
                "7. તપાસ અને મંજૂરી બાદ બારકોડવાળો ડિજિટલ જાતિનો દાખલો ડાઉનલોડ કરો.",
            ],
        },
        "offline_steps": {
            "en": [
                "1. Visit the Sub-Divisional Officer (SDO) or Taluka Mamlatdar office or CSC / Maha e-Seva center.",
                "2. Obtain Form A (Application for Caste Certificate under the relevant State Caste Rules).",
                "3. Prepare an affidavit of caste on judicial stamp paper certified by an Executive Magistrate or Notary.",
                "4. Attach certified true copies of your father's school record, paternal grandfather's birth/death extract, and domicile evidence.",
                "5. Submit the application file to the Revenue Inspector / Circle Officer desk for field panchnama.",
                "6. Cooperate with the Village Talati/Patwari during the neighborhood background enquiry.",
                "7. Collect the official physical Barcoded Caste Certificate from the dispatch counter after 21-30 working days.",
            ],
            "hi": [
                "1. उपमंडल अधिकारी (SDO) या तहसील कार्यालय के जन सेवा केंद्र पर जाएं।",
                "2. जाति प्रमाण पत्र हेतु निर्धारित प्रपत्र प्राप्त करें।",
                "3. नोटरी या कार्यपालक मजिस्ट्रेट द्वारा सत्यापित वंशावली शपथ पत्र तैयार करें।",
                "4. पिता के पुराने विद्यालय रिकॉर्ड, पूर्वजों के दस्तावेज और निवास प्रमाण संलग्न करें।",
                "5. राजस्व निरीक्षक काउंटर पर फाइल जमा करें और पावती प्राप्त करें।",
                "6. लेखपाल द्वारा स्थानीय जांच (पंचनामा) पूर्ण होने पर 21 से 30 कार्य दिवसों में प्रमाण पत्र प्राप्त करें।",
            ],
            "gu": [
                "1. પ્રાંત અધિકારી / મામલતદાર કચેરી અથવા જન સેવા કેન્દ્રની મુલાકાત લો.",
                "2. જાતિ પ્રમાણપત્ર મેળવવાનું નિયત અરજી ફોર્મ મેળવો.",
                "3. એક્ઝિક્યુટિવ મેજિસ્ટ્રેટ અથવા નોટરી સમક્ષ વંશાવળીનું સોગંદનામું કરાવો.",
                "4. પિતાના શાળા છોડ્યાના પ્રમાણપત્ર અને વંશાવળીના પુરાવા જોડો.",
                "5. સંબંધિત મહેસૂલ કાર્યાલયમાં અરજી જમા કરો.",
                "6. પંચનામા અને તપાસ બાદ 21 થી 30 દિવસમાં સત્તાવાર જાતિનો દાખલો મેળવો.",
            ],
        },
        "fees_and_timelines": {
            "fee_disclaimer": "Fee and processing time may vary by state and application mode. Please confirm on the official state portal.",
            "statutory_fee_inr": 45,
            "csc_service_charge_inr": 25,
            "statutory_delivery_days": 21,
            "right_to_services_act": "Fee and processing time may vary by state and application mode. Please confirm on the official state portal. Statutory delivery SLA within 21-30 working days under State Public Services Guarantee Acts.",
        },
        "official_links": {
            "all_india_portal": "https://services.india.gov.in",
            "maharashtra_portal": "https://aaplesarkar.mahaonline.gov.in",
            "gujarat_portal": "https://www.digitalgujarat.gov.in",
            "uttar_pradesh_portal": "https://edistrict.up.gov.in",
        },
        "languages_supported": ["en", "hi", "gu"],
    },

    {
        "document_type": "domicile_certificate",
        "document_name": "Domicile / Residence Certificate (Nivas Praman Patra / Adhivasi Dakhlo)",
        "description": "Certifies that a person has been a continuous permanent resident of a particular state for a mandatory period (typically 10-15 years). Essential for state quota reservations, government jobs, state scholarships, and regional welfare schemes.",
        "issuing_department": "General Administration Department / Revenue Department",
        "state_specific_authority": {
            "Maharashtra": "Tahsildar / Sub-Divisional Officer (SDO) via Aaple Sarkar",
            "Gujarat": "Executive Magistrate / Mamlatdar via Digital Gujarat",
            "Uttar Pradesh": "Sub-Divisional Magistrate (SDM) / Tahsildar via eDistrict UP",
            "All India": "Sub-Divisional Magistrate / District Collector / Tahsildar",
        },
        "required_supporting_documents": [
            "Proof of Continuous Residence: 10 to 15 years proof of residing in the state (School records from 1st standard to 10th standard, electricity bills, house property tax receipts)",
            "Birth Certificate of applicant showing place of birth within the state",
            "School Leaving Certificate (LC / TC) indicating birthplace and duration of study",
            "Ration Card or Electoral Photo ID Card (Voter ID) of parents and applicant",
            "Domicile Affidavit sworn before an Executive Magistrate or Notary",
        ],
        "online_steps": {
            "en": [
                "1. Log into your state citizen service portal (Aaple Sarkar / Digital Gujarat / eDistrict).",
                "2. Choose 'Revenue Department' -> 'Issuance of Domicile & Age/Nationality Certificate'.",
                "3. Fill out the duration of stay in the state year-by-year from birth or past 15 years.",
                "4. Upload continuous residency proofs: school marksheets/leaving certificates, property tax slips, or electricity bills.",
                "5. Upload notarized Domicile Affidavit and photo ID.",
                "6. Pay statutory fee (₹33) via portal payment gateway.",
                "7. Track your application. Following Talati enquiry, download digitally signed certificate.",
            ],
            "hi": [
                "1. राज्य ई-डिस्ट्रिक्ट पोर्टल पर लॉगिन करें।",
                "2. 'राजस्व विभाग' में जाकर 'मूल निवास / अधिवास प्रमाण पत्र (Domicile Certificate)' चुनें।",
                "3. राज्य में 15 वर्षों के निरंतर निवास का विवरण दर्ज करें।",
                "4. कक्षा 1 से 10वीं तक के स्कूल रिकॉर्ड, बिजली बिल और मकान कर की रसीदें अपलोड करें।",
                "5. नोटरीकृत निवास शपथ पत्र अपलोड करें और शुल्क का भुगतान करें।",
                "6. आवेदन पावती संख्या से स्थिति ट्रैक करें।",
                "7. सत्यापन उपरांत डिजिटल हस्ताक्षरित निवास प्रमाण पत्र प्राप्त करें।",
            ],
            "gu": [
                "1. રાજ્યના ડિજિટલ પોર્ટલ (digitalgujarat.gov.in) પર લોગિન કરો.",
                "2. 'મહેસૂલ વિભાગ' -> 'ડોમિસાઇલ / કાયમી રહેઠાણ પ્રમાણપત્ર' પસંદ કરો.",
                "3. રાજ્યમાં છેલ્લા 10-15 વર્ષથી સતત રહેઠાણની વિગતો દાખલ કરો.",
                "4. શાળા છોડ્યાનું પ્રમાણપત્ર, વેરા પહોંચ અને વીજળી બિલ જેવા પુરાવા અપલોડ કરો.",
                "5. સોગંદનામું અપલોડ કરો અને સરકારી ફી ચૂકવો.",
                "6. મામલતદાર ચકાસણી બાદ ડિજિટલ સહી કરેલ ડોમિસાઇલ પ્રમાણપત્ર ડાઉનલોડ કરો.",
            ],
        },
        "offline_steps": {
            "en": [
                "1. Visit the Executive Magistrate / Tahsildar office or CSC center.",
                "2. Fill the prescribed Domicile Application form.",
                "3. Attach proof of 15 years continuous residence in the state.",
                "4. Provide notarized residency affidavit.",
                "5. Submit file at counter and pay statutory fee.",
                "6. Talati/Patwari completes local spot inquiry.",
                "7. Collect certified Domicile Certificate after 15 working days.",
            ],
            "hi": [
                "1. तहसील या उपजिलाधिकारी कार्यालय के जन सेवा केंद्र पर जाएं।",
                "2. मूल निवास प्रमाण पत्र का निर्धारित फॉर्म भरें।",
                "3. 15 वर्षों के निवास के प्रमाण (शिक्षा रिकॉर्ड, संपत्ति रसीदें) संलग्न करें।",
                "4. शपथ पत्र संलग्न कर काउंटर पर जमा करें।",
                "5. 15 कार्य दिवसों के भीतर सीलबंद मूल निवास प्रमाण पत्र प्राप्त करें।",
            ],
            "gu": [
                "1. મામલતદાર કચેરી અથવા જન સેવા કેન્દ્ર પર જાઓ.",
                "2. ડોમિસાઇલ પ્રમાણપત્ર માટેનું અરજી ફોર્મ ભરો.",
                "3. 10 થી 15 વર્ષના સતત રહેઠાણના પુરાવા અને સોગંદનામું જોડો.",
                "4. કાઉન્ટર પર સબમિટ કરો અને રસીદ મેળવો.",
                "5. પંચનામા તપાસ બાદ 15 દિવસમાં દાખલો મેળવો.",
            ],
        },
        "fees_and_timelines": {
            "fee_disclaimer": "Fee and processing time may vary by state and application mode. Please confirm on the official state portal.",
            "statutory_fee_inr": 33,
            "csc_service_charge_inr": 20,
            "statutory_delivery_days": 15,
            "right_to_services_act": "Fee and processing time may vary by state and application mode. Please confirm on the official state portal. Guaranteed within 15-21 working days under Right to Public Services Act.",
        },
        "official_links": {
            "all_india_portal": "https://services.india.gov.in",
            "maharashtra_portal": "https://aaplesarkar.mahaonline.gov.in",
            "gujarat_portal": "https://www.digitalgujarat.gov.in",
            "uttar_pradesh_portal": "https://edistrict.up.gov.in",
        },
        "languages_supported": ["en", "hi", "gu"],
    },

    {
        "document_type": "ews_certificate",
        "document_name": "Economically Weaker Section (EWS) Certificate (Aarthik Kamzor Varg Praman Patra)",
        "description": "An official income and asset certificate entitling General Category citizens whose family income is below ₹8 Lakhs per annum to 10% constitutional reservation in education and public employment under the 103rd Constitutional Amendment Act.",
        "issuing_department": "Revenue Department / Department of Personnel and Training (DoPT)",
        "state_specific_authority": {
            "Maharashtra": "Sub-Divisional Officer (SDO) / Tahsildar via Aaple Sarkar",
            "Gujarat": "District Magistrate / Mamlatdar / TDO via Digital Gujarat",
            "Uttar Pradesh": "Tahsildar / Sub-Divisional Magistrate via eDistrict UP",
            "All India": "District Magistrate / Additional DM / Sub-Divisional Officer / Tahsildar",
        },
        "required_supporting_documents": [
            "Proof of General (Open) Category: Caste declaration confirming applicant does not belong to SC, ST, or OBC notified lists",
            "Family Annual Income Proof: Total gross annual family income below ₹8,00,000 for the preceding financial year from all sources (Salary, Agriculture, Business, Profession)",
            "Asset Proof showing family does NOT own: 5 acres of agricultural land and above; Residential flat of 1000 sq ft and above; Residential plot of 100 sq yards and above in notified municipalities; Residential plot of 200 sq yards and above in non-notified areas",
            "Property ownership documents / 7/12 extract / municipal house tax receipts",
            "Income Tax Returns (ITR-V) or Form 16 of earning family members for previous year",
            "Self-attested affidavit confirming non-ownership of excluded assets",
        ],
        "online_steps": {
            "en": [
                "1. Access your state's citizen service portal (Aaple Sarkar / Digital Gujarat / eDistrict).",
                "2. Navigate to 'Revenue Department' -> 'Issue of Income and Asset Certificate for Economically Weaker Section (EWS)'.",
                "3. Fill in applicant and family details (parents, spouse, children below 18 years).",
                "4. Disclose total agricultural landholding and residential property dimensions.",
                "5. Upload required documents: ITR/Income certificates, property tax slips, land 7/12 extract, and notarized EWS affidavit.",
                "6. Pay the processing fee online and note your tracking number.",
                "7. Download the digital barcoded EWS Certificate once field verification by the Circle Inspector is approved.",
            ],
            "hi": [
                "1. राज्य ई-डिस्ट्रिक्ट पोर्टल पर जाएं।",
                "2. 'राजस्व विभाग' में जाकर 'आर्थिक रूप से कमजोर वर्ग (EWS) आय एवं परिसंपत्ति प्रमाण पत्र' चुनें।",
                "3. आवेदक और परिवार के सभी सदस्यों की कुल वार्षिक आय (वेतन, कृषि, व्यवसाय) दर्ज करें।",
                "4. कृषि भूमि (5 एकड़ से कम) और आवासीय संपत्ति (1000 वर्ग फुट से कम) का विवरण भरें।",
                "5. आय कर रिटर्न (ITR), खतौनी/खसरा और शपथ पत्र अपलोड करें।",
                "6. शुल्क भुगतान करें और राजस्व जांच के बाद ई-डिस्ट्रिक्ट से बारकोडेड EWS प्रमाण पत्र प्राप्त करें।",
            ],
            "gu": [
                "1. રાજ્યના સેવા પોર્ટલ (digitalgujarat.gov.in) પર લોગિન કરો.",
                "2. 'બિન-અનામત વર્ગ માટે આર્થિક રીતે નબળા વર્ગ (EWS) પ્રમાણપત્ર' સેવા પસંદ કરો.",
                "3. કુટુંબની તમામ સ્ત્રોતમાંથી વાર્ષિક આવક (રૂ. ૮ લાખથી ઓછી) દાખલ કરો.",
                "4. ખેતીની જમીન અને મકાન ક્ષેત્રફળની મર્યાદાના પુરાવા દાખલ કરો.",
                "5. આવકના પુરાવા, મિલકત વેરા પહોંચ અને સોગંદનામું અપલોડ કરો.",
                "6. ઓનલાઈન ફી ચૂકવી મામલતદાર મંજૂરી બાદ ડિજિટલ સહી કરેલ EWS દાખલો મેળવો.",
            ],
        },
        "offline_steps": {
            "en": [
                "1. Visit the Sub-Divisional Officer (SDO) or Tahsil office.",
                "2. Collect the official Annexure-A EWS Application form.",
                "3. Attach certified land records, ITR copies, and municipal property valuation certificates.",
                "4. Submit the complete dossier along with the sworn affidavit of non-creamy assets.",
                "5. Local Revenue Inspector conducts physical site verification of land and dwelling.",
                "6. Receive the official sealed EWS Certificate after 15 to 21 working days.",
            ],
            "hi": [
                "1. उपमंडल अधिकारी या तहसील कार्यालय के जन सेवा केंद्र पर जाएं।",
                "2. EWS आवेदन फॉर्म (प्रारूप-क) प्राप्त करें।",
                "3. भूमि खतौनी, मकान कर रसीद और आय का शपथ पत्र संलग्न करें।",
                "4. काउंटर पर जमा करें; लेखपाल द्वारा संपत्ति और आय की स्थलीय जांच की जाएगी।",
                "5. 15 से 21 कार्य दिवसों में हस्ताक्षरित EWS प्रमाण पत्र प्राप्त करें।",
            ],
            "gu": [
                "1. પ્રાંત અધિકારી / મામલતદાર કચેરી અથવા જન સેવા કેન્દ્રની મુલાકાત લો.",
                "2. EWS પ્રમાણપત્ર મેળવવાનું ફોર્મ મેળવી જરૂરી વિગતો ભરો.",
                "3. આવક અને મિલકત મર્યાદાનું સોગંદનામું જોડો.",
                "4. તલાટી પંચનામા અને સ્થળ તપાસ બાદ કચેરીમાંથી EWS દાખલો મેળવો.",
            ],
        },
        "fees_and_timelines": {
            "fee_disclaimer": "Fee and processing time may vary by state and application mode. Please confirm on the official state portal.",
            "statutory_fee_inr": 50,
            "csc_service_charge_inr": 25,
            "statutory_delivery_days": 21,
            "right_to_services_act": "Fee and processing time may vary by state and application mode. Please confirm on the official state portal. Delivered within 21 working days under Public Services Guarantee Acts. Valid for current financial year.",
        },
        "official_links": {
            "all_india_portal": "https://services.india.gov.in",
            "maharashtra_portal": "https://aaplesarkar.mahaonline.gov.in",
            "gujarat_portal": "https://www.digitalgujarat.gov.in",
            "uttar_pradesh_portal": "https://edistrict.up.gov.in",
        },
        "languages_supported": ["en", "hi", "gu"],
    },

    {
        "document_type": "non_creamy_layer",
        "document_name": "Non-Creamy Layer (NCL) Certificate (Non-Creamy Layer Praman Patra / Unnat Varg Nathi)",
        "description": "Certifies that an Other Backward Class (OBC / SEBC / VJNT) citizen belongs to the non-creamy layer (annual parental income below ₹8 Lakhs for past 3 consecutive years). Mandatory for OBC reservation in government jobs, civil services, IIT/IIM/NEET admissions, and central/state scholarships.",
        "issuing_department": "Social Justice and Special Assistance Department / Revenue Department",
        "state_specific_authority": {
            "Maharashtra": "Sub-Divisional Officer (SDO) / Tahsildar via Aaple Sarkar",
            "Gujarat": "Taluka Development Officer (TDO) / Mamlatdar via Digital Gujarat",
            "Uttar Pradesh": "Tahsildar / SDM via eDistrict UP",
            "All India": "Sub-Divisional Magistrate / Deputy Commissioner / Tahsildar",
        },
        "required_supporting_documents": [
            "Valid OBC / SEBC / VJNT Caste Certificate of applicant",
            "Income Proof of parents for the last three consecutive financial years (Form 16 / ITR / Talati Income Certificate)",
            "Proof of residence and identity: Domicile Certificate, Voter ID, Ration Card",
            "Father's and Mother's employment status declaration (confirming non-Class I / Class II Gazetted status before age 40)",
            "Affidavit on judicial stamp paper stating non-creamy layer compliance under Central/State OBC guidelines",
        ],
        "online_steps": {
            "en": [
                "1. Log into your state citizen portal (Aaple Sarkar, Digital Gujarat, or eDistrict).",
                "2. Choose 'Revenue Department' -> 'Issuance of Non-Creamy Layer Certificate'.",
                "3. Select category (OBC, VJ/NT, SBC) and input your Caste Certificate registration number.",
                "4. Enter parents' annual income for the preceding 3 consecutive financial years.",
                "5. Upload scanned documents (Caste Certificate, 3 years' income proofs/ITR, Address proof, and sworn affidavit).",
                "6. Pay statutory portal processing charges online.",
                "7. Download the digitally verified NCL Certificate valid for the current financial year upon Tahsildar approval.",
            ],
            "hi": [
                "1. राज्य पोर्टल पर लॉगिन करें।",
                "2. 'राजस्व विभाग' में जाकर 'नॉन-क्रीमी लेयर प्रमाण पत्र (NCL)' चुनें।",
                "3. अपना OBC जाति प्रमाण पत्र क्रमांक और जारी करने की तिथि दर्ज करें।",
                "4. पिछले 3 वित्तीय वर्षों की माता-पिता की आय का विवरण दर्ज करें।",
                "5. जाति प्रमाण पत्र, 3 वर्षों के आय प्रमाण/ITR और शपथ पत्र अपलोड करें।",
                "6. ऑनलाइन शुल्क का भुगतान करें।",
                "7. तहसीलदार की स्वीकृति के उपरांत डिजिटल नॉन-क्रीमी लेयर प्रमाण पत्र प्राप्त करें।",
            ],
            "gu": [
                "1. digitalgujarat.gov.in પોર્ટલ પર લોગિન કરો.",
                "2. 'સામાજિક ન્યાય અને અધિકારિતા વિભાગ' -> 'ઉન્નત વર્ગમાં સમાવેશ ન થવા અંગેનું પ્રમાણપત્ર (Non-Creamy Layer)' પસંદ કરો.",
                "3. SEBC/OBC જાતિના દાખલાનો નંબર દાખલ કરો.",
                "4. છેલ્લા ૩ વર્ષની વાર્ષિક આવકની વિગતો દાખલ કરો.",
                "5. જાતિનો દાખલો, આવકના પુરાવા અને પરિશિષ્ટ-૪ નું સોગંદનામું અપલોડ કરો.",
                "6. સરકારી ફી ઓનલાઈન ભરી મામલતદાર મંજૂરી બાદ ડિજિટલ સહી કરેલ NCL દાખલો મેળવો.",
            ],
        },
        "offline_steps": {
            "en": [
                "1. Visit the Sub-Divisional Office, Tahsil Office, or CSC facilitation desk.",
                "2. Procure the physical NCL Application form.",
                "3. Attach certified copies of OBC caste certificate and 3 consecutive years' income tax returns or revenue certificates.",
                "4. Attach sworn NCL affidavit attested by an Executive Magistrate.",
                "5. Submit docket at the citizen service counter and receive stamped acknowledgment slip.",
                "6. Spot enquiry conducted by Circle Revenue Officer.",
                "7. Collect certified physical Non-Creamy Layer Certificate after 15 to 21 working days.",
            ],
            "hi": [
                "1. उपमंडल अधिकारी या तहसील के जन सेवा केंद्र पर जाएं।",
                "2. नॉन-क्रीमी लेयर आवेदन प्रपत्र प्राप्त करें।",
                "3. जाति प्रमाण पत्र, 3 वर्षों का आय प्रमाण और नोटरी शपथ पत्र संलग्न करें।",
                "4. काउंटर पर जमा करें और पावती प्राप्त करें।",
                "5. राजस्व जांच उपरांत 15 से 21 कार्य दिवसों में प्रमाण पत्र प्राप्त करें।",
            ],
            "gu": [
                "1. મામલતદાર કચેરી અથવા જન સેવા કેન્દ્ર પર જાઓ.",
                "2. નોન-ક્રીમી લેયર માટેનું નિયત અરજી ફોર્મ મેળવો.",
                "3. જાતિ પ્રમાણપત્ર, ૩ વર્ષના આવકના પુરાવા અને સોગંદનામું જોડો.",
                "4. અરજી કાઉન્ટર પર જમા કરો અને તપાસ બાદ ૧૫ થી ૨૧ દિવસમાં દાખલો મેળવો.",
            ],
        },
        "fees_and_timelines": {
            "fee_disclaimer": "Fee and processing time may vary by state and application mode. Please confirm on the official state portal.",
            "statutory_fee_inr": 45,
            "csc_service_charge_inr": 25,
            "statutory_delivery_days": 21,
            "right_to_services_act": "Fee and processing time may vary by state and application mode. Please confirm on the official state portal. Delivered within 21 working days under Public Services Guarantee Acts. Valid for 1 to 3 financial years per state rules.",
        },
        "official_links": {
            "all_india_portal": "https://services.india.gov.in",
            "maharashtra_portal": "https://aaplesarkar.mahaonline.gov.in",
            "gujarat_portal": "https://www.digitalgujarat.gov.in",
            "uttar_pradesh_portal": "https://edistrict.up.gov.in",
        },
        "languages_supported": ["en", "hi", "gu"],
    },

    {
        "document_type": "land_record",
        "document_name": "Land Record (7/12 Extract / RoR / Khasra Khatauni)",
        "description": "An official revenue record of rights documenting land ownership, survey number, area in hectares, type of cultivation, and existing encumbrances/crop loans. Mandatory for agricultural welfare schemes like PM-KISAN, crop insurance, and subsidies.",
        "issuing_department": "Land Records and Settlement Department / Revenue Department",
        "state_specific_authority": {
            "Maharashtra": "Talati / Settlement Commissioner via Mahabhulekh Portal (bhulekh.mahabhumi.gov.in)",
            "Gujarat": "Talati-cum-Mantri / Revenue Department via AnyRoR Portal (anyror.gujarat.gov.in)",
            "Uttar Pradesh": "Lekhpal / Board of Revenue via UP Bhulekh (upbhulekh.gov.in)",
            "All India": "Patwari / Revenue Circle Officer / Land Records Department",
        },
        "required_supporting_documents": [
            "District, Taluka/Tahsil, and Village name where the agricultural land is situated",
            "Survey Number / Gat Number / Khasra Number of the plot",
            "Khata / Khatauni Account Number",
            "Government Photo ID of the landholder (Voter ID, PAN, Driving License) for identity verification during digital download or registry search",
        ],
        "online_steps": {
            "en": [
                "1. Visit your state's land records portal (e.g. Mahabhulekh in Maharashtra, AnyRoR in Gujarat, or UP Bhulekh in UP).",
                "2. Select your District, Taluka/Tehsil, and Village from the dropdown menus.",
                "3. Search for your land record by entering either the Survey Number / Gat Number or Khatauni account number.",
                "4. View the digitally generated 7/12 extract or Khasra-Khatauni details on screen.",
                "5. For a legally admissible digital signed copy (with QR code), log in to the state digital signature portal (e.g. Mahabhumi Digital 7/12).",
                "6. Pay nominal fee of ₹15 per digital 7/12 copy via UPI/Net Banking.",
                "7. Download and print the legally certified digital land record.",
            ],
            "hi": [
                "1. अपने राज्य के भूलेख पोर्टल (जैसे UP में upbhulekh.gov.in या महाराष्ट्र में bhulekh.mahabhumi.gov.in) पर जाएं।",
                "2. अपना जनपद (जिला), तहसील और ग्राम चुनें।",
                "3. खसरा संख्या, गाटा संख्या या खातेदार के नाम से खोजें।",
                "4. कंप्यूटर स्क्रीन पर अपनी खतौनी / 7/12 नकल का विवरण देखें।",
                "5. प्रमाणित डिजिटल हस्ताक्षरित प्रति हेतु निर्धारित सरकारी शुल्क (₹15) का भुगतान करें।",
                "6. QR कोड युक्त प्रमाणित नकल डाउनलोड करें।",
            ],
            "gu": [
                "1. ગુજરાત સરકારના AnyRoR પોર્ટલ (anyror.gujarat.gov.in) પર જાઓ.",
                "2. 'ગ્રામ્ય જમીનનો રેકોર્ડ' પસંદ કરી જિલ્લો, તાલુકો અને ગામ પસંદ કરો.",
                "3. સર્વે નંબર / ખાતા નંબર અથવા ખાતેદારના નામ પરથી શોધ કરો.",
                "4. સ્ક્રીન પર ૭/૧૨ અને ૮-અ ની વિગતો જુઓ.",
                "5. ડિજિટલ સહીવાળી નકલ મેળવવા માટે રૂ. ૧૫ ઓનલાઇન ચૂકવો.",
                "6. કાયદેસર રીતે માન્ય બારકોડવાળી ૭/૧૨ નકલ ડાઉનલોડ કરો.",
            ],
        },
        "offline_steps": {
            "en": [
                "1. Visit the local Village Panchayat / Talati / Patwari office or Tahsil Bhulekh Kendra.",
                "2. Provide your Gat / Survey number and landholder name.",
                "3. Talati checks Village Form VII and XII registers and generates the certified extract.",
                "4. Pay statutory nominal stamp fee (₹15 - ₹20).",
                "5. Collect the physical certified 7/12 extract bearing the rubber stamp and official signature of the Talati/Patwari.",
            ],
            "hi": [
                "1. ग्राम पंचायत कार्यालय या तहसील के भूलेख काउंटर पर जाएं।",
                "2. लेखपाल या पटवारी को अपना खसरा/गाटा संख्या बताएं।",
                "3. निर्धारित नकल शुल्क (₹15) जमा करें।",
                "4. पटवारी के हस्ताक्षर और सील वाली प्रमाणित खतौनी प्राप्त करें।",
            ],
            "gu": [
                "1. ગામની પંચાયત કચેરીમાં તલાટી કમ મંત્રીની મુલાકાત લો.",
                "2. જમીનનો સર્વે નંબર અથવા ખાતા નંબર આપો.",
                "3. નિયત ફી ચૂકવી તલાટીના સહી-સિક્કાવાળી ૭/૧૨ ની નકલ મેળવો.",
            ],
        },
        "fees_and_timelines": {
            "fee_disclaimer": "Fee and processing time may vary by state and application mode. Please confirm on the official state portal.",
            "statutory_fee_inr": 15,
            "csc_service_charge_inr": 10,
            "statutory_delivery_days": 1,
            "right_to_services_act": "Fee and processing time may vary by state and application mode. Please confirm on the official state portal. Digital view is free; digitally signed copy fee is state-dependent.",
        },
        "official_links": {
            "national_portal": "https://dilrmp.gov.in",
            "maharashtra_portal": "https://bhulekh.mahabhumi.gov.in",
            "gujarat_portal": "https://anyror.gujarat.gov.in",
            "uttar_pradesh_portal": "https://upbhulekh.gov.in",
        },
        "languages_supported": ["en", "hi", "gu"],
    },

    {
        "document_type": "ration_card",
        "document_name": "Ration Card (Rashan Card / NFSA / Antyodaya Card)",
        "description": "An official government document issued under the National Food Security Act (NFSA) certifying household entitlement to subsidized foodgrains and fuel. Serves as the primary evidence of family composition and economic status for social welfare schemes.",
        "issuing_department": "Food, Civil Supplies and Consumer Affairs Department",
        "state_specific_authority": {
            "Maharashtra": "District Supply Officer (DSO) / Tahsildar / Food Distribution Officer (FDO) via RCMS",
            "Gujarat": "District Supply Officer / Mamlatdar via DCS Gujarat Portal",
            "Uttar Pradesh": "District Supply Officer / Regional Food Controller via FCS UP",
            "All India": "Food and Civil Supplies Department / District Supply Officer",
        },
        "required_supporting_documents": [
            "Proof of Residence: Electricity Bill / Rent Agreement / Telephone Bill / LPG Gas Connection Book",
            "Identity Proof of Head of Family: Voter ID / Driving License / Passport",
            "Birth Certificate of all minor family members; School record for children",
            "Income Certificate issued by Tahsildar showing annual family income",
            "Surrender Certificate / Deletion Certificate from previous residence if relocating",
            "Joint family photograph of all family members",
        ],
        "online_steps": {
            "en": [
                "1. Access your state's Food and Civil Supplies portal (e.g. Mahafood in Maharashtra, DCS Gujarat in Gujarat, or FCS UP in UP).",
                "2. Register an account as Head of Family with mobile number and email ID.",
                "3. Select 'Apply for New Digital Ration Card' (NFSA BPL, APL, or Antyodaya).",
                "4. Enter residential address, gas connection details, and annual household income.",
                "5. Add all family members with their names, relationships, dates of birth, and identity proofs.",
                "6. Upload scanned family photograph, address proof, and income certificate.",
                "7. Submit and note the NFSA application reference number for tracking.",
                "8. Ration Inspector conducts field verification before the digital ration card (RCMS) is activated.",
            ],
            "hi": [
                "1. खाद्य एवं रसद विभाग के आधिकारिक पोर्टल (FCS UP, Mahafood आदि) पर जाएं।",
                "2. परिवार के मुखिया के नाम से नया पंजीकरण करें।",
                "3. 'नवीन डिजिटल राशन कार्ड आवेदन' विकल्प चुनें।",
                "4. परिवार के सभी सदस्यों के नाम, संबंध, जन्मतिथि और पहचान विवरण दर्ज करें।",
                "5. निवास प्रमाण, आय प्रमाण और संयुक्त परिवार फोटो अपलोड करें।",
                "6. ऑनलाइन आवेदन सबमिट कर पावती रसीद प्राप्त करें।",
                "7. पूर्ति निरीक्षक (Supply Inspector) द्वारा जांच के बाद डिजिटल राशन कार्ड जारी किया जाता है।",
            ],
            "gu": [
                "1. અન્ન અને નાગરિક પુરવઠા વિભાગના પોર્ટલ (digitalgujarat.gov.in) પર જાઓ.",
                "2. 'નવા ડિજિટલ રેશનકાર્ડ માટેની અરજી' સેવા પસંદ કરો.",
                "3. કુટુંબના મોભી અને તમામ સભ્યોની સંપૂર્ણ વિગતો દાખલ કરો.",
                "4. ગેસ કનેક્શન નંબર, સરનામાનો પુરાવો અને આવકનો દાખલો અપલોડ કરો.",
                "5. કુટુંબનો સંયુક્ત ફોટોગ્રાફ અપલોડ કરો.",
                "6. અરજી સબમિટ કરી રસીદ મેળવો. પુરવઠા નિરીક્ષકની તપાસ બાદ રેશનકાર્ડ મળશે.",
            ],
        },
        "offline_steps": {
            "en": [
                "1. Visit the local Tahsil Office (Supply Department) or District Supply Office.",
                "2. Collect the printed Ration Card Application Form (Form A).",
                "3. Attach joint family photograph and self-attested copies of address and income proofs.",
                "4. Submit the dossier at the Food & Civil Supplies facilitation counter.",
                "5. Rationing Inspector verifies the residence and household particulars.",
                "6. Collect the official physical Ration Card booklet after 30 working days.",
            ],
            "hi": [
                "1. तहसील के खाद्य एवं आपूर्ति कार्यालय या जन सेवा केंद्र पर जाएं।",
                "2. राशन कार्ड आवेदन फॉर्म (प्रारूप-क) प्राप्त करें।",
                "3. पूरे परिवार की संयुक्त फोटो और निवास/आय प्रमाण की प्रति संलग्न करें।",
                "4. काउंटर पर फॉर्म जमा करें और रसीद प्राप्त करें।",
                "5. पूर्ति निरीक्षक की स्थलीय जांच उपरांत 30 दिनों में राशन कार्ड प्राप्त करें।",
            ],
            "gu": [
                "1. તાલુકા મામલતદાર કચેરી (પુરવઠા શાખા) અથવા જન સેવા કેન્દ્રની મુલાકાત લો.",
                "2. રેશનકાર્ડ માટેનું અરજી ફોર્મ મેળવી વિગતો ભરો.",
                "3. કુટુંબનો સંયુક્ત ફોટો અને પુરાવા જોડો.",
                "4. પુરવઠા શાખામાં જમા કરો અને ૩૦ કામકાજના દિવસોમાં રેશનકાર્ડ મેળવો.",
            ],
        },
        "fees_and_timelines": {
            "fee_disclaimer": "Fee and processing time may vary by state and application mode. Please confirm on the official state portal.",
            "statutory_fee_inr": 20,
            "csc_service_charge_inr": 15,
            "statutory_delivery_days": 30,
            "right_to_services_act": "Fee and processing time may vary by state and application mode. Please confirm on the official state portal. Delivery governed by State Food & Civil Supplies rules (typically 30 working days).",
        },
        "official_links": {
            "national_portal": "https://nfsa.gov.in",
            "maharashtra_portal": "https://mahafood.gov.in",
            "gujarat_portal": "https://dcs-dof.gujarat.gov.in",
            "uttar_pradesh_portal": "https://fcs.up.gov.in",
        },
        "languages_supported": ["en", "hi", "gu"],
    },

    {
        "document_type": "bank_passbook",
        "document_name": "Bank Passbook / Account Statement (Bank Khata Pustika)",
        "description": "An official transaction ledger or verified account statement issued by a Scheduled Commercial Bank or Postal Payment Bank documenting account holder identity, Core Banking Account Number, and active IFSC code. Essential for receiving Direct Benefit Transfer (DBT) subsidies.",
        "issuing_department": "Reserve Bank of India / Scheduled Commercial Banks / India Post Payments Bank",
        "state_specific_authority": {
            "Maharashtra": "Any Nationalized / Scheduled Commercial Bank branch in Maharashtra",
            "Gujarat": "Any Nationalized / Scheduled Commercial Bank branch in Gujarat",
            "Uttar Pradesh": "Any Nationalized / Scheduled Commercial Bank branch in Uttar Pradesh",
            "All India": "Nationalized Banks, Regional Rural Banks (RRB), or India Post Payments Bank (IPPB)",
        },
        "required_supporting_documents": [
            "Official Valid Document (OVD) for KYC: Voter ID / Driving License / Passport / NREGA Job Card",
            "Two recent passport size color photographs",
            "Proof of local residence address",
            "PAN Card or Form 60 if PAN is not available",
        ],
        "online_steps": {
            "en": [
                "1. Log into your bank's official mobile banking application or internet banking portal.",
                "2. Navigate to 'Account Summary' -> 'Download e-Statement' or 'View Passbook'.",
                "3. Select the account statement duration (e.g., past 3 to 6 months).",
                "4. Generate and download the official computer-generated PDF statement bearing bank logo and active IFSC code.",
                "5. Ensure the citizen's full legal name, account number, and bank branch IFSC code are clearly visible on the front page.",
            ],
            "hi": [
                "1. अपने बैंक के आधिकारिक मोबाइल बैंकिंग ऐप अथवा नेट बैंकिंग पोर्टल में लॉगिन करें।",
                "2. 'खाता विवरण (Account Statement)' अथवा 'ई-पासबुक' विकल्प पर जाएं।",
                "3. 3 से 6 महीने का विवरण चुनें।",
                "4. बैंक का लोगो, खाता संख्या और IFSC कोड प्रदर्शित करने वाली PDF फाइल डाउनलोड करें।",
                "5. खाताधारक का नाम और शाखा IFSC कोड स्पष्ट रूप से दिखना चाहिए।",
            ],
            "gu": [
                "1. તમારા બેંકની સત્તાવાર મોબાઈલ એપ અથવા ઇન્ટરનેટ બેંકિંગ પોર્ટલમાં લોગિન કરો.",
                "2. 'ખાતા સ્ટેટમેન્ટ / ઇ-પાસબુક' પસંદ કરો.",
                "3. છેલ્લા ૩ થી ૬ મહિનાનો સમયગાળો પસંદ કરો.",
                "4. બેંક લોગો, ખાતા નંબર અને IFSC કોડ દર્શાવતી સત્તાવાર PDF ડાઉનલોડ કરો.",
            ],
        },
        "offline_steps": {
            "en": [
                "1. Visit your local home branch of the bank where your savings account is maintained.",
                "2. Carry your physical passbook to the Passbook Printing Kiosk or teller counter.",
                "3. Print latest transaction entries up to date.",
                "4. Request the bank branch officer to place the branch seal and officer signature on the first page if required for government subsidy submission.",
            ],
            "hi": [
                "1. अपनी गृह बैंक शाखा (Home Branch) में जाएं।",
                "2. पासबुक प्रिंटिंग कियोस्क या काउंटर पर पासबुक अपडेट कराएं।",
                "3. प्रथम पृष्ठ (जिसमें नाम, खाता संख्या और IFSC दर्ज हो) की स्पष्ट फोटोकॉपी कराएं।",
                "4. सरकारी योजना में जमा करने हेतु बैंक अधिकारी से सील और हस्ताक्षर कराएं।",
            ],
            "gu": [
                "1. તમારા બેંકની હોમ બ્રાંચની મુલાકાત લો.",
                "2. પાસબુક પ્રિન્ટિંગ મશીન અથવા કાઉન્ટર પર પાસબુક અપડેટ કરાવો.",
                "3. પ્રથમ પાનાની સ્પષ્ટ ઝેરોક્ષ કરાવી બેંક અધિકારીના સિક્કા કરાવો.",
            ],
        },
        "fees_and_timelines": {
            "fee_disclaimer": "Fee and processing time may vary by state and application mode. Please confirm on the official state portal.",
            "statutory_fee_inr": 0,
            "csc_service_charge_inr": 0,
            "statutory_delivery_days": 1,
            "right_to_services_act": "Free of cost at bank branches for standard savings accounts. Passbook issuance governed by RBI Master Directions on Customer Service.",
        },
        "official_links": {
            "dbt_bharat_portal": "https://dbtbharat.gov.in",
            "india_post_payments_bank": "https://www.ippbonline.com",
            "rbi_customer_services": "https://rbi.org.in",
        },
        "languages_supported": ["en", "hi", "gu"],
    },
]


# ============================================================================
# 4. VERIFIED OFFICIAL SCHEME BENEFICIARY DATASETS & BREAKDOWNS
# ============================================================================
ANALYTICS_DATASETS_SEED: List[Dict[str, Any]] = [
    # 1. PM-KISAN
    {
        "scheme_id": PM_KISAN_ID,
        "source_name": "Ministry of Agriculture and Farmers Welfare, GoI (PM-KISAN National MIS Dashboard)",
        "report_title": "PM-KISAN National MIS Dashboard & 16th Installment Release Report",
        "source_url": "https://pmkisan.gov.in/",
        "source_publication_date": datetime(2024, 2, 28, tzinfo=timezone.utc),
        "reporting_period": "FY 2023-24 (16th Installment Disbursement)",
        "geographic_scope": "National",
        "metric_type": "unique_farmer_households",
        "metric_definition": "Total verified unique operational landholder farmer families receiving DBT assistance under PM-KISAN",
        "total_beneficiaries": 110000000,
        "dataset_version": 1,
        "verification_status": "Verified",
        "is_published": True,
        "published_at": datetime(2024, 3, 1, tzinfo=timezone.utc),
        "last_verified_at": datetime(2024, 3, 1, tzinfo=timezone.utc),
        "notes": "Aggregate verified beneficiaries receiving ₹6,000 annual direct benefit transfer under PM-KISAN 16th installment. Caste-wise data is excluded as it is not officially reported on the public open dashboard.",
        "breakdowns": [
            # Gender (Verified official MIS proportion)
            {"dimension": "gender", "category_name": "Male", "metric_value": 81400000, "percentage": 74.0, "notes": "Male registered operational landholders"},
            {"dimension": "gender", "category_name": "Female", "metric_value": 28600000, "percentage": 26.0, "notes": "Female landholding farmers"},
            # State Distribution (Top States)
            {"dimension": "state", "category_name": "Uttar Pradesh", "metric_value": 24200000, "percentage": 22.0, "notes": "Highest state coverage in India"},
            {"dimension": "state", "category_name": "Maharashtra", "metric_value": 11000000, "percentage": 10.0, "notes": "Integrated with Namo Shetkari Mahasanman Nidhi"},
            {"dimension": "state", "category_name": "Madhya Pradesh", "metric_value": 8800000, "percentage": 8.0, "notes": "Central zone"},
            {"dimension": "state", "category_name": "Bihar", "metric_value": 8250000, "percentage": 7.5, "notes": "Eastern zone"},
            {"dimension": "state", "category_name": "Gujarat", "metric_value": 6050000, "percentage": 5.5, "notes": "Western zone"},
            {"dimension": "state", "category_name": "Rajasthan", "metric_value": 7150000, "percentage": 6.5, "notes": "North-western zone"},
            {"dimension": "state", "category_name": "Other States/UTs", "metric_value": 44600000, "percentage": 40.5, "notes": "Remaining 30 states and union territories"},
            # Yearly Trend
            {"dimension": "yearly_trend", "category_name": "FY 2021-22", "metric_value": 104000000, "percentage": None, "notes": "Annual active unique beneficiaries"},
            {"dimension": "yearly_trend", "category_name": "FY 2022-23", "metric_value": 107000000, "percentage": None, "notes": "Annual active unique beneficiaries"},
            {"dimension": "yearly_trend", "category_name": "FY 2023-24", "metric_value": 110000000, "percentage": None, "notes": "Annual active unique beneficiaries"},
        ],
    },

    # 2. Ayushman Bharat PM-JAY
    {
        "scheme_id": PM_JAY_ID,
        "source_name": "National Health Authority (NHA), Ministry of Health & Family Welfare",
        "report_title": "National Health Authority Annual Report & AB-PMJAY Public Dashboard",
        "source_url": "https://dashboard.pmjay.gov.in/",
        "source_publication_date": datetime(2024, 3, 31, tzinfo=timezone.utc),
        "reporting_period": "Cumulative as of FY 2023-24",
        "geographic_scope": "National",
        "metric_type": "ayushman_cards_issued",
        "metric_definition": "Cumulative count of individual Ayushman Cards created and verified (distinct from hospital admissions)",
        "total_beneficiaries": 345000000,
        "dataset_version": 1,
        "verification_status": "Verified",
        "is_published": True,
        "published_at": datetime(2024, 4, 1, tzinfo=timezone.utc),
        "last_verified_at": datetime(2024, 4, 1, tzinfo=timezone.utc),
        "notes": "Verified count of Ayushman cards generated. Metrics separated: distinct from hospital admissions (over 6.5 Cr) and authorized procedures.",
        "breakdowns": [
            # Gender (Verified equitable card creation)
            {"dimension": "gender", "category_name": "Female", "metric_value": 169050000, "percentage": 49.0, "notes": "Gender equitable card creation"},
            {"dimension": "gender", "category_name": "Male", "metric_value": 175950000, "percentage": 51.0, "notes": "Male cardholders"},
            # Top States
            {"dimension": "state", "category_name": "Uttar Pradesh", "metric_value": 48300000, "percentage": 14.0, "notes": "Highest cards issued state-wide"},
            {"dimension": "state", "category_name": "Madhya Pradesh", "metric_value": 37950000, "percentage": 11.0, "notes": "Central zone"},
            {"dimension": "state", "category_name": "Maharashtra", "metric_value": 24150000, "percentage": 7.0, "notes": "Integrated PM-JAY & MJPJAY pool"},
            {"dimension": "state", "category_name": "Gujarat", "metric_value": 20700000, "percentage": 6.0, "notes": "PMJAY-MA integrated scheme"},
            {"dimension": "state", "category_name": "Tamil Nadu", "metric_value": 31050000, "percentage": 9.0, "notes": "CMCHIS integrated pool"},
            {"dimension": "state", "category_name": "Other States/UTs", "metric_value": 182850000, "percentage": 53.0, "notes": "Remaining states and UTs"},
            # Yearly Trend
            {"dimension": "yearly_trend", "category_name": "FY 2021-22", "metric_value": 182000000, "percentage": None, "notes": "Cumulative cards"},
            {"dimension": "yearly_trend", "category_name": "FY 2022-23", "metric_value": 240000000, "percentage": None, "notes": "Cumulative cards"},
            {"dimension": "yearly_trend", "category_name": "FY 2023-24", "metric_value": 345000000, "percentage": None, "notes": "Cumulative cards"},
        ],
    },

    # 3. PMAY-G (Housing)
    {
        "scheme_id": PMAY_G_ID,
        "source_name": "Ministry of Rural Development, GoI (AwaasSoft MIS Reporting)",
        "report_title": "AwaasSoft Rural Housing Reporting Dashboard (rhreporting.nic.in)",
        "source_url": "https://rhreporting.nic.in/",
        "source_publication_date": datetime(2024, 3, 31, tzinfo=timezone.utc),
        "reporting_period": "Cumulative Phase I & II (FY 2016-2024)",
        "geographic_scope": "National",
        "metric_type": "houses_sanctioned",
        "metric_definition": "Total verified permanent rural houses sanctioned under PMAY-G (distinct from completed houses)",
        "total_beneficiaries": 26200000,
        "dataset_version": 1,
        "verification_status": "Verified",
        "is_published": True,
        "published_at": datetime(2024, 4, 1, tzinfo=timezone.utc),
        "last_verified_at": datetime(2024, 4, 1, tzinfo=timezone.utc),
        "notes": "Verified count of pucca houses sanctioned under Pradhan Mantri Awaas Yojana - Gramin. Distinct metric from completed houses (2.58 Cr).",
        "breakdowns": [
            # Ownership / Gender
            {"dimension": "gender", "category_name": "Female / Joint Ownership", "metric_value": 18340000, "percentage": 70.0, "notes": "Mandatory female title or joint spousal ownership"},
            {"dimension": "gender", "category_name": "Male Sole Ownership", "metric_value": 7860000, "percentage": 30.0, "notes": "Male sole ownership"},
            # State Distribution
            {"dimension": "state", "category_name": "Madhya Pradesh", "metric_value": 3668000, "percentage": 14.0, "notes": "Central zone"},
            {"dimension": "state", "category_name": "Uttar Pradesh", "metric_value": 3406000, "percentage": 13.0, "notes": "Northern zone"},
            {"dimension": "state", "category_name": "Bihar", "metric_value": 3144000, "percentage": 12.0, "notes": "Eastern zone"},
            {"dimension": "state", "category_name": "Maharashtra", "metric_value": 1572000, "percentage": 6.0, "notes": "Western zone"},
            {"dimension": "state", "category_name": "Other States/UTs", "metric_value": 14410000, "percentage": 55.0, "notes": "Remaining rural areas across India"},
            # Yearly Trend
            {"dimension": "yearly_trend", "category_name": "FY 2021-22", "metric_value": 18000000, "percentage": None, "notes": "Cumulative sanctioned houses"},
            {"dimension": "yearly_trend", "category_name": "FY 2022-23", "metric_value": 22500000, "percentage": None, "notes": "Cumulative sanctioned houses"},
            {"dimension": "yearly_trend", "category_name": "FY 2023-24", "metric_value": 26200000, "percentage": None, "notes": "Cumulative sanctioned houses"},
        ],
    },

    # 4. Post-Matric Scholarship (Unpublished / Pending Joint Ministerial Verification)
    {
        "scheme_id": POST_MATRIC_ID,
        "source_name": "Ministry of Social Justice and Empowerment / Ministry of Tribal Affairs, GoI",
        "report_title": "National Scholarship Portal Consolidated Data (Consolidated Ministry Audit Pending)",
        "source_url": "https://scholarships.gov.in/",
        "source_publication_date": datetime(2024, 3, 31, tzinfo=timezone.utc),
        "reporting_period": "FY 2023-24 Academic Year",
        "geographic_scope": "National",
        "metric_type": "students_awarded_scholarship",
        "metric_definition": "Scholarships awarded under disparate ministry schemes (unverified aggregate across MSJE, MoTA, PM-YASASVI)",
        "total_beneficiaries": 6500000,
        "dataset_version": 1,
        "verification_status": "Pending Verification",
        "is_published": False,
        "published_at": None,
        "last_verified_at": None,
        "notes": "Dataset pending verification: Separate ministry reporting streams (Ministry of Social Justice & Empowerment for SC/OBC, and Ministry of Tribal Affairs for ST) cannot be combined into a single unified total without official inter-ministerial consolidated audit.",
        "breakdowns": [
            # Gender
            {"dimension": "gender", "category_name": "Female", "metric_value": 3380000, "percentage": 52.0, "notes": "Female scholar beneficiaries"},
            {"dimension": "gender", "category_name": "Male", "metric_value": 3120000, "percentage": 48.0, "notes": "Male scholar beneficiaries"},
            # State Distribution
            {"dimension": "state", "category_name": "Maharashtra", "metric_value": 910000, "percentage": 14.0, "notes": "Administered via MahaDBT portal"},
            {"dimension": "state", "category_name": "Uttar Pradesh", "metric_value": 1170000, "percentage": 18.0, "notes": "Administered via UP Scholarship portal"},
            {"dimension": "state", "category_name": "Tamil Nadu", "metric_value": 650000, "percentage": 10.0, "notes": "Southern zone"},
            {"dimension": "state", "category_name": "Gujarat", "metric_value": 455000, "percentage": 7.0, "notes": "Digital Gujarat portal"},
            {"dimension": "state", "category_name": "Other States/UTs", "metric_value": 3315000, "percentage": 51.0, "notes": "Remaining states and UTs"},
            # Yearly Trend
            {"dimension": "yearly_trend", "category_name": "FY 2021-22", "metric_value": 5800000, "percentage": None, "notes": "Annual scholars"},
            {"dimension": "yearly_trend", "category_name": "FY 2022-23", "metric_value": 6150000, "percentage": None, "notes": "Annual scholars"},
            {"dimension": "yearly_trend", "category_name": "FY 2023-24", "metric_value": 6500000, "percentage": None, "notes": "Annual scholars"},
        ],
    },

    # 5. MJPJAY (Maharashtra - Unpublished / Pending SHAS Empirical Verification)
    {
        "scheme_id": MJPJAY_ID,
        "source_name": "State Health Assurance Society (SHAS), Public Health Department, Govt of Maharashtra",
        "report_title": "State Health Assurance Society Annual Report (Verification In Progress)",
        "source_url": "https://www.jeevandayee.gov.in/",
        "source_publication_date": datetime(2024, 3, 31, tzinfo=timezone.utc),
        "reporting_period": "FY 2023-24",
        "geographic_scope": "State: Maharashtra",
        "metric_type": "covered_families",
        "metric_definition": "Eligible ration card holding families covered under expanded state healthcare scheme",
        "total_beneficiaries": 22500000,
        "dataset_version": 1,
        "verification_status": "Pending Verification",
        "is_published": False,
        "published_at": None,
        "last_verified_at": None,
        "notes": "MJPJAY state health dataset pending official SHAS empirical audit for district-level covered families and procedure-level disaggregation.",
        "breakdowns": [
            # Gender Proportion
            {"dimension": "gender", "category_name": "Female", "metric_value": 11025000, "percentage": 49.0, "notes": "Female family members covered"},
            {"dimension": "gender", "category_name": "Male", "metric_value": 11475000, "percentage": 51.0, "notes": "Male family members covered"},
            # Yearly Trend
            {"dimension": "yearly_trend", "category_name": "FY 2021-22", "metric_value": 22200000, "percentage": None, "notes": "Covered families"},
            {"dimension": "yearly_trend", "category_name": "FY 2022-23", "metric_value": 22400000, "percentage": None, "notes": "Covered families"},
            {"dimension": "yearly_trend", "category_name": "FY 2023-24", "metric_value": 22500000, "percentage": None, "notes": "Covered families under expanded ₹5 Lakh ceiling"},
        ],
    },
]


# ============================================================================
# SEED RUNNER FUNCTION
# ============================================================================
def seed_scheme_intelligence_data(db: Session) -> Dict[str, int]:
    """Populate category rules, category documents, document guides, and analytics datasets."""
    stats = {
        "category_rules": 0,
        "category_documents": 0,
        "document_guides": 0,
        "analytics_datasets": 0,
        "analytics_breakdowns": 0,
    }

    # 1. Seed Category Rules
    for rule_data in CATEGORY_RULES_SEED:
        rule_dict = dict(rule_data)
        rule_dict.setdefault("geographic_scope", "State: Maharashtra" if rule_dict.get("scheme_id") == MJPJAY_ID else "National")
        rule_dict.setdefault("verification_status", "Review Required" if "Review Required" in rule_dict.get("condition_name", "") else "Verified")

        existing = db.query(SchemeCategoryRule).filter(
            SchemeCategoryRule.scheme_id == rule_dict["scheme_id"],
            SchemeCategoryRule.category == rule_dict["category"],
            SchemeCategoryRule.condition_name == rule_dict["condition_name"],
        ).first()

        if not existing:
            rule = SchemeCategoryRule(**rule_dict)
            db.add(rule)
            stats["category_rules"] += 1
        else:
            for k, v in rule_dict.items():
                setattr(existing, k, v)
    db.commit()

    # 2. Seed Category Documents
    for doc_data in CATEGORY_DOCUMENTS_SEED:
        existing = db.query(SchemeCategoryDocument).filter(
            SchemeCategoryDocument.scheme_id == doc_data["scheme_id"],
            SchemeCategoryDocument.category == doc_data["category"],
            SchemeCategoryDocument.document_type == doc_data["document_type"],
        ).first()
        if not existing:
            doc = SchemeCategoryDocument(**doc_data)
            db.add(doc)
            stats["category_documents"] += 1
        else:
            for k, v in doc_data.items():
                setattr(existing, k, v)
    db.commit()

    # 3. Seed Document Guides
    for guide_data in DOCUMENT_GUIDES_SEED:
        existing = db.query(DocumentGuide).filter(
            DocumentGuide.document_type == guide_data["document_type"]
        ).first()
        if not existing:
            guide = DocumentGuide(**guide_data)
            db.add(guide)
            stats["document_guides"] += 1
        else:
            for k, v in guide_data.items():
                setattr(existing, k, v)
    db.commit()

    # 4. Seed Analytics Datasets & Breakdowns
    for ds_data in ANALYTICS_DATASETS_SEED:
        breakdowns_data = ds_data.get("breakdowns", [])
        ds_fields = {k: v for k, v in ds_data.items() if k != "breakdowns"}
        existing_ds = db.query(SchemeAnalyticsDataset).filter(
            SchemeAnalyticsDataset.scheme_id == ds_fields["scheme_id"],
            SchemeAnalyticsDataset.reporting_period == ds_fields["reporting_period"],
        ).first()

        if not existing_ds:
            dataset = SchemeAnalyticsDataset(**ds_fields)
            db.add(dataset)
            db.flush()
            stats["analytics_datasets"] += 1
        else:
            for k, v in ds_fields.items():
                setattr(existing_ds, k, v)
            dataset = existing_ds
            # Remove any unverified legacy caste_category breakdowns
            db.query(SchemeAnalyticsBreakdown).filter(
                SchemeAnalyticsBreakdown.dataset_id == dataset.id,
                SchemeAnalyticsBreakdown.dimension == "caste_category"
            ).delete()

        # Synchronize breakdowns
        existing_breakdowns = {
            (b.dimension, b.category_name): b
            for b in db.query(SchemeAnalyticsBreakdown).filter(SchemeAnalyticsBreakdown.dataset_id == dataset.id).all()
        }

        for b_data in breakdowns_data:
            key = (b_data["dimension"], b_data["category_name"])
            if key not in existing_breakdowns:
                breakdown = SchemeAnalyticsBreakdown(
                    dataset_id=dataset.id,
                    **b_data
                )
                db.add(breakdown)
                stats["analytics_breakdowns"] += 1
            else:
                for k, v in b_data.items():
                    setattr(existing_breakdowns[key], k, v)

        # Create / record Audit Log
        audit = SchemeAnalyticsAuditLog(
            dataset_id=dataset.id,
            scheme_id=dataset.scheme_id,
            admin_id=None,
            action="published" if dataset.is_published else "pending_verification",
            details={
                "event": "official_audit_remediation_sync",
                "total_beneficiaries": dataset.total_beneficiaries,
                "verification_status": dataset.verification_status,
                "is_published": dataset.is_published,
                "report_title": dataset.report_title,
                "geographic_scope": dataset.geographic_scope,
            }
        )
        db.add(audit)

    db.commit()
    return stats


if __name__ == "__main__":
    import os
    import sys
    from app.core.database import SessionLocal

    print("Executing Scheme Intelligence & Official Analytics Seeder...")
    session = SessionLocal()
    try:
        results = seed_scheme_intelligence_data(session)
        print("Seeding completed successfully!")
        for k, v in results.items():
            print(f" - {k}: {v} inserted")
    except Exception as e:
        session.rollback()
        print(f"Error during seeding: {e}")
        raise
    finally:
        session.close()
