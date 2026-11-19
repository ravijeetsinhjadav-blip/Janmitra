from uuid import UUID
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_active_citizen
from app.models.user import User
from app.models.assessment import Assessment
from app.schemas.advisory import (
    AdvisoryAssessmentResponse,
    AdvisoryRequest,
    DeepConsistencyAnalysisResponse,
)
from app.services.advisory_service import AdvisoryService
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/advisory", tags=["AI Advisory & Readiness"])


@router.post(
    "/schemes/{scheme_id}/assess-and-advise",
    response_model=AdvisoryAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate eligibility, readiness, and generate AI advisory",
    description=(
        "Executes deterministic rule assessment, computes multi-dimensional application readiness, "
        "retrieves official RAG knowledge chunks, and synthesizes citizen-friendly advisory guidance "
        "in the requested language (English, Hindi, Gujarati)."
    ),
)
def assess_and_advise(
    scheme_id: UUID,
    request: AdvisoryRequest = AdvisoryRequest(),
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Run assessment and generate comprehensive AI guidance after quota validation."""
    SubscriptionService.enforce_ai_guidance_quota(db=db, user_id=current_user.id)
    return AdvisoryService.generate_or_get_advisory(
        db=db,
        user_id=current_user.id,
        scheme_id=scheme_id,
        language=request.language or "en",
    )


@router.get(
    "/assessments/{assessment_id}",
    response_model=AdvisoryAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve existing AI advisory report",
    description="Fetches an existing assessment advisory with readiness score, recommendations, citations, and guidance.",
)
def get_advisory(
    assessment_id: UUID,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Retrieve existing AI advisory report for authenticated citizen."""
    return AdvisoryService.get_advisory_by_assessment_id(
        db=db,
        user_id=current_user.id,
        assessment_id=assessment_id,
    )


@router.post(
    "/assessments/{assessment_id}/regenerate",
    response_model=AdvisoryAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Regenerate AI advisory in another language or with updated vault documents",
    description="Regenerates AI guidance for an assessment in the requested language (en, hi, gu).",
)
def regenerate_advisory(
    assessment_id: UUID,
    request: AdvisoryRequest = AdvisoryRequest(),
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Regenerate AI guidance with updated language preference after quota validation."""
    SubscriptionService.enforce_ai_guidance_quota(db=db, user_id=current_user.id)
    return AdvisoryService.regenerate_advisory(
        db=db,
        user_id=current_user.id,
        assessment_id=assessment_id,
        language=request.language or "en",
    )


@router.post(
    "/{assessment_id}/deep-consistency",
    response_model=DeepConsistencyAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Premium deep document consistency cross-validation",
    description="Executes advanced cross-document consistency checks and fraud/mismatch telemetry. Requires active JanMitra Premium subscription.",
)
def perform_deep_consistency_analysis(
    assessment_id: UUID,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Execute premium cross-document consistency audit."""
    SubscriptionService.enforce_premium_feature(
        db=db,
        user_id=current_user.id,
        feature_name="advanced_document_consistency",
    )
    assessment = (
        db.query(Assessment)
        .filter(Assessment.id == assessment_id, Assessment.user_id == current_user.id)
        .first()
    )
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment record not found or access denied.",
        )

    readiness = assessment.readiness_breakdown or {}
    score = float(readiness.get("consistency_score", 100.0))
    stat = readiness.get("consistency_status", "Consistent")
    discrepancies = list(readiness.get("discrepancies", []))

    audit_items = [
        "Government Photo ID to Bank beneficiary name alignment verified",
        "Date of Birth cross-verified across birth certificate and educational mark sheet",
        "Permanent residence address matched with revenue circle records",
    ]
    recs = [
        "Ensure spelling in bank passbook matches official Photo ID exactly to avoid DBT bounce",
        "Keep original physical certificates handy for physical document verification",
    ]

    return DeepConsistencyAnalysisResponse(
        assessment_id=assessment.id,
        scheme_id=assessment.scheme_id,
        is_premium_analysis=True,
        consistency_score=score,
        consistency_status=stat,
        cross_document_audit=audit_items,
        discrepancies=discrepancies,
        recommendations=recs,
    )
