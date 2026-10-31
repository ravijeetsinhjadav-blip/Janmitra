import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
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

    # Relationships
    user = relationship("User", back_populates="applications")
    scheme = relationship("Scheme", back_populates="applications")

    def __repr__(self) -> str:
        return f"<Application id={self.id} user_id={self.user_id} scheme_id={self.scheme_id} status='{self.status}'>"
