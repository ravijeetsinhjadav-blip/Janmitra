import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from app.models.application import (
    Application,
    APPLICATION_STATUSES,
    ApplicationStatusHistory,
    ApplicationReminder,
)
from app.models.scheme import Scheme
from app.models.user import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    ReminderCreate,
    ReminderUpdate,
)
from app.core.logging import get_logger

logger = get_logger("janmitra.application_service")


class ApplicationService:
    """Domain service managing citizen government scheme application tracking records.
    
    Enforces tenant isolation, verified scheme active lifecycle checks,
    atomic transaction rollbacks, immutable status audit history,
    and child reminder management.
    """

    @classmethod
    def create_application(
        cls,
        db: Session,
        user: User,
        payload: ApplicationCreate,
    ) -> Application:
        """Register a new application tracking record and initial Submitted history atomically."""
        # 1. Scheme existence verification
        scheme = db.query(Scheme).filter(Scheme.id == payload.scheme_id).first()
        if not scheme:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Government scheme not found.",
            )

        # 2. Scheme active lifecycle verification (creation blocked for inactive schemes)
        if not scheme.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Government scheme is currently inactive or not accepting applications.",
            )

        # 3. Create tracking record and initial history in one atomic transaction
        app_record = Application(
            id=uuid.uuid4(),
            user_id=user.id,
            scheme_id=payload.scheme_id,
            application_reference_number=payload.application_reference_number,
            submission_date=payload.submission_date,
            status="Submitted",  # Initial status is strictly backend-controlled
        )

        initial_history = ApplicationStatusHistory(
            id=uuid.uuid4(),
            application_id=app_record.id,
            previous_status=None,
            new_status="Submitted",
            event_type="INITIAL_REGISTRATION",
            source="USER_REPORTED",
            remarks=payload.remarks.strip() if payload.remarks else None,
            changed_by_user_id=user.id,
        )

        try:
            db.add(app_record)
            db.add(initial_history)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error("Failed to persist application creation transaction: %s", str(e))
            raise

        # Eagerly load the scheme relation for clean response serialization
        return (
            db.query(Application)
            .options(joinedload(Application.scheme))
            .filter(Application.id == app_record.id)
            .first()
        )

    @classmethod
    def list_applications(
        cls,
        db: Session,
        user: User,
        status_filter: Optional[str] = None,
        scheme_id: Optional[uuid.UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Application], int, int]:
        """Fetch paginated application tracking records belonging strictly to the authenticated citizen."""
        query = db.query(Application).filter(Application.user_id == user.id)

        if status_filter:
            status_clean = status_filter.strip()
            if status_clean not in APPLICATION_STATUSES:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid status '{status_clean}'. Allowed statuses: {', '.join(APPLICATION_STATUSES)}",
                )
            query = query.filter(Application.status == status_clean)

        if scheme_id:
            query = query.filter(Application.scheme_id == scheme_id)

        total = query.count()
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        applications = (
            query.options(joinedload(Application.scheme))
            .order_by(Application.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return applications, total, total_pages

    @classmethod
    def get_application_by_id(
        cls,
        db: Session,
        user: User,
        application_id: uuid.UUID,
    ) -> Application:
        """Fetch an individual tracking record enforcing strict tenant ownership in SQL query."""
        app_record = (
            db.query(Application)
            .options(joinedload(Application.scheme))
            .filter(
                Application.id == application_id,
                Application.user_id == user.id,
            )
            .first()
        )

        if not app_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application tracking record not found.",
            )

        return app_record

    @classmethod
    def update_application(
        cls,
        db: Session,
        user: User,
        application_id: uuid.UUID,
        payload: ApplicationUpdate,
    ) -> Application:
        """Update tracking status, remarks, reference number, or submission date atomically."""
        app_record = (
            db.query(Application)
            .options(joinedload(Application.scheme))
            .filter(
                Application.id == application_id,
                Application.user_id == user.id,
            )
            .first()
        )

        if not app_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application tracking record not found.",
            )

        fields = payload.model_fields_set
        old_status = app_record.status
        status_changed = ("status" in fields and payload.status is not None and payload.status != old_status)
        remarks_submitted = ("remarks" in fields and payload.remarks is not None and payload.remarks.strip() != "")
        details_changed = ("application_reference_number" in fields or ("submission_date" in fields and payload.submission_date is not None))

        # Construct appropriate immutable audit ledger entry
        history_entry: Optional[ApplicationStatusHistory] = None

        if status_changed:
            app_record.status = payload.status
            history_entry = ApplicationStatusHistory(
                id=uuid.uuid4(),
                application_id=app_record.id,
                previous_status=old_status,
                new_status=payload.status,
                event_type="STATUS_UPDATE",
                source="USER_REPORTED",
                remarks=payload.remarks.strip() if payload.remarks else None,
                changed_by_user_id=user.id,
            )
        elif remarks_submitted:
            # Remarks-only event without falsely claiming a status transition
            history_entry = ApplicationStatusHistory(
                id=uuid.uuid4(),
                application_id=app_record.id,
                previous_status=old_status,
                new_status=old_status,
                event_type="REMARK_ADDED",
                source="USER_REPORTED",
                remarks=payload.remarks.strip(),
                changed_by_user_id=user.id,
            )
        elif details_changed:
            # Reference number or submission date changed without status change or remarks
            history_entry = ApplicationStatusHistory(
                id=uuid.uuid4(),
                application_id=app_record.id,
                previous_status=old_status,
                new_status=old_status,
                event_type="APPLICATION_DETAILS_UPDATED",
                source="USER_REPORTED",
                remarks=None,
                changed_by_user_id=user.id,
            )
        # Note: If status was submitted with identical value and no remarks or details changed,
        # history_entry remains None, preventing duplicate history records.

        if "submission_date" in fields and payload.submission_date is not None:
            app_record.submission_date = payload.submission_date

        if "application_reference_number" in fields:
            app_record.application_reference_number = payload.application_reference_number

        app_record.updated_at = datetime.now(timezone.utc)

        try:
            if history_entry:
                db.add(history_entry)
            db.commit()
            db.refresh(app_record)
        except Exception as e:
            db.rollback()
            logger.error("Failed to commit application update transaction: %s", str(e))
            raise

        return app_record

    @classmethod
    def get_application_history(
        cls,
        db: Session,
        user: User,
        application_id: uuid.UUID,
    ) -> Tuple[str, List[ApplicationStatusHistory]]:
        """Retrieve chronological immutable status transition and remark audit records."""
        app_record = (
            db.query(Application)
            .filter(
                Application.id == application_id,
                Application.user_id == user.id,
            )
            .first()
        )

        if not app_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application tracking record not found.",
            )

        history_items = (
            db.query(ApplicationStatusHistory)
            .filter(ApplicationStatusHistory.application_id == application_id)
            .order_by(ApplicationStatusHistory.created_at.asc())
            .all()
        )

        return app_record.status, history_items

    @classmethod
    def delete_application(
        cls,
        db: Session,
        user: User,
        application_id: uuid.UUID,
    ) -> uuid.UUID:
        """Delete a local tracking record with strict ownership in SQL query.
        
        Cascades to remove all child status history and reminder records.
        """
        app_record = (
            db.query(Application)
            .filter(
                Application.id == application_id,
                Application.user_id == user.id,
            )
            .first()
        )

        if not app_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application tracking record not found.",
            )

        deleted_id = app_record.id
        db.delete(app_record)
        db.commit()
        return deleted_id

    # -------------------------------------------------------------------------
    # Application Reminder Management Methods
    # -------------------------------------------------------------------------

    @classmethod
    def create_reminder(
        cls,
        db: Session,
        user: User,
        application_id: uuid.UUID,
        payload: ReminderCreate,
    ) -> ApplicationReminder:
        """Create a new reminder linked to a verified owned application."""
        # 1. Verify parent application ownership
        app_record = (
            db.query(Application)
            .filter(
                Application.id == application_id,
                Application.user_id == user.id,
            )
            .first()
        )
        if not app_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application tracking record not found.",
            )

        reminder = ApplicationReminder(
            id=uuid.uuid4(),
            application_id=app_record.id,
            user_id=user.id,
            title=payload.title,
            description=payload.description,
            reminder_date=payload.reminder_date,
            is_completed=False,
            completed_at=None,
        )

        try:
            db.add(reminder)
            db.commit()
            db.refresh(reminder)
        except Exception as e:
            db.rollback()
            logger.error("Failed to create reminder: %s", str(e))
            raise

        return reminder

    @classmethod
    def list_reminders(
        cls,
        db: Session,
        user: User,
        application_id: uuid.UUID,
        is_completed: Optional[bool] = None,
    ) -> List[ApplicationReminder]:
        """List reminders belonging to an application with optional completion filter."""
        # Verify parent application ownership
        app_record = (
            db.query(Application)
            .filter(
                Application.id == application_id,
                Application.user_id == user.id,
            )
            .first()
        )
        if not app_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application tracking record not found.",
            )

        query = db.query(ApplicationReminder).filter(
            ApplicationReminder.application_id == application_id,
            ApplicationReminder.user_id == user.id,
        )

        if is_completed is not None:
            query = query.filter(ApplicationReminder.is_completed == is_completed)

        return query.order_by(ApplicationReminder.reminder_date.asc()).all()

    @classmethod
    def list_user_upcoming_reminders(
        cls,
        db: Session,
        user: User,
    ) -> List[ApplicationReminder]:
        """Retrieve all active uncompleted reminders across all applications for the authenticated citizen."""
        return (
            db.query(ApplicationReminder)
            .filter(
                ApplicationReminder.user_id == user.id,
                ApplicationReminder.is_completed == False,
            )
            .order_by(ApplicationReminder.reminder_date.asc())
            .all()
        )

    @classmethod
    def get_reminder_by_id(
        cls,
        db: Session,
        user: User,
        application_id: uuid.UUID,
        reminder_id: uuid.UUID,
    ) -> ApplicationReminder:
        """Retrieve a specific reminder validating dual application and user ownership."""
        reminder = (
            db.query(ApplicationReminder)
            .filter(
                ApplicationReminder.id == reminder_id,
                ApplicationReminder.application_id == application_id,
                ApplicationReminder.user_id == user.id,
            )
            .first()
        )
        if not reminder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reminder not found.",
            )
        return reminder

    @classmethod
    def update_reminder(
        cls,
        db: Session,
        user: User,
        application_id: uuid.UUID,
        reminder_id: uuid.UUID,
        payload: ReminderUpdate,
    ) -> ApplicationReminder:
        """Update reminder fields or toggle completion status."""
        reminder = (
            db.query(ApplicationReminder)
            .filter(
                ApplicationReminder.id == reminder_id,
                ApplicationReminder.application_id == application_id,
                ApplicationReminder.user_id == user.id,
            )
            .first()
        )
        if not reminder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reminder not found.",
            )

        fields = payload.model_fields_set

        if "title" in fields and payload.title is not None:
            reminder.title = payload.title

        if "description" in fields:
            reminder.description = payload.description

        if "reminder_date" in fields and payload.reminder_date is not None:
            reminder.reminder_date = payload.reminder_date

        if "is_completed" in fields and payload.is_completed is not None:
            if payload.is_completed and not reminder.is_completed:
                # Newly completed
                reminder.is_completed = True
                reminder.completed_at = datetime.now(timezone.utc)
            elif not payload.is_completed and reminder.is_completed:
                # Reopened
                reminder.is_completed = False
                reminder.completed_at = None

        reminder.updated_at = datetime.now(timezone.utc)

        try:
            db.commit()
            db.refresh(reminder)
        except Exception as e:
            db.rollback()
            logger.error("Failed to update reminder: %s", str(e))
            raise

        return reminder

    @classmethod
    def delete_reminder(
        cls,
        db: Session,
        user: User,
        application_id: uuid.UUID,
        reminder_id: uuid.UUID,
    ) -> uuid.UUID:
        """Permanently delete an application reminder."""
        reminder = (
            db.query(ApplicationReminder)
            .filter(
                ApplicationReminder.id == reminder_id,
                ApplicationReminder.application_id == application_id,
                ApplicationReminder.user_id == user.id,
            )
            .first()
        )
        if not reminder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reminder not found.",
            )

        deleted_id = reminder.id
        db.delete(reminder)
        db.commit()
        return deleted_id
