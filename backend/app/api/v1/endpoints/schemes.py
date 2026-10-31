import math
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_citizen, get_current_user
from app.models.user import User
from app.schemas.scheme import (
    AssessmentHistoryItem,
    AssessmentResultResponse,
    SchemeCategoryItem,
    SchemeListResponse,
    SchemeRecommendation,
    SchemeResponse,
)
from app.services.scheme_service import SchemeService

router = APIRouter()


@router.get(
    "/categories",
    response_model=List[SchemeCategoryItem],
    summary="List available scheme categories",
    description="Retrieve list of unique sector categories with active scheme counts.",
)
def get_scheme_categories(db: Session = Depends(get_db)):
    """Retrieve distinct scheme sector categories."""
    return SchemeService.get_categories(db)


@router.get(
    "/recommendations",
    response_model=List[SchemeRecommendation],
    summary="Get profile-based scheme recommendations",
    description="Retrieve tailored government scheme recommendations evaluated against authenticated citizen demographics.",
)
def get_recommendations(
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Retrieve personalized scheme recommendations for authenticated citizen."""
    return SchemeService.get_recommendations_for_user(db, current_user.id)


@router.get(
    "/assessments/history",
    response_model=List[AssessmentHistoryItem],
    summary="Get citizen eligibility assessment history",
    description="Retrieve past eligibility evaluations for the authenticated citizen with strict user isolation.",
)
def get_assessment_history(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Retrieve citizen's historical assessment runs."""
    return SchemeService.get_assessment_history(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/assessments/{assessment_id}",
    response_model=AssessmentResultResponse,
    summary="Get specific assessment result details",
    description="Retrieve condition breakdown and advisory score for a specific assessment run.",
)
def get_assessment_detail(
    assessment_id: UUID,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Retrieve detailed outcome of a specific assessment."""
    return SchemeService.get_assessment_detail(
        db=db,
        user_id=current_user.id,
        assessment_id=assessment_id,
    )


@router.get(
    "",
    response_model=SchemeListResponse,
    summary="Discover and search government schemes",
    description="Search, filter, and paginate government schemes by keyword, category, state, and status.",
)
def list_schemes(
    q: Optional[str] = Query(None, description="Search keyword in scheme name, description, or department"),
    category: Optional[str] = Query(None, description="Filter by sector category (e.g. Agriculture, Healthcare)"),
    state: Optional[str] = Query(None, description="Filter by applicable state name (returns state-specific and All India schemes)"),
    status_filter: Optional[str] = Query("active", description="Filter by scheme status (active, inactive, discontinued)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    """Discover government schemes with multi-criteria search and pagination."""
    items, total = SchemeService.get_schemes(
        db=db,
        query=q,
        category=category,
        state=state,
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return SchemeListResponse(
        items=[SchemeResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/{scheme_id}",
    response_model=SchemeResponse,
    summary="Get government scheme full details",
    description="Retrieve comprehensive scheme overview, structured eligibility criteria, benefits, documents, and official URLs.",
)
def get_scheme_detail(
    scheme_id: UUID,
    db: Session = Depends(get_db),
):
    """Retrieve complete scheme details by UUID."""
    scheme = SchemeService.get_scheme_by_id(db, scheme_id)
    return SchemeResponse.model_validate(scheme)


@router.post(
    "/{scheme_id}/assess",
    response_model=AssessmentResultResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Evaluate citizen eligibility for a scheme",
    description="Run deterministic rule engine against authenticated citizen profile and persist assessment record.",
)
def run_eligibility_assessment(
    scheme_id: UUID,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Execute eligibility assessment and persist advisory result."""
    return SchemeService.run_assessment(
        db=db,
        user_id=current_user.id,
        scheme_id=scheme_id,
    )

