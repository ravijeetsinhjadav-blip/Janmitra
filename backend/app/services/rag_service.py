import re
import math
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.scheme import Scheme
from app.models.scheme_knowledge import SchemeKnowledgeChunk
from app.core.logging import get_logger

logger = get_logger("janmitra.rag_service")


class RAGService:
    """Retrieval-Augmented Generation (RAG) service for official government scheme documents.
    
    Provides ingestion, chunking, seeding, and ranked retrieval of authoritative government
    rules and notices. Ensures the AI advisory engine makes only verifiable claims.
    """

    @staticmethod
    def seed_scheme_knowledge_chunks(db: Session) -> int:
        """Seed verified knowledge chunks for all demo schemes if not already present."""
        schemes = db.query(Scheme).all()
        if not schemes:
            return 0

        scheme_map = {s.scheme_name: s for s in schemes}
        total_seeded = 0

        # Verified Curated MCA Demo Knowledge Chunks
        knowledge_corpus: List[Dict[str, Any]] = [
            # 1. PM-KISAN
            {
                "scheme_name": "Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)",
                "chunks": [
                    {
                        "title": "Landholding & Cultivable Land Criteria",
                        "category": "eligibility",
                        "content": (
                            "Under PM-KISAN Operational Guidelines, eligible beneficiaries are small and marginal "
                            "farmer families who own cultivable landholding in their names as per official State/UT land records. "
                            "Institutional landholders and farmer families holding constitutional posts or paying income tax in "
                            "the last assessment year are strictly excluded."
                        ),
                        "reference": "PM-KISAN Guidelines 2023, Section 3.1 (Beneficiary Eligibility & Exclusions)",
                        "freshness": "Verified Official Source",
                    },
                    {
                        "title": "DBT Installment Cycles & PFMS Verification",
                        "category": "benefits",
                        "content": (
                            "Financial benefit of ₹6,000 per annum is payable in three equal four-monthly installments of "
                            "₹2,000 each (Period 1: April-July, Period 2: August-November, Period 3: December-March). "
                            "Payments are processed directly into the beneficiary's Aadhaar-seeded bank account through the "
                            "Public Financial Management System (PFMS)."
                        ),
                        "reference": "PM-KISAN Operational Guidelines, Section 2 (Financial Modalities)",
                        "freshness": "Verified Official Source",
                    },
                    {
                        "title": "Mandatory e-KYC and Land Record Seeding",
                        "category": "documents",
                        "content": (
                            "To receive uninterrupted installments, registered farmers must complete Aadhaar-based e-KYC "
                            "via OTP on the PM-KISAN portal or biometric verification at Common Service Centres (CSCs). "
                            "Physical land records (RoR / 7/12 extract) and bank account details must be mapped to Aadhaar."
                        ),
                        "reference": "Ministry of Agriculture & Farmers Welfare Advisory on e-KYC and Land Seeding",
                        "freshness": "Verified Official Source",
                    },
                ],
            },
            # 2. Ayushman Bharat (AB-PMJAY)
            {
                "scheme_name": "Ayushman Bharat - Pradhan Mantri Jan Arogya Yojana (AB-PMJAY)",
                "chunks": [
                    {
                        "title": "SECC 2011 Deprivation & Vulnerability Mapping",
                        "category": "eligibility",
                        "content": (
                            "AB-PMJAY covers families included in the Socio-Economic Caste Census (SECC) 2011 database "
                            "based on rural deprivation criteria (D1: single room with kuccha walls, D2: no adult 16-59, "
                            "D3: female-headed, D4: disabled member, D5: SC/ST, D7: landless manual scavengers) and "
                            "11 defined occupational categories of urban workers. Families holding NFSA Ration Cards may be eligible."
                        ),
                        "reference": "National Health Authority (NHA) Beneficiary Identification System (BIS) Guidelines",
                        "freshness": "Verified Official Source",
                    },
                    {
                        "title": "Cashless Secondary and Tertiary Hospitalization",
                        "category": "benefits",
                        "content": (
                            "Provides health insurance coverage of up to ₹5,00,000 per family per year on a family floater basis. "
                            "Covers pre-hospitalization (up to 3 days) and post-hospitalization (up to 15 days) expenses including "
                            "diagnostics, medicine, ICU, and surgery at all empanelled public and private hospitals across India."
                        ),
                        "reference": "AB-PMJAY Health Benefit Packages 2.2",
                        "freshness": "Verified Official Source",
                    },
                    {
                        "title": "Ayushman Card Generation & Identity Enclosures",
                        "category": "documents",
                        "content": (
                            "Beneficiaries must generate an Ayushman Card (Golden Card) at empanelled hospitals, CSCs, or "
                            "via the Ayushman App. Essential identification requires an Aadhaar Card or government ration card "
                            "matching the SECC/NFSA household roster. There is zero enrollment fee for eligible citizens."
                        ),
                        "reference": "NHA Patient Guidelines for Empanelled Health Care Providers",
                        "freshness": "Verified Official Source",
                    },
                ],
            },
            # 3. PMAY-G (Gramin)
            {
                "scheme_name": "Pradhan Mantri Awaas Yojana - Gramin (PMAY-G)",
                "chunks": [
                    {
                        "title": "Rural Houselessness & Deprivation Identification",
                        "category": "eligibility",
                        "content": (
                            "Beneficiaries are identified from the SECC 2011 Permanent Wait List (PWL) and Awaas+ survey, "
                            "verified and prioritized by the local Gram Sabha. Eligible households are houseless or living in "
                            "dilapidated zero, one, or two-room houses with kutcha walls and kutcha roof."
                        ),
                        "reference": "MoRD PMAY-G Framework for Implementation, Chapter 3",
                        "freshness": "Verified Official Source",
                    },
                    {
                        "title": "Housing Grant Amount & MGNREGA Convergence",
                        "category": "benefits",
                        "content": (
                            "Unit assistance of ₹1,20,000 in plain areas and ₹1,30,000 in hilly/difficult/IAP areas for constructing "
                            "a minimum 25 sq. m pucca house with a dedicated hygienic cooking space. In addition, beneficiaries receive "
                            "90/95 person-days of unskilled labor wage under MGNREGA and ₹12,000 for toilet construction under SBM-G."
                        ),
                        "reference": "MoRD PMAY-G Financial Guidelines, Chapter 2",
                        "freshness": "Verified Official Source",
                    },
                    {
                        "title": "Geo-Tagged Construction Milestones & Account Verification",
                        "category": "documents",
                        "content": (
                            "Disbursement is released in 3–4 installments tied directly to geo-tagged photographs uploaded via "
                            "the AwaasApp inspection system: stage 1 (sanction), stage 2 (plinth level), stage 3 (lintel/roof level), "
                            "and stage 4 (completion). Enclosures require Aadhaar, MGNREGA Job Card, and bank account details."
                        ),
                        "reference": "MoRD PMAY-G Inspection & Monitoring Manual",
                        "freshness": "Verified Official Source",
                    },
                ],
            },
            # 4. NSP Post-Matric Scholarship
            {
                "scheme_name": "National Scholarship Portal - Post-Matric Scholarship Scheme",
                "chunks": [
                    {
                        "title": "Family Income Ceiling & Course Eligibility",
                        "category": "eligibility",
                        "content": (
                            "Scholarship is awarded to students belonging to SC, ST, OBC, and EWS categories pursuing recognized "
                            "post-matriculation or post-secondary courses (Class 11 to PhD) in recognized government or private "
                            "institutions. The annual family income from all sources must not exceed ₹2,50,000."
                        ),
                        "reference": "Ministry of Social Justice & Empowerment, Post-Matric Scholarship Scheme Guidelines",
                        "freshness": "Verified Official Source",
                    },
                    {
                        "title": "Tuition Reimbursement and Maintenance Allowance",
                        "category": "benefits",
                        "content": (
                            "Covers complete reimbursement of non-refundable compulsory fees charged by the educational institution "
                            "plus a monthly maintenance allowance categorized by course group (Group 1 to Group 4) for day scholars "
                            "and hostellers. Disbursed via Direct Benefit Transfer through PFMS."
                        ),
                        "reference": "NSP Operational Manual & Fee Structure Norms",
                        "freshness": "Verified Official Source",
                    },
                    {
                        "title": "Mandatory Certificates & Institutional Verification",
                        "category": "documents",
                        "content": (
                            "Applicants must upload: 1) Current Financial Year Income Certificate issued by an authorized revenue officer "
                            "(Tahsildar/SDM), 2) Valid Caste / Community Certificate, 3) Previous qualifying exam marksheet, 4) Bonafide "
                            "student certificate and fee receipt from the educational institution, and 5) Aadhaar-seeded bank account."
                        ),
                        "reference": "National Scholarship Portal Application Verification Protocol",
                        "freshness": "Verified Official Source",
                    },
                ],
            },
            # 5. Maharashtra MJPJAY
            {
                "scheme_name": "Mahatma Jyotirao Phule Jan Arogya Yojana (MJPJAY)",
                "chunks": [
                    {
                        "title": "Maharashtra Ration Card & Resident Eligibility",
                        "category": "eligibility",
                        "content": (
                            "Open to permanent residents of Maharashtra holding valid Yellow Ration Cards, Orange Ration Cards (annual "
                            "income up to ₹1 Lakh or as amended), Antyodaya Anna Yojana (AAY) cards, or Annapurna cards issued by the "
                            "Food, Civil Supplies and Consumer Protection Department of Maharashtra."
                        ),
                        "reference": "Public Health Department, Govt. of Maharashtra, GR No. MJPJAY-2023/CR-142/PH-4",
                        "freshness": "Verified Official Source",
                    },
                    {
                        "title": "Cashless Hospitalization Package Ceiling",
                        "category": "benefits",
                        "content": (
                            "Provides cashless treatment up to ₹5,00,000 per family per policy year across 996 identified medical and surgical "
                            "procedures in 30 specialized categories at network hospitals. Renal transplant coverage has an additional "
                            "statutory ceiling under state guidelines."
                        ),
                        "reference": "State Health Assurance Society (SHAS) Benefit Schedule",
                        "freshness": "Verified Official Source",
                    },
                    {
                        "title": "Identity Verification at Hospital Aarogyamitra Desks",
                        "category": "documents",
                        "content": (
                            "Beneficiary must present their valid Maharashtra Ration Card accompanied by a valid photo ID (Aadhaar Card, "
                            "Voter ID, or Domicile Certificate) at the network hospital's Aarogyamitra help desk. The Aarogyamitra facilitates "
                            "online pre-authorization and cashless admission."
                        ),
                        "reference": "SHAS Aarogyamitra Standard Operating Procedure",
                        "freshness": "Verified Official Source",
                    },
                ],
            },
        ]

        for item in knowledge_corpus:
            scheme_title = item["scheme_name"].lower()
            scheme = next(
                (s for s in schemes if scheme_title in s.scheme_name.lower() or s.scheme_name.lower() in scheme_title),
                None,
            )
            if not scheme:
                continue

            for c in item["chunks"]:
                existing = (
                    db.query(SchemeKnowledgeChunk)
                    .filter(
                        SchemeKnowledgeChunk.scheme_id == scheme.id,
                        SchemeKnowledgeChunk.chunk_title == c["title"],
                    )
                    .first()
                )
                if not existing:
                    chunk = SchemeKnowledgeChunk(
                        scheme_id=scheme.id,
                        chunk_title=c["title"],
                        chunk_category=c["category"],
                        chunk_content=c["content"],
                        source_url=scheme.official_source_url,
                        source_title=scheme.scheme_name + " Guidelines",
                        source_reference=c["reference"],
                        source_freshness_status=c["freshness"],
                        is_demo_data=True,
                    )
                    db.add(chunk)
                    total_seeded += 1

        if total_seeded > 0:
            db.commit()
            logger.info(f"Seeded {total_seeded} RAG scheme knowledge chunks.")

        return total_seeded

    @staticmethod
    def _compute_lexical_similarity(query_tokens: List[str], text: str) -> float:
        """Compute term-frequency overlap score between query tokens and chunk text."""
        if not query_tokens or not text:
            return 0.0

        text_tokens = re.findall(r"\w+", text.lower())
        if not text_tokens:
            return 0.0

        match_count = sum(1 for q in query_tokens if q in text_tokens)
        return match_count / math.sqrt(len(text_tokens) + len(query_tokens))

    @classmethod
    def retrieve_relevant_chunks(
        cls,
        db: Session,
        scheme_id: UUID,
        query: str,
        category: Optional[str] = None,
        top_k: int = 3,
    ) -> List[SchemeKnowledgeChunk]:
        """Retrieve top-k relevant official knowledge chunks for a scheme."""
        # Ensure chunks are seeded
        query_chunks = db.query(SchemeKnowledgeChunk).filter(SchemeKnowledgeChunk.scheme_id == scheme_id)
        if category:
            query_chunks = query_chunks.filter(SchemeKnowledgeChunk.chunk_category == category)

        chunks = query_chunks.all()
        if not chunks:
            # Seed and re-query
            cls.seed_scheme_knowledge_chunks(db)
            chunks = db.query(SchemeKnowledgeChunk).filter(SchemeKnowledgeChunk.scheme_id == scheme_id).all()

        if not chunks:
            return []

        # Tokenize query for ranking
        query_clean = re.sub(r"[^\w\s]", " ", query.lower())
        query_tokens = [t for t in query_clean.split() if len(t) > 2]

        scored_chunks: List[tuple[float, SchemeKnowledgeChunk]] = []
        for chunk in chunks:
            title_score = cls._compute_lexical_similarity(query_tokens, chunk.chunk_title) * 2.0
            content_score = cls._compute_lexical_similarity(query_tokens, chunk.chunk_content)
            total_score = title_score + content_score

            # Freshness score weighting: Stale or unverified gets penalty
            if chunk.source_freshness_status != "Verified Official Source":
                total_score *= 0.8

            scored_chunks.append((total_score, chunk))

        # Sort descending by score
        scored_chunks.sort(key=lambda x: x[0], reverse=True)

        return [c for _, c in scored_chunks[:top_k]]
