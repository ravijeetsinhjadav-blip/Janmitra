import uuid
from typing import Optional, List
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
    ApplicationStatusHistoryResponse,
    ApplicationStatusHistoryListResponse,
    ReminderCreate,
    ReminderUpdate,
    ReminderResponse,
    ReminderListResponse,
    ReminderDeleteResponse,
)
from app.services.application_service import ApplicationService

router = APIRouter()


@router.post(
    "",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register submitted application for tracking",
    description="Record an application formally submitted on an official government portal with atomic initial history.",
)
def create_application(
    payload: ApplicationCreate,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Register submitted application under citizen ownership with initial 'Submitted' status and history."""
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


# -------------------------------------------------------------------------
# Global Upcoming Reminders Route (Mounted BEFORE dynamic /{application_id})
# -------------------------------------------------------------------------

@router.get(
    "/reminders/upcoming",
    response_model=ReminderListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all upcoming reminders for authenticated citizen",
    description="Retrieve all active uncompleted reminders across all tracked applications for the authenticated caller.",
)
def list_user_upcoming_reminders(
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """List all upcoming reminders for the current citizen ordered by reminder date."""
    reminders = ApplicationService.list_user_upcoming_reminders(
        db=db,
        user=current_user,
    )
    return ReminderListResponse(
        total=len(reminders),
        reminders=[ReminderResponse.model_validate(r) for r in reminders],
    )


# -------------------------------------------------------------------------
# Dynamic Application Subresource Routes
# -------------------------------------------------------------------------

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
    description="Update tracking status, remarks, reference number, or submission date. Rejects empty payloads and nulls.",
)
def update_application(
    application_id: uuid.UUID,
    payload: ApplicationUpdate,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Update citizen tracking entry atomically; appends immutable status/remark history."""
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
    """Delete tracking record from JanMitra database with ownership check (cascades child history and reminders)."""
    deleted_id = ApplicationService.delete_application(
        db=db,
        user=current_user,
        application_id=application_id,
    )
    return ApplicationDeleteResponse(id=deleted_id)


# -------------------------------------------------------------------------
# Status History Subresource Route
# -------------------------------------------------------------------------

@router.get(
    "/{application_id}/history",
    response_model=ApplicationStatusHistoryListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get application status history and remarks",
    description="Retrieve chronological immutable audit trail of manual citizen status updates and progress remarks.",
)
def get_application_history(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Retrieve chronological status history for an owned application tracking record."""
    current_status, history_records = ApplicationService.get_application_history(
        db=db,
        user=current_user,
        application_id=application_id,
    )
    return ApplicationStatusHistoryListResponse(
        application_id=application_id,
        current_status=current_status,
        total=len(history_records),
        history=[ApplicationStatusHistoryResponse.model_validate(h) for h in history_records],
    )


# -------------------------------------------------------------------------
# Application Reminders CRUD Subresource Routes
# -------------------------------------------------------------------------

@router.post(
    "/{application_id}/reminders",
    response_model=ReminderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create reminder for application",
    description="Schedule a task or deadline reminder associated with an owned application.",
)
def create_reminder(
    application_id: uuid.UUID,
    payload: ReminderCreate,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Create a new reminder linked to the specified owned application."""
    reminder = ApplicationService.create_reminder(
        db=db,
        user=current_user,
        application_id=application_id,
        payload=payload,
    )
    return ReminderResponse.model_validate(reminder)


@router.get(
    "/{application_id}/reminders",
    response_model=ReminderListResponse,
    status_code=status.HTTP_200_OK,
    summary="List reminders for application",
    description="Retrieve all reminders scheduled for an application, sorted chronologically.",
)
def list_reminders(
    application_id: uuid.UUID,
    is_completed: Optional[bool] = Query(None, description="Filter by completion status (true/false)"),
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """List reminders for the specified owned application."""
    reminders = ApplicationService.list_reminders(
        db=db,
        user=current_user,
        application_id=application_id,
        is_completed=is_completed,
    )
    return ReminderListResponse(
        total=len(reminders),
        reminders=[ReminderResponse.model_validate(r) for r in reminders],
    )


@router.get(
    "/{application_id}/reminders/{reminder_id}",
    response_model=ReminderResponse,
    status_code=status.HTTP_200_OK,
    summary="Get reminder detail",
    description="Retrieve details of a specific reminder validating dual application and user ownership.",
)
def get_reminder_detail(
    application_id: uuid.UUID,
    reminder_id: uuid.UUID,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Retrieve specific reminder; returns HTTP 404 on unowned or mismatched resources."""
    reminder = ApplicationService.get_reminder_by_id(
        db=db,
        user=current_user,
        application_id=application_id,
        reminder_id=reminder_id,
    )
    return ReminderResponse.model_validate(reminder)


@router.patch(
    "/{application_id}/reminders/{reminder_id}",
    response_model=ReminderResponse,
    status_code=status.HTTP_200_OK,
    summary="Update reminder or toggle completion",
    description="Update reminder title, date, description, or completion status (auto-manages completed_at).",
)
def update_reminder(
    application_id: uuid.UUID,
    reminder_id: uuid.UUID,
    payload: ReminderUpdate,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Update reminder details with dual ownership verification."""
    reminder = ApplicationService.update_reminder(
        db=db,
        user=current_user,
        application_id=application_id,
        reminder_id=reminder_id,
        payload=payload,
    )
    return ReminderResponse.model_validate(reminder)


@router.delete(
    "/{application_id}/reminders/{reminder_id}",
    response_model=ReminderDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete application reminder",
    description="Permanently delete an application reminder.",
)
def delete_reminder(
    application_id: uuid.UUID,
    reminder_id: uuid.UUID,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Permanently delete a reminder with ownership verification."""
    deleted_id = ApplicationService.delete_reminder(
        db=db,
        user=current_user,
        application_id=application_id,
        reminder_id=reminder_id,
    )
    return ReminderDeleteResponse(id=deleted_id)
