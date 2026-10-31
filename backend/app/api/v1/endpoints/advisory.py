from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_active_citizen
from app.models.user import User
from app.schemas.advisory import AdvisoryAssessmentResponse, AdvisoryRequest
from app.services.advisory_service import AdvisoryService

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
    """Run assessment and generate comprehensive AI guidance."""
    return AdvisoryService.generate_or_get_advisory(
        db=db,
        user_id=current_user.id,
        scheme_id=scheme_id,
        language=request.language or "en",
    )


@router.get(
    "/assessments/{assessment_id}",
    response_model=AdvisoryAssessmentResponse,
    summary="Retrieve AI advisory and readiness report for past assessment",
    description="Retrieve existing advisory report and readiness breakdown with citizen ownership verification.",
)
def get_assessment_advisory(
    assessment_id: UUID,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Retrieve existing AI advisory report by assessment UUID."""
    return AdvisoryService.get_advisory_by_assessment_id(
        db=db,
        user_id=current_user.id,
        assessment_id=assessment_id,
    )


@router.post(
    "/assessments/{assessment_id}/regenerate",
    response_model=AdvisoryAssessmentResponse,
    summary="Regenerate AI advisory in another language or with updated vault documents",
    description="Regenerates AI guidance for an assessment in the requested language (en, hi, gu).",
)
def regenerate_advisory(
    assessment_id: UUID,
    request: AdvisoryRequest = AdvisoryRequest(),
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Regenerate AI guidance with updated language preference."""
    return AdvisoryService.regenerate_advisory(
        db=db,
        user_id=current_user.id,
        assessment_id=assessment_id,
        language=request.language or "en",
    )
