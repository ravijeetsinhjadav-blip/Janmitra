import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_citizen
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationResponse,
    ApplicationListResponse,
    ApplicationDeleteResponse,
)
from app.services.application_service import ApplicationService

router = APIRouter()


@router.post(
    "",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register submitted application for tracking",
    description="Record an application that has been formally submitted on an official government portal.",
)
def create_application(
    payload: ApplicationCreate,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Register submitted application under citizen ownership with initial 'Submitted' status."""
    app_record = ApplicationService.create_application(
        db=db,
        user=current_user,
        payload=payload,
    )
    return ApplicationResponse.model_validate(app_record)


@router.get(
    "",
    response_model=ApplicationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List citizen application tracking records",
    description="Retrieve paginated tracking records for the authenticated citizen with optional status filtering.",
)
def list_applications(
    status: Optional[str] = Query(None, description="Filter by status: Submitted, Under Review, Pending, Document Verification, Approved, Rejected, Completed"),
    scheme_id: Optional[uuid.UUID] = Query(None, description="Filter by scheme UUID"),
    page: int = Query(1, ge=1, description="Page number (>= 1)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (1 to 100)"),
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """List citizen's tracked applications with strict user isolation and pagination bounds."""
    items, total, total_pages = ApplicationService.list_applications(
        db=db,
        user=current_user,
        status_filter=status,
        scheme_id=scheme_id,
        page=page,
        page_size=page_size,
    )
    return ApplicationListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        applications=[ApplicationResponse.model_validate(item) for item in items],
    )


@router.get(
    "/{application_id}",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get application tracking record details",
    description="Retrieve full tracking details for a specific application record with ownership verification.",
)
def get_application_detail(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Retrieve tracking record; returns HTTP 404 for non-existent or unowned records (IDOR protection)."""
    app_record = ApplicationService.get_application_by_id(
        db=db,
        user=current_user,
        application_id=application_id,
    )
    return ApplicationResponse.model_validate(app_record)


@router.patch(
    "/{application_id}",
    response_model=ApplicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update application tracking status or details",
    description="Update tracking status, reference number, or submission date. Rejects empty payloads and nulls.",
)
def update_application(
    application_id: uuid.UUID,
    payload: ApplicationUpdate,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Update citizen tracking entry; requires explicit fields and returns HTTP 404 on unowned records."""
    app_record = ApplicationService.update_application(
        db=db,
        user=current_user,
        application_id=application_id,
        payload=payload,
    )
    return ApplicationResponse.model_validate(app_record)


@router.delete(
    "/{application_id}",
    response_model=ApplicationDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete local tracking record",
    description="Delete local tracking entry from JanMitra Assist (does NOT cancel the official government application).",
)
def delete_application(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Delete tracking record from JanMitra database with ownership check."""
    deleted_id = ApplicationService.delete_application(
        db=db,
        user=current_user,
        application_id=application_id,
    )
    return ApplicationDeleteResponse(id=deleted_id)

