import uuid
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from app.models.application import Application, APPLICATION_STATUSES
from app.models.scheme import Scheme
from app.models.user import User
from app.schemas.application import ApplicationCreate, ApplicationUpdate
from app.core.logging import get_logger

logger = get_logger("janmitra.application_service")


class ApplicationService:
    """Domain service managing citizen government scheme application tracking records.
    
    Enforces tenant isolation, verified scheme active lifecycle checks,
    and joined-load eager retrieval to avoid N+1 queries.
    """

    @classmethod
    def create_application(
        cls,
        db: Session,
        user: User,
        payload: ApplicationCreate,
    ) -> Application:
        """Register a new application tracking record for an application submitted on an official portal."""
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

        # 3. Create tracking record - user_id derived strictly from authenticated user context
        app_record = Application(
            id=uuid.uuid4(),
            user_id=user.id,
            scheme_id=payload.scheme_id,
            application_reference_number=payload.application_reference_number,
            submission_date=payload.submission_date,
            status="Submitted",  # Initial status is strictly backend-controlled
        )

        db.add(app_record)
        db.commit()

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
        """Fetch an individual tracking record enforcing strict tenant ownership in SQL query.
        
        Returns uniform HTTP 404 for non-existent IDs and cross-user IDs to prevent object enumeration.
        """
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
        """Update tracking status, reference number, or submission date with strict ownership in SQL query."""
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

        if "status" in fields and payload.status is not None:
            app_record.status = payload.status

        if "submission_date" in fields and payload.submission_date is not None:
            app_record.submission_date = payload.submission_date

        if "application_reference_number" in fields:
            app_record.application_reference_number = payload.application_reference_number

        app_record.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(app_record)

        return app_record

    @classmethod
    def delete_application(
        cls,
        db: Session,
        user: User,
        application_id: uuid.UUID,
    ) -> uuid.UUID:
        """Delete a local tracking record with strict ownership in SQL query.
        
        Does not affect the citizen's actual submission on the official government portal.
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

