import re
from uuid import UUID
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.scheme import Scheme
from app.models.assessment import Assessment
from app.models.profile import UserProfile
from app.models.document import DocumentMetadata, DocumentProcessingStatus
from app.services.scheme_service import SchemeService
from app.services.readiness_service import ReadinessService
from app.services.rag_service import RAGService
from app.services.llm_service import get_llm_adapter
from app.schemas.assistance import (
    DocumentPreparationStatusItem,
    ChecklistItem,
    ApplicantInfoRequirement,
    SupportingDocumentSpecification,
    PortalStepInstruction,
    ApplicationInfoGuide,
    ApplicationAssistanceResponse,
    ChecklistUpdateResponse,
)
from app.core.logging import get_logger

logger = get_logger("janmitra.assistance_service")


def _slugify(text: str) -> str:
    """Generate safe identifier from text string."""
    cleaned = re.sub(r"[^\w\s]", "", text.lower())
    return re.sub(r"\s+", "_", cleaned.strip())


def _match_doc_types(req_name: str, doc_type: str) -> bool:
    """Robust normalized matching for Indian civic document types."""
    r = re.sub(r"[_\s]+", " ", req_name.strip().lower())
    d = re.sub(r"[_\s]+", " ", doc_type.strip().lower())
    if r in d or d in r:
        return True
    # Key civic document roots
    for root in ["aadhaar", "ration", "caste", "domicile", "residence", "income", "land", "passbook", "bank"]:
        if root in r and root in d:
            return True
    return False


