import re
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.scheme import Scheme
from app.models.profile import UserProfile
from app.models.document import DocumentMetadata, DocumentProcessingStatus
from app.core.logging import get_logger

logger = get_logger("janmitra.readiness_service")


class ReadinessService:
    """Computes transparent, multi-dimensional application readiness metrics and performs
    cross-validation between citizen profile data and OCR-extracted document records.
    """

    @classmethod
    def evaluate_readiness(
        cls,
        db: Session,
        user_id: UUID,
        scheme: Scheme,
        criteria_match_percentage: float,
        missing_fields: List[str],
    ) -> Dict[str, Any]:
        """Evaluate overall application readiness across criteria match, document coverage,
        information completeness, and document-profile consistency.
        """
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        documents = db.query(DocumentMetadata).filter(DocumentMetadata.user_id == user_id).all()

        # 1. Document Coverage
        scheme_required_docs = scheme.required_documents or []
        uploaded_doc_types = [doc.document_type.strip().lower() for doc in documents]

        matched_doc_types: List[str] = []
        missing_doc_types: List[str] = []

        for req in scheme_required_docs:
            req_clean = req.strip()
            # Check if any uploaded document matches required type
            found = any(
                req_clean.lower() in u or u in req_clean.lower()
                for u in uploaded_doc_types
            )
            if found:
                matched_doc_types.append(req_clean)
            else:
                missing_doc_types.append(req_clean)

        total_req = len(scheme_required_docs)
        if total_req > 0:
            doc_coverage_pct = round((len(matched_doc_types) / total_req) * 100.0, 1)
        else:
            doc_coverage_pct = 100.0

        # 2. Information Completeness
        req_profile_fields = scheme.required_profile_fields or [
            "full_name", "date_of_birth", "state", "district", "residence_type", "annual_family_income"
        ]
        total_fields = len(req_profile_fields)
        missing_count = len(missing_fields)
        present_count = max(0, total_fields - missing_count)
        completeness_pct = round((present_count / total_fields) * 100.0, 1) if total_fields > 0 else 100.0

        # 3. Document Consistency Cross-Validation
        consistency_status = "Consistent"
        discrepancies: List[str] = []
        low_confidence_docs: List[str] = []

        # Check OCR confidence of documents
        for doc in documents:
            if doc.ocr_confidence is not None and doc.ocr_confidence < 0.70:
                low_confidence_docs.append(f"{doc.document_type} ({doc.original_filename})")
            elif doc.manual_review_required:
                low_confidence_docs.append(f"{doc.document_type} ({doc.original_filename})")

        # Name and DOB Cross-Validation if profile exists
        if profile:
            profile_name = profile.full_name.strip().lower() if profile.full_name else ""
            profile_dob_str = profile.date_of_birth.strftime("%Y-%m-%d") if profile.date_of_birth else ""
            profile_year = profile.date_of_birth.strftime("%Y") if profile.date_of_birth else ""

            name_tokens = [t for t in re.split(r"\s+", profile_name) if len(t) > 2]

            for doc in documents:
                ocr_text = (doc.ocr_extracted_text or "").lower()
                if not ocr_text:
                    continue

                # Check Name match if document is an identity document
                is_id_doc = any(k in doc.document_type.lower() for k in ["aadhaar", "ration", "caste", "domicile", "income", "pan"])
                if is_id_doc and name_tokens:
                    # Token overlap check
                    found_tokens = [t for t in name_tokens if t in ocr_text]
                    if len(found_tokens) == 0 and len(name_tokens) > 0:
                        discrepancies.append(
                            f"Name mismatch in {doc.document_type}: Citizen profile name '{profile.full_name}' was not detected in extracted text."
                        )

                # Check DOB / Year match
                if profile_year and is_id_doc:
                    # Check if birth year or formatted date appears
                    year_match = profile_year in ocr_text
                    if not year_match and ("dob" in ocr_text or "birth" in ocr_text or "year" in ocr_text):
                        discrepancies.append(
                            f"Birth year mismatch in {doc.document_type}: Birth year '{profile_year}' does not appear in extracted document text."
                        )

        # Determine consistency score and final status
        if discrepancies:
            consistency_status = "Discrepancy Detected"
            consistency_score = 50.0
        elif low_confidence_docs:
            consistency_status = "Review Required"
            consistency_score = 75.0
        else:
            consistency_status = "Consistent"
            consistency_score = 100.0

        # 4. Overall Weighted Application Readiness Score
        # Weighting: 40% criteria match, 30% document coverage, 15% completeness, 15% consistency
        overall_score = (
            0.40 * criteria_match_percentage
            + 0.30 * doc_coverage_pct
            + 0.15 * completeness_pct
            + 0.15 * consistency_score
        )
        overall_score = round(min(100.0, max(0.0, overall_score)), 1)

        return {
            "overall_readiness_score": overall_score,
            "criteria_match_percentage": criteria_match_percentage,
            "document_coverage_percentage": doc_coverage_pct,
            "information_completeness_percentage": completeness_pct,
            "consistency_score": consistency_score,
            "consistency_status": consistency_status,
            "discrepancies": discrepancies,
            "low_confidence_documents": low_confidence_docs,
            "uploaded_document_types": matched_doc_types,
            "missing_document_types": missing_doc_types,
            "score_interpretation": (
                f"Application Readiness Score ({overall_score:.1f}%) is a composite advisory index "
                f"reflecting criteria match ({criteria_match_percentage:.1f}%), document type coverage ({doc_coverage_pct:.1f}%), "
                f"information completeness ({completeness_pct:.1f}%), and document consistency ({consistency_score:.1f}%). "
                f"It is NOT an official government approval probability or guarantee."
            ),
        }
