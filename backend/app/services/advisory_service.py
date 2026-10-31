from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.scheme import Scheme
from app.models.assessment import Assessment
from app.models.profile import UserProfile
from app.services.scheme_service import SchemeService
from app.services.rag_service import RAGService
from app.services.readiness_service import ReadinessService
from app.services.llm_service import get_llm_adapter
from app.schemas.advisory import (
    AdvisoryAssessmentResponse,
    ReadinessBreakdown,
    AIAdvisoryGuidance,
    ConditionAnalysisItem,
    CitationItem,
)
from app.core.logging import get_logger

logger = get_logger("janmitra.advisory_service")


class AdvisoryService:
    """Orchestrates deterministic rule evaluations, multi-dimensional readiness scoring,
    RAG official source retrieval, and cloud LLM advisory synthesis.
    """

    @classmethod
    def generate_or_get_advisory(
        cls,
        db: Session,
        user_id: UUID,
        scheme_id: UUID,
        language: str = "en",
    ) -> AdvisoryAssessmentResponse:
        """Run deterministic evaluation, calculate application readiness, retrieve RAG knowledge,
        and generate multilingual AI guidance.
        """
        scheme = db.query(Scheme).filter(Scheme.id == scheme_id).first()
        if not scheme:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scheme not found.",
            )

        # 1. Run deterministic assessment first (sole source of eligibility truth)
        assessment_res = SchemeService.run_assessment(db=db, user_id=user_id, scheme_id=scheme_id)

        assessment = db.query(Assessment).filter(Assessment.id == assessment_res.assessment_id).first()
        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to persist or retrieve assessment record.",
            )

        # 2. Evaluate multi-dimensional application readiness
        readiness_data = ReadinessService.evaluate_readiness(
            db=db,
            user_id=user_id,
            scheme=scheme,
            criteria_match_percentage=assessment_res.criteria_match_percentage,
            missing_fields=assessment_res.missing_fields,
            overall_status=assessment_res.overall_status,
        )

        # 3. Retrieve relevant RAG official knowledge chunks
        rag_chunks = RAGService.retrieve_relevant_chunks(
            db=db,
            scheme_id=scheme_id,
            query=f"{scheme.scheme_name} eligibility documents benefits {assessment_res.overall_status}",
            top_k=3,
        )
        rag_dicts = [
            {
                "chunk_title": c.chunk_title,
                "chunk_category": c.chunk_category,
                "chunk_content": c.chunk_content,
                "source_title": c.source_title,
                "source_reference": (
                    f"[WARNING: {c.source_freshness_status.upper()}] {c.source_reference}"
                    if c.source_freshness_status != "Verified Official Source"
                    else c.source_reference
                ),
                "source_url": c.source_url,
                "source_freshness_status": c.source_freshness_status,
                "is_demo_data": c.is_demo_data,
            }
            for c in rag_chunks
        ]

        # 4. Invoke LLM Provider Adapter
        llm_adapter = get_llm_adapter()
        breakdown_dicts = [c.model_dump() for c in assessment_res.conditions_breakdown]

        advisory_dict = llm_adapter.generate_advisory(
            scheme_name=scheme.scheme_name,
            category=scheme.category,
            overall_status=assessment_res.overall_status,
            criteria_match_percentage=assessment_res.criteria_match_percentage,
            conditions_breakdown=breakdown_dicts,
            missing_fields=assessment_res.missing_fields,
            rag_chunks=rag_dicts,
            document_readiness=readiness_data,
            language=language,
        )

        # 5. Persist readiness and AI guidance back to Assessment record
        assessment.overall_readiness_score = readiness_data["overall_readiness_score"]
        assessment.readiness_breakdown = readiness_data
        assessment.advisory_guidance = advisory_dict
        assessment.language = language
        db.commit()
        db.refresh(assessment)

        return cls._build_response(assessment, scheme, readiness_data, advisory_dict)

    @classmethod
    def get_advisory_by_assessment_id(
        cls,
        db: Session,
        user_id: UUID,
        assessment_id: UUID,
    ) -> AdvisoryAssessmentResponse:
        """Retrieve existing AI advisory report with strict citizen ownership validation."""
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

        scheme = db.query(Scheme).filter(Scheme.id == assessment.scheme_id).first()
        if not scheme:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated scheme not found.",
            )

        # If guidance has not been generated yet, generate it now
        if not assessment.advisory_guidance or not assessment.readiness_breakdown:
            return cls.generate_or_get_advisory(
                db=db,
                user_id=user_id,
                scheme_id=scheme.id,
                language=assessment.language or "en",
            )

        return cls._build_response(
            assessment=assessment,
            scheme=scheme,
            readiness_data=assessment.readiness_breakdown,
            advisory_dict=assessment.advisory_guidance,
        )

    @classmethod
    def regenerate_advisory(
        cls,
        db: Session,
        user_id: UUID,
        assessment_id: UUID,
        language: str = "en",
    ) -> AdvisoryAssessmentResponse:
        """Regenerate AI guidance in a different language or refresh with updated vault documents."""
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

        scheme = db.query(Scheme).filter(Scheme.id == assessment.scheme_id).first()
        if not scheme:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated scheme not found.",
            )

        res_data = assessment.result_data or {}
        criteria_match = float(res_data.get("criteria_match_percentage", assessment.overall_readiness_score or 0.0))
        missing_fields = res_data.get("missing_fields", [])
        overall_status = res_data.get("overall_status", "Insufficient Information")
        conditions = res_data.get("conditions_breakdown", [])

        # Re-evaluate readiness
        readiness_data = ReadinessService.evaluate_readiness(
            db=db,
            user_id=user_id,
            scheme=scheme,
            criteria_match_percentage=criteria_match,
            missing_fields=missing_fields,
            overall_status=overall_status,
        )

        # Retrieve RAG chunks
        rag_chunks = RAGService.retrieve_relevant_chunks(
            db=db,
            scheme_id=scheme.id,
            query=f"{scheme.scheme_name} eligibility documents benefits {overall_status}",
            top_k=3,
        )
        rag_dicts = [
            {
                "chunk_title": c.chunk_title,
                "chunk_category": c.chunk_category,
                "chunk_content": c.chunk_content,
                "source_title": c.source_title,
                "source_reference": (
                    f"[WARNING: {c.source_freshness_status.upper()}] {c.source_reference}"
                    if c.source_freshness_status != "Verified Official Source"
                    else c.source_reference
                ),
                "source_url": c.source_url,
                "source_freshness_status": c.source_freshness_status,
                "is_demo_data": c.is_demo_data,
            }
            for c in rag_chunks
        ]

        # Generate advisory in requested language
        llm_adapter = get_llm_adapter()
        advisory_dict = llm_adapter.generate_advisory(
            scheme_name=scheme.scheme_name,
            category=scheme.category,
            overall_status=overall_status,
            criteria_match_percentage=criteria_match,
            conditions_breakdown=conditions,
            missing_fields=missing_fields,
            rag_chunks=rag_dicts,
            document_readiness=readiness_data,
            language=language,
        )

        assessment.overall_readiness_score = readiness_data["overall_readiness_score"]
        assessment.readiness_breakdown = readiness_data
        assessment.advisory_guidance = advisory_dict
        assessment.language = language
        db.commit()
        db.refresh(assessment)

        return cls._build_response(assessment, scheme, readiness_data, advisory_dict)

    @staticmethod
    def _build_response(
        assessment: Assessment,
        scheme: Scheme,
        readiness_data: Dict[str, Any],
        advisory_dict: Dict[str, Any],
    ) -> AdvisoryAssessmentResponse:
        res_data = assessment.result_data or {}

        criteria_items = [
            ConditionAnalysisItem(
                condition=c.get("condition", "Condition"),
                status=c.get("status", "unknown"),
                note=c.get("note", ""),
            )
            for c in advisory_dict.get("criteria_analysis", [])
        ]

        citation_items = [
            CitationItem(
                title=c.get("title", "Guideline"),
                source_title=c.get("source_title", scheme.scheme_name),
                source_reference=c.get("source_reference"),
                source_url=c.get("source_url", scheme.official_source_url),
                source_freshness_status=c.get("source_freshness_status", "Verified Official Source"),
                is_demo_data=c.get("is_demo_data", True),
            )
            for c in advisory_dict.get("citations", [])
        ]

        return AdvisoryAssessmentResponse(
            assessment_id=assessment.id,
            scheme_id=scheme.id,
            scheme_name=res_data.get("scheme_name", scheme.scheme_name),
            category=res_data.get("category", scheme.category),
            overall_status=res_data.get("overall_status", "Insufficient Information"),
            readiness=ReadinessBreakdown(
                overall_readiness_score=float(readiness_data.get("overall_readiness_score", 0.0)),
                criteria_match_percentage=float(readiness_data.get("criteria_match_percentage", 0.0)),
                document_coverage_percentage=float(readiness_data.get("document_coverage_percentage", 0.0)),
                information_completeness_percentage=float(readiness_data.get("information_completeness_percentage", 0.0)),
                consistency_score=float(readiness_data.get("consistency_score", 100.0)),
                consistency_status=readiness_data.get("consistency_status", "Consistent"),
                score_interpretation=readiness_data.get("score_interpretation", ""),
                uploaded_document_types=readiness_data.get("uploaded_document_types", []),
                missing_document_types=readiness_data.get("missing_document_types", []),
                discrepancies=readiness_data.get("discrepancies", []),
                low_confidence_documents=readiness_data.get("low_confidence_documents", []),
            ),
            advisory=AIAdvisoryGuidance(
                summary=advisory_dict.get("summary", ""),
                assessment_explanation=advisory_dict.get("assessment_explanation", ""),
                criteria_analysis=criteria_items,
                document_analysis=advisory_dict.get("document_analysis", ""),
                potential_inconsistencies=advisory_dict.get("potential_inconsistencies", []),
                next_steps=advisory_dict.get("next_steps", []),
                official_portal_guidance=advisory_dict.get("official_portal_guidance", ""),
                citations=citation_items,
                language=advisory_dict.get("language", "en"),
                is_mock=advisory_dict.get("is_mock", False),
                disclaimer=advisory_dict.get(
                    "disclaimer",
                    "Advisory Notice: This guidance is AI-assisted and based on citizen-provided details. "
                    "It does NOT constitute an official government determination or guarantee approval."
                ),
            ),
            evaluated_at=assessment.created_at or datetime.utcnow(),
            official_source_url=scheme.official_source_url,
            official_application_url=scheme.official_application_url,
        )

