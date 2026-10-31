import re
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.scheme import Scheme
from app.models.profile import UserProfile
from app.models.document import DocumentMetadata, DocumentProcessingStatus
from app.core.logging import get_logger

logger = get_logger("janmitra.readiness_service")


def _match_doc_types(req_name: str, doc_type: str) -> bool:
    """Robust normalized matching for Indian civic document types."""
    r = re.sub(r"[_\s]+", " ", req_name.strip().lower())
    d = re.sub(r"[_\s]+", " ", doc_type.strip().lower())
    if r in d or d in r:
        return True
    for root in ["aadhaar", "ration", "caste", "domicile", "residence", "income", "land", "passbook", "bank"]:
        if root in r and root in d:
            return True
    return False


class ReadinessService:
    """Computes transparent, multi-dimensional application readiness metrics and performs
    cross-validation between citizen profile data and OCR-extracted document records.
    
    Weights Rationale:
    - 40% Criteria Match: Primary legal determinant of scheme eligibility.
    - 30% Document Coverage: Mandatory prerequisite for government service application submission.
    - 15% Information Completeness: Extent to which required profile fields are fully provided.
    - 15% Document Consistency: Integrity check ensuring vault certificates align with claimed profile records.
    """

    # Transparent mathematical weight distribution
    WEIGHT_CRITERIA_MATCH: float = 0.40
    WEIGHT_DOC_COVERAGE: float = 0.30
    WEIGHT_COMPLETENESS: float = 0.15
    WEIGHT_CONSISTENCY: float = 0.15

    # Capping thresholds to prevent false sense of readiness
    CAP_NOT_ELIGIBLE: float = 35.0
    CAP_INSUFFICIENT_INFO: float = 50.0

    @classmethod
    def evaluate_readiness(
        cls,
        db: Session,
        user_id: UUID,
        scheme: Scheme,
        criteria_match_percentage: float,
        missing_fields: List[str],
        overall_status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Evaluate overall application readiness across criteria match, document coverage,
        information completeness, and document-profile consistency.
        
        Guarantees:
        - OCR_FAILED documents receive 0% usable coverage credit.
        - MANUAL_REVIEW_REQUIRED / low-confidence documents receive partial (50%) coverage credit.
        - 0 uploaded documents yields 'Not Evaluated (No Documents)' and 0.0 consistency score.
        - Ineligible assessments are capped at <= 35.0% readiness.
        - Insufficient information assessments are capped at <= 50.0% readiness.
        """
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        documents = db.query(DocumentMetadata).filter(DocumentMetadata.user_id == user_id).all()

        # 1. Document Coverage Evaluation with usability validation
        scheme_required_docs = scheme.required_documents or []
        total_req = len(scheme_required_docs)

        matched_doc_types: List[str] = []
        partial_doc_types: List[str] = []
        failed_doc_types: List[str] = []
        missing_doc_types: List[str] = []

        total_coverage_credit = 0.0

        for req in scheme_required_docs:
            req_clean = req.strip()
            # Find all uploaded documents matching required type using normalized matcher
            matching_docs = [
                doc for doc in documents
                if _match_doc_types(req_clean, doc.document_type)
            ]

            if not matching_docs:
                missing_doc_types.append(req_clean)
                continue

            # Determine usability credit among matching docs
            # Priority: Fully Usable (1.0) > Review Required (0.5) > Failed (0.0)
            has_fully_usable = False
            has_review_required = False
            has_failed_only = True

            for d in matching_docs:
                is_failed = (d.ocr_status == DocumentProcessingStatus.OCR_FAILED)
                is_manual_review = (
                    d.manual_review_required or
                    (d.ocr_confidence is not None and d.ocr_confidence < 0.70)
                )

                if is_failed:
                    continue
                has_failed_only = False

                if is_manual_review:
                    has_review_required = True
                elif d.ocr_status == DocumentProcessingStatus.OCR_COMPLETED:
                    has_fully_usable = True
                    break

            if has_fully_usable:
                total_coverage_credit += 1.0
                matched_doc_types.append(req_clean)
            elif has_review_required:
                total_coverage_credit += 0.5
                partial_doc_types.append(f"{req_clean} (Manual Review Required)")
            elif has_failed_only:
                failed_doc_types.append(f"{req_clean} (OCR Processing Failed)")
            else:
                missing_doc_types.append(req_clean)

        if total_req > 0:
            doc_coverage_pct = round((total_coverage_credit / total_req) * 100.0, 1)
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
        discrepancies: List[str] = []
        low_confidence_docs: List[str] = []

        if len(documents) == 0:
            # When zero documents exist, consistency cannot be asserted as 100%
            consistency_status = "Not Evaluated (No Documents)"
            consistency_score = 0.0
        else:
            # Check OCR confidence of documents
            for doc in documents:
                if doc.ocr_status == DocumentProcessingStatus.OCR_FAILED:
                    low_confidence_docs.append(f"{doc.document_type} (OCR Failed: {doc.original_filename})")
                elif doc.ocr_confidence is not None and doc.ocr_confidence < 0.70:
                    low_confidence_docs.append(f"{doc.document_type} (Low Confidence: {doc.ocr_confidence:.2f})")
                elif doc.manual_review_required:
                    low_confidence_docs.append(f"{doc.document_type} (Flagged for Review: {doc.original_filename})")

            # Name and DOB Cross-Validation if profile exists
            if profile:
                profile_name = profile.full_name.strip().lower() if profile.full_name else ""
                profile_year = profile.date_of_birth.strftime("%Y") if profile.date_of_birth else ""
                name_tokens = [t for t in re.split(r"\s+", profile_name) if len(t) > 2]

                for doc in documents:
                    ocr_text = (doc.ocr_extracted_text or "").lower()
                    if not ocr_text:
                        continue

                    # Check Name match if document is an identity document
                    is_id_doc = any(k in doc.document_type.lower() for k in ["aadhaar", "ration", "caste", "domicile", "income", "pan"])
                    if is_id_doc and name_tokens:
                        found_tokens = [t for t in name_tokens if t in ocr_text]
                        if len(found_tokens) == 0 and len(name_tokens) > 0:
                            discrepancies.append(
                                f"Identity Name Mismatch in {doc.document_type}: Stated profile name tokens were not detected in OCR record."
                            )

                    # Check DOB / Year match
                    if profile_year and is_id_doc:
                        year_match = profile_year in ocr_text
                        if not year_match and ("dob" in ocr_text or "birth" in ocr_text or "year" in ocr_text):
                            discrepancies.append(
                                f"Birth Year Mismatch in {doc.document_type}: Profile birth year '{profile_year}' was not detected in document OCR record."
                            )

            # Proportional Consistency Deduction Model
            # Base: 100.0, -20.0 per discrepancy, -10.0 per low confidence / review item
            base_consistency = 100.0
            discrepancy_deduction = len(discrepancies) * 20.0
            review_deduction = len(low_confidence_docs) * 10.0
            total_deduction = discrepancy_deduction + review_deduction

            consistency_score = round(max(0.0, base_consistency - total_deduction), 1)

            if discrepancies:
                consistency_status = "Discrepancy Detected"
            elif low_confidence_docs:
                consistency_status = "Review Required"
            else:
                consistency_status = "Consistent"

        # 4. Overall Weighted Application Readiness Score
        # Weighting: 40% criteria match, 30% document coverage, 15% completeness, 15% consistency
        raw_overall_score = (
            cls.WEIGHT_CRITERIA_MATCH * criteria_match_percentage
            + cls.WEIGHT_DOC_COVERAGE * doc_coverage_pct
            + cls.WEIGHT_COMPLETENESS * completeness_pct
            + cls.WEIGHT_CONSISTENCY * consistency_score
        )
        raw_overall_score = round(min(100.0, max(0.0, raw_overall_score)), 1)

        # 5. Apply Status-Based Capping Rules to prevent misleading high scores
        capped_overall_score = raw_overall_score
        capping_note = ""

        status_lower = (overall_status or "").lower()
        if "not eligible" in status_lower:
            # If user is ineligible based on available rules, readiness must not exceed 35%
            max_allowed = min(cls.CAP_NOT_ELIGIBLE, criteria_match_percentage)
            if raw_overall_score > max_allowed:
                capped_overall_score = round(max_allowed, 1)
                capping_note = (
                    f" (Capped from {raw_overall_score:.1f}% to {capped_overall_score:.1f}% because citizen is "
                    f"evaluated as '{overall_status}'; submission readiness cannot be high when core criteria fail)."
                )
        elif "insufficient" in status_lower:
            # If information is insufficient, readiness cannot exceed 50%
            if raw_overall_score > cls.CAP_INSUFFICIENT_INFO:
                capped_overall_score = round(cls.CAP_INSUFFICIENT_INFO, 1)
                capping_note = (
                    f" (Capped from {raw_overall_score:.1f}% to {capped_overall_score:.1f}% because citizen has "
                    f"'{overall_status}'; key criteria remain unverified)."
                )

        all_uploaded_reported = matched_doc_types + partial_doc_types
        all_missing_reported = missing_doc_types + failed_doc_types

        score_interpretation = (
            f"Application Readiness Score ({capped_overall_score:.1f}%) is a composite advisory index "
            f"reflecting criteria match ({criteria_match_percentage:.1f}%, weight 40%), "
            f"document type coverage ({doc_coverage_pct:.1f}%, weight 30%), "
            f"information completeness ({completeness_pct:.1f}%, weight 15%), and "
            f"document consistency ({consistency_score:.1f}%, weight 15%).{capping_note} "
            f"It is NOT an official government approval probability or guarantee."
        )

        return {
            "overall_readiness_score": capped_overall_score,
            "raw_readiness_score": raw_overall_score,
            "criteria_match_percentage": criteria_match_percentage,
            "document_coverage_percentage": doc_coverage_pct,
            "information_completeness_percentage": completeness_pct,
            "consistency_score": consistency_score,
            "consistency_status": consistency_status,
            "discrepancies": discrepancies,
            "low_confidence_documents": low_confidence_docs,
            "uploaded_document_types": all_uploaded_reported,
            "missing_document_types": all_missing_reported,
            "score_interpretation": score_interpretation,
        }
