from uuid import UUID
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_active_citizen
from app.models.user import User
from app.models.profile import UserProfile
from app.models.scheme import Scheme
from app.schemas.assistance import (
    ApplicationAssistanceRequest,
    ApplicationAssistanceResponse,
    ChecklistItemToggleRequest,
    ChecklistUpdateResponse,
    AdvancedCompletenessResponse,
    ApplicationInfoGuide,
    ApplicationPreparationPacketResponse,
)
from app.services.assistance_service import AssistanceService
from app.services.subscription_service import SubscriptionService

router = APIRouter(tags=["Application Assistance"])


@router.post(
    "/schemes/{scheme_id}/prepare",
    response_model=ApplicationAssistanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate personalized application preparation guide and checklist",
    description=(
        "Connects scheme discovery, eligibility assessment, document vault status, and official "
        "RAG knowledge to construct a structured preparation checklist, common pitfalls guide, and official portal roadmap."
    ),
)
def prepare_application(
    scheme_id: UUID,
    request: ApplicationAssistanceRequest = ApplicationAssistanceRequest(),
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Generate personalized application preparation plan for a scheme.
    Enforces monthly AI guidance quota before execution (SEC-06).
    """
    SubscriptionService.enforce_ai_guidance_quota(db=db, user_id=current_user.id)
    return AssistanceService.generate_or_get_assistance(
        db=db,
        user_id=current_user.id,
        scheme_id=scheme_id,
        language=request.language or "en",
    )


@router.patch(
    "/schemes/{scheme_id}/checklist/{item_id}",
    response_model=ChecklistUpdateResponse,
    status_code=status.HTTP_200_OK,
    summary="Toggle citizen completion state of a preparation checklist item",
    description=(
        "Updates completion progress for a preparation checklist item. "
        "Marking items as completed does NOT submit the application to the government."
    ),
)
def toggle_checklist_item(
    scheme_id: UUID,
    item_id: str,
    request: ChecklistItemToggleRequest,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Update citizen preparation checklist item completion state."""
    return AssistanceService.toggle_checklist_item(
        db=db,
        user_id=current_user.id,
        scheme_id=scheme_id,
        item_id=item_id,
        is_completed=request.is_completed,
    )


@router.get(
    "/schemes/{scheme_id}/guide",
    response_model=ApplicationInfoGuide,
    status_code=status.HTTP_200_OK,
    summary="Get application preparation reference guide for a scheme",
    description=(
        "Retrieves structured instructions: required applicant information, supporting document specifications, "
        "common mistakes to avoid, and step-by-step portal instructions."
    ),
)
def get_scheme_guide(
    scheme_id: UUID,
    language: str = Query(default="en", description="Guidance language code: en, hi, gu"),
    db: Session = Depends(get_db),
):
    """Retrieve application preparation information guide (public/unauthenticated or authenticated)."""
    return AssistanceService.get_scheme_guide(
        db=db,
        scheme_id=scheme_id,
        language=language,
    )


@router.post(
    "/schemes/{scheme_id}/advanced-completeness",
    response_model=AdvancedCompletenessResponse,
    status_code=status.HTTP_200_OK,
    summary="Premium advanced application completeness and readiness gap profiling",
    description="Conducts deep field-by-field completeness audit and preparation optimization. Requires active JanMitra Premium subscription.",
)
def evaluate_advanced_completeness(
    scheme_id: UUID,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Execute premium advanced completeness and gap profiling."""
    SubscriptionService.enforce_premium_feature(
        db=db,
        user_id=current_user.id,
        feature_name="advanced_completeness_analysis",
    )
    scheme = db.query(Scheme).filter(Scheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheme not found.",
        )

    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    gaps = []
    if profile:
        if not profile.annual_family_income:
            gaps.append({"field": "annual_family_income", "severity": "High", "advice": "Income certificate must state exact family income."})
        if not profile.occupation:
            gaps.append({"field": "occupation", "severity": "Medium", "advice": "Occupation category clarifies beneficiary classification."})

    optimizations = [
        "Upload gazetted income certificate within 6 months of issue date",
        "Verify bank account is enabled with DBT / NPCI mapping for direct benefit transfer",
    ]
    action_plan = [
        "Phase 1: Complete missing profile attributes",
        "Phase 2: Review verified OCR document extractions",
        "Phase 3: Access official portal URL for final submission",
    ]

    return AdvancedCompletenessResponse(
        scheme_id=scheme.id,
        is_premium_analysis=True,
        completeness_score=95.0 if not gaps else 75.0,
        field_gap_analysis=gaps,
        document_readiness_optimizations=optimizations,
        expedited_action_plan=action_plan,
    )


@router.get(
    "/schemes/{scheme_id}/packet-export",
    response_model=ApplicationPreparationPacketResponse,
    status_code=status.HTTP_200_OK,
    summary="Export consolidated scheme application preparation packet",
    description=(
        "Returns a complete, structured application preparation packet suitable for printing or "
        "downloading. Summarizes scheme details, checklist, portal steps, common mistakes, and precautions. "
        "Strictly contains no citizen PII, Aadhaar numbers, or raw OCR tokens."
    ),
)
def export_preparation_packet(
    scheme_id: UUID,
    language: str = Query(default="en", description="Guidance language code: en, hi, gu"),
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Export application preparation packet for a scheme."""
    return AssistanceService.export_preparation_packet(
        db=db,
        user_id=current_user.id,
        scheme_id=scheme_id,
        language=language,
    )
