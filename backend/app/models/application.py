import uuid
from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    Integer,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, foreign
from app.core.database import Base

APPLICATION_STATUSES = [
    "Submitted",
    "Under Review",
    "Pending",
    "Document Verification",
    "Approved",
    "Rejected",
    "Completed",
]


class Application(Base):
    """Citizen application tracking record.
    
    Workflow Architecture Note:
    Citizens complete their actual applications on official government portals.
    This entity allows citizens to manually enter their portal reference number
    and track status progression locally.
    """
    __tablename__ = "applications"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Primary UUID key for application record",
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Citizen user ID",
    )
    scheme_id = Column(
        UUID(as_uuid=True),
        ForeignKey("schemes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Target government scheme applied for",
    )
    application_reference_number = Column(
        String(100),
        nullable=True,
        index=True,
        comment="Official acknowledgement / application reference from government portal (optional)",
    )
    submission_date = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date and time when user submitted on the official portal",
    )
    status = Column(
        String(50),
        nullable=False,
        default="Submitted",
        index=True,
        comment="Manual tracking status: Submitted, Under Review, Pending, Document Verification, Approved, Rejected, Completed",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Record creation timestamp",
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Record last updated timestamp",
    )

    # Composite unique constraint supporting child reminder composite foreign key
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_applications_id_user_id"),
    )

    # Relationships
    user = relationship("User", back_populates="applications")
    scheme = relationship("Scheme", back_populates="applications")
    status_history = relationship(
        "ApplicationStatusHistory",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationStatusHistory.created_at.asc()",
    )
    reminders = relationship(
        "ApplicationReminder",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationReminder.reminder_date.asc()",
        overlaps="application_reminders,user",
    )

    def __repr__(self) -> str:
        return f"<Application id={self.id} user_id={self.user_id} scheme_id={self.scheme_id} status='{self.status}'>"


class ApplicationStatusHistory(Base):
    """Immutable audit ledger tracking status transitions, remarks, and user-reported events.
    Architecture Note:
    All citizen-entered status updates are marked source='USER_REPORTED'.
    Local statuses (including Approved/Rejected) represent citizen-reported progress
    and are not official government determinations.
    """
    __tablename__ = "application_status_history"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Primary UUID key for status history record",
    )
    application_id = Column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent application tracking record ID",
    )
    previous_status = Column(
        String(50),
        nullable=True,
        comment="Status prior to this transition (null for initial creation)",
    )
    new_status = Column(
        String(50),
        nullable=False,
        comment="Updated status: Submitted, Under Review, Pending, Document Verification, Approved, Rejected, Completed",
    )
    event_type = Column(
        String(50),
        nullable=False,
        default="STATUS_UPDATE",
        comment="Event category: INITIAL_REGISTRATION, STATUS_UPDATE, REMARK_ADDED, APPLICATION_DETAILS_UPDATED",
    )
    source = Column(
        String(50),
        nullable=False,
        default="USER_REPORTED",
        comment="Source of update: USER_REPORTED or SYSTEM_MIGRATION",
    )
    remarks = Column(
        Text,
        nullable=True,
        comment="Citizen notes, remarks, or progress observations (null if not provided)",
    )
    changed_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User ID who submitted this update (audit trail)",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="Timestamp when this status transition or remark occurred",
    )

    # Relationships
    application = relationship("Application", back_populates="status_history")
    changed_by = relationship("User")

    def __repr__(self) -> str:
        return f"<ApplicationStatusHistory id={self.id} application_id={self.application_id} event_type='{self.event_type}' new_status='{self.new_status}'>"


class ApplicationReminder(Base):
    """Citizen reminder/task for an application (e.g. document submission, biometrics)."""
    __tablename__ = "application_reminders"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Primary UUID key for reminder record",
    )
    application_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Associated application tracking record ID",
    )
    user_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Citizen owner ID (strictly locked to application.user_id)",
    )
    title = Column(
        String(200),
        nullable=False,
        comment="Short summary / title of the reminder task",
    )
    description = Column(
        Text,
        nullable=True,
        comment="Detailed instructions, required documents, or office address",
    )
    reminder_date = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Scheduled date and time for the reminder (normalized UTC)",
    )
    is_completed = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Completion flag",
    )
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when reminder was completed (cleared if reopened)",
    )
    last_dispatched_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when notification was successfully dispatched",
    )
    dispatch_lease_until = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Lease expiration timestamp for active worker claim",
    )
    dispatch_token = Column(
        String(64),
        nullable=True,
        comment="Unique worker token claiming this reminder for dispatch",
    )
    retry_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of dispatch retry attempts on transient failure",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Record creation timestamp",
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Record last updated timestamp",
    )

    # Composite Foreign Key: guarantees application_reminders.user_id MUST match applications.user_id
    __table_args__ = (
        ForeignKeyConstraint(
            ["application_id", "user_id"],
            ["applications.id", "applications.user_id"],
            ondelete="CASCADE",
            name="fk_application_reminders_application_user",
        ),
    )

    # Relationships
    application = relationship(
        "Application",
        back_populates="reminders",
        overlaps="application_reminders,user",
    )
    user = relationship(
        "User",
        back_populates="application_reminders",
        primaryjoin="foreign(ApplicationReminder.user_id) == User.id",
        overlaps="application,reminders",
    )

    def __repr__(self) -> str:
        return f"<ApplicationReminder id={self.id} application_id={self.application_id} completed={self.is_completed}>"

