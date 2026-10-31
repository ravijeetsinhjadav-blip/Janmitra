from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_active_citizen
from app.models.user import User
from app.schemas.assistance import (
    ApplicationAssistanceRequest,
    ApplicationAssistanceResponse,
    ChecklistItemToggleRequest,
    ChecklistUpdateResponse,
    ApplicationInfoGuide,
)
from app.services.assistance_service import AssistanceService

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
    """Generate personalized application preparation plan for a scheme."""
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
    summary="Retrieve verified general scheme application guide and document specifications",
    description="Returns official documentary specifications, common mistakes, and application process steps.",
)
def get_scheme_guide(
    scheme_id: UUID,
    language: str = Query(default="en", description="Guidance language code: en, hi, gu"),
    db: Session = Depends(get_db),
):
    """Retrieve public application guide for a scheme."""
    return AssistanceService.get_scheme_guide(
        db=db,
        scheme_id=scheme_id,
        language=language,
    )