class AssistanceService:
    """Application Assistance module orchestrating personalized preparation guides,
    document status validation, interactive checklists, and official portal procedures.
    """

    @classmethod
    def generate_or_get_assistance(
        cls,
        db: Session,
        user_id: UUID,
        scheme_id: UUID,
        language: str = "en",
    ) -> ApplicationAssistanceResponse:
        """Construct personalized preparation checklist and scheme guide for citizen."""
        scheme = db.query(Scheme).filter(Scheme.id == scheme_id).first()
        if not scheme:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scheme not found.",
            )

        # 1. Retrieve or run deterministic eligibility assessment
        assessment = (
            db.query(Assessment)
            .filter(Assessment.scheme_id == scheme_id, Assessment.user_id == user_id)
            .order_by(Assessment.created_at.desc())
            .first()
        )

        if not assessment:
            # Run deterministic assessment if none exists yet
            assessment_res = SchemeService.run_assessment(db=db, user_id=user_id, scheme_id=scheme_id)
            assessment = db.query(Assessment).filter(Assessment.id == assessment_res.assessment_id).first()
            if not assessment:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate or retrieve assessment record.",
                )

        # 2. Re-evaluate document readiness & cross-validation metrics
        res_data = assessment.result_data or {}
        criteria_match = float(res_data.get("criteria_match_percentage", assessment.overall_readiness_score or 0.0))
        missing_fields = res_data.get("missing_fields", [])
        overall_status = res_data.get("overall_status", "Insufficient Information")

        readiness_data = ReadinessService.evaluate_readiness(
            db=db,
            user_id=user_id,
            scheme=scheme,
            criteria_match_percentage=criteria_match,
            missing_fields=missing_fields,
            overall_status=overall_status,
        )

        # 3. Analyze document preparation statuses for all required scheme documents
        documents = db.query(DocumentMetadata).filter(DocumentMetadata.user_id == user_id).all()
        scheme_required_docs = scheme.required_documents or []
        doc_statuses: List[DocumentPreparationStatusItem] = []
        discrepancies = readiness_data.get("discrepancies", [])

        for req in scheme_required_docs:
            req_clean = req.strip()
            matching_docs = [
                doc for doc in documents
                if _match_doc_types(req_clean, doc.document_type)
            ]

            if not matching_docs:
                doc_statuses.append(
                    DocumentPreparationStatusItem(
                        document_name=req_clean,
                        status="Missing",
                        notes="Document not yet uploaded to your Document Vault.",
                        matching_document_id=None,
                    )
                )
                continue

            # Prioritize best document state
            best_doc = matching_docs[0]
            has_discrepancy = any(req_clean.lower() in d.lower() for d in discrepancies)
            is_failed = all(d.ocr_status == DocumentProcessingStatus.OCR_FAILED for d in matching_docs)

            if is_failed:
                doc_statuses.append(
                    DocumentPreparationStatusItem(
                        document_name=req_clean,
                        status="Processing Failed",
                        notes="OCR processing failed for uploaded scan. Please re-upload a clearer PDF or image.",
                        matching_document_id=best_doc.id,
                    )
                )
            elif has_discrepancy:
                doc_statuses.append(
                    DocumentPreparationStatusItem(
                        document_name=req_clean,
                        status="Needs Correction",
                        notes="Discrepancy detected between stated profile record and extracted document text.",
                        matching_document_id=best_doc.id,
                    )
                )
            elif best_doc.manual_review_required or (best_doc.ocr_confidence is not None and best_doc.ocr_confidence < 0.70):
                doc_statuses.append(
                    DocumentPreparationStatusItem(
                        document_name=req_clean,
                        status="Manual Review Required",
                        notes="OCR extraction confidence is below 70% or flagged for review. Verify that details are readable.",
                        matching_document_id=best_doc.id,
                    )
                )
            elif best_doc.ocr_status == DocumentProcessingStatus.OCR_COMPLETED:
                doc_statuses.append(
                    DocumentPreparationStatusItem(
                        document_name=req_clean,
                        status="Ready for Application Preparation",
                        notes="Document available in Vault with verified OCR text.",
                        matching_document_id=best_doc.id,
                    )
                )
            else:
                doc_statuses.append(
                    DocumentPreparationStatusItem(
                        document_name=req_clean,
                        status="Available",
                        notes="Document is uploaded and stored in your Vault.",
                        matching_document_id=best_doc.id,
                    )
                )

        # 4. Retrieve stored checklist completion progress
        completed_item_ids = set(res_data.get("completed_checklist_items", []))

        # 5. Build personalized preparation checklist
        checklist_items: List[ChecklistItem] = []

        # A. Required Documents
        for ds in doc_statuses:
            item_id = f"doc_{_slugify(ds.document_name)}"
            is_ready = ds.status in ["Ready for Application Preparation", "Available"]
            checklist_items.append(
                ChecklistItem(
                    item_id=item_id,
                    category="document",
                    title=f"Keep Ready: {ds.document_name}",
                    description=f"Status: {ds.status}. {ds.notes}",
                    is_mandatory=True,
                    is_completed=(item_id in completed_item_ids) or is_ready,
                )
            )

        # B. Citizen Profile & Demographic Fields
        req_fields = scheme.required_profile_fields or ["full_name", "date_of_birth", "annual_family_income", "state", "district"]
        for f in req_fields:
            item_id = f"field_{_slugify(f)}"
            is_missing = f in missing_fields
            checklist_items.append(
                ChecklistItem(
                    item_id=item_id,
                    category="profile_field",
                    title=f"Verify Profile Field: {f.replace('_', ' ').title()}",
                    description=(
                        "Missing from your profile. Update profile before applying."
                        if is_missing
                        else "Profile field is complete. Confirm it matches your certificates."
                    ),
                    is_mandatory=True,
                    is_completed=(item_id in completed_item_ids) or (not is_missing),
                )
            )

        # C. Declarations and Portal Actions
        checklist_items.append(
            ChecklistItem(
                item_id="decl_eligibility_criteria",
                category="declaration",
                title="Verify Scheme Non-Exclusion Criteria",
                description="Confirm you do not fall into any statutory exclusion categories (e.g., income tax payer, institutional landholder).",
                is_mandatory=True,
                is_completed="decl_eligibility_criteria" in completed_item_ids,
            )
        )
        checklist_items.append(
            ChecklistItem(
                item_id="decl_dbt_bank_active",
                category="declaration",
                title="Verify Aadhaar-Seeded Bank Account",
                description="Ensure your bank account is active and mapped to NPCI/DBT for Direct Benefit Transfer.",
                is_mandatory=True,
                is_completed="decl_dbt_bank_active" in completed_item_ids,
            )
        )
        checklist_items.append(
            ChecklistItem(
                item_id="action_visit_portal",
                category="portal_action",
                title="Open Official Government Portal",
                description=f"Navigate to {scheme.official_application_url} and sign up with your Aadhaar-linked mobile number.",
                is_mandatory=True,
                is_completed="action_visit_portal" in completed_item_ids,
            )
        )
        checklist_items.append(
            ChecklistItem(
                item_id="action_save_ack_receipt",
                category="portal_action",
                title="Download Official Acknowledgment Receipt",
                description="Upon formal submission on the government portal, save and print your official application reference number.",
                is_mandatory=True,
                is_completed="action_save_ack_receipt" in completed_item_ids,
            )
        )

        # Calculate progress
        total_count = len(checklist_items)
        completed_count = sum(1 for item in checklist_items if item.is_completed)
        completion_pct = round((completed_count / total_count) * 100.0, 1) if total_count > 0 else 0.0

        # 6. Scheme Guide Resolution with caching (SEC-06)
        cache = scheme.application_guide_cache or {}
        if language in cache and isinstance(cache[language], dict):
            logger.info(f"Serving application guide for scheme {scheme_id} ({language}) from cache")
            guide_dict = cache[language]
        else:
            logger.info(f"Generating and caching application guide for scheme {scheme_id} ({language})")
            rag_chunks = RAGService.retrieve_relevant_chunks(
                db=db,
                scheme_id=scheme_id,
                query=f"{scheme.scheme_name} application procedure documents submission common mistakes",
                top_k=3,
            )
            rag_dicts = [
                {
                    "chunk_title": c.chunk_title,
                    "chunk_category": c.chunk_category,
                    "chunk_content": c.chunk_content,
                    "source_title": c.source_title,
                    "source_reference": c.source_reference,
                }
                for c in rag_chunks
            ]

            llm_adapter = get_llm_adapter()
            guide_dict = llm_adapter.generate_application_guide(
                scheme_name=scheme.scheme_name,
                category=scheme.category,
                department=scheme.department,
                required_documents=scheme.required_documents or [],
                required_profile_fields=scheme.required_profile_fields or [],
                application_process=scheme.application_process or [],
                rag_chunks=rag_dicts,
                language=language,
            )
            new_cache = dict(cache)
            new_cache[language] = guide_dict
            scheme.application_guide_cache = new_cache
            db.commit()

        guide_obj = ApplicationInfoGuide(
            applicant_info_required=[
                ApplicantInfoRequirement(**item)
                for item in guide_dict.get("applicant_info_required", [])
            ],
            supporting_documents_specs=[
                SupportingDocumentSpecification(**item)
                for item in guide_dict.get("supporting_documents_specs", [])
            ],
            important_declarations=guide_dict.get("important_declarations", []),
            common_mistakes_to_avoid=guide_dict.get("common_mistakes_to_avoid", []),
            submission_precautions=guide_dict.get("submission_precautions", []),
            portal_steps=[
                PortalStepInstruction(**item)
                for item in guide_dict.get("portal_steps", [])
            ],
            language=language,
            disclaimer=guide_dict.get(
                "disclaimer",
                "Advisory Notice: JanMitra Assist is an application preparation assistant. "
                "It does NOT replace official government portals or submit applications on your behalf."
            ),
        )

        # 7. Persist updated assistance snapshot into assessment record
        updated_res_data = dict(res_data)
        updated_res_data["assistance_data"] = {
            "checklist_total_count": total_count,
            "checklist_completed_count": completed_count,
            "checklist_completion_percentage": completion_pct,
            "language": language,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        assessment.result_data = updated_res_data
        db.commit()

        return ApplicationAssistanceResponse(
            scheme_id=scheme.id,
            scheme_name=scheme.scheme_name,
            category=scheme.category,
            department=scheme.department,
            assessment_id=assessment.id,
            overall_status=overall_status,
            criteria_match_percentage=criteria_match,
            overall_readiness_score=float(readiness_data.get("overall_readiness_score", 0.0)),
            readiness_interpretation=readiness_data.get("score_interpretation", ""),
            document_preparation_statuses=doc_statuses,
            checklist=checklist_items,
            checklist_completed_count=completed_count,
            checklist_total_count=total_count,
            checklist_completion_percentage=completion_pct,
            guide=guide_obj,
            official_application_url=scheme.official_application_url,
            official_source_url=scheme.official_source_url,
            is_demo_data=scheme.is_demo_data,
            language=language,
            evaluated_at=assessment.created_at or datetime.now(timezone.utc),
        )

    @classmethod
    def toggle_checklist_item(
        cls,
        db: Session,
        user_id: UUID,
        scheme_id: UUID,
        item_id: str,
        is_completed: bool,
    ) -> ChecklistUpdateResponse:
        """Mark an individual preparation checklist item as completed or pending."""
        assessment = (
            db.query(Assessment)
            .filter(Assessment.scheme_id == scheme_id, Assessment.user_id == user_id)
            .order_by(Assessment.created_at.desc())
            .first()
        )
        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment record not found or access denied.",
            )

        res_data = dict(assessment.result_data or {})
        completed_set = set(res_data.get("completed_checklist_items", []))

        if is_completed:
            completed_set.add(item_id)
        else:
            completed_set.discard(item_id)

        res_data["completed_checklist_items"] = list(completed_set)
        total_items = res_data.get("assistance_data", {}).get("checklist_total_count", 8)
        completed_count = len(completed_set)
        completion_pct = round((completed_count / total_items) * 100.0, 1) if total_items > 0 else 0.0

        if "assistance_data" in res_data:
            res_data["assistance_data"]["checklist_completed_count"] = completed_count
            res_data["assistance_data"]["checklist_completion_percentage"] = completion_pct

        assessment.result_data = res_data
        db.commit()

        return ChecklistUpdateResponse(
            item_id=item_id,
            is_completed=is_completed,
            completed_count=completed_count,
            total_count=total_items,
            completion_percentage=completion_pct,
            message="Checklist progress updated. This preparation checklist does NOT submit your application to the government.",
        )

    @classmethod
    def get_scheme_guide(
        cls,
        db: Session,
        scheme_id: UUID,
        language: str = "en",
    ) -> ApplicationInfoGuide:
        """Retrieve verified public application guide for a scheme with database caching (SEC-06)."""
        scheme = db.query(Scheme).filter(Scheme.id == scheme_id).first()
        if not scheme:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scheme not found.",
            )

        # Check guide cache on scheme (SEC-06)
        cache = scheme.application_guide_cache or {}
        if language in cache and isinstance(cache[language], dict):
            logger.info(f"Serving public guide for scheme {scheme_id} ({language}) from cache")
            guide_dict = cache[language]
        else:
            logger.info(f"Generating and caching public guide for scheme {scheme_id} ({language})")
            rag_chunks = RAGService.retrieve_relevant_chunks(
                db=db,
                scheme_id=scheme_id,
                query=f"{scheme.scheme_name} application procedure documents instructions",
                top_k=3,
            )
            rag_dicts = [
                {
                    "chunk_title": c.chunk_title,
                    "chunk_category": c.chunk_category,
                    "chunk_content": c.chunk_content,
                    "source_title": c.source_title,
                    "source_reference": c.source_reference,
                }
                for c in rag_chunks
            ]

            llm_adapter = get_llm_adapter()
            guide_dict = llm_adapter.generate_application_guide(
                scheme_name=scheme.scheme_name,
                category=scheme.category,
                department=scheme.department,
                required_documents=scheme.required_documents or [],
                required_profile_fields=scheme.required_profile_fields or [],
                application_process=scheme.application_process or [],
                rag_chunks=rag_dicts,
                language=language,
            )
            new_cache = dict(cache)
            new_cache[language] = guide_dict
            scheme.application_guide_cache = new_cache
            db.commit()

        return ApplicationInfoGuide(
            applicant_info_required=[
                ApplicantInfoRequirement(**item)
                for item in guide_dict.get("applicant_info_required", [])
            ],
            supporting_documents_specs=[
                SupportingDocumentSpecification(**item)
                for item in guide_dict.get("supporting_documents_specs", [])
            ],
            important_declarations=guide_dict.get("important_declarations", []),
            common_mistakes_to_avoid=guide_dict.get("common_mistakes_to_avoid", []),
            submission_precautions=guide_dict.get("submission_precautions", []),
            portal_steps=[
                PortalStepInstruction(**item)
                for item in guide_dict.get("portal_steps", [])
            ],
            language=language,
            disclaimer=guide_dict.get(
                "disclaimer",
                "Advisory Notice: JanMitra Assist is an application preparation assistant. "
                "It does NOT replace official government portals or submit applications on your behalf."
            ),
        )
