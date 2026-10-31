import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class AccountDeletionRequest(Base):
    """Citizen Account Deletion Request Record.
    
    Privacy Architecture:
    1. Authenticated citizens can submit an account deletion request.
    2. Active sessions are revoked immediately upon request.
    3. Records are retained in protected state according to retention policy
       before processing, rather than destructive immediate deletion.
    """
    __tablename__ = "account_deletion_requests"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Primary UUID key for deletion request",
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Requesting citizen user ID",
    )
    status = Column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
        comment="Request status: pending, cancelled, completed",
    )
    reason = Column(
        Text,
        nullable=True,
        comment="Citizen feedback or rationale for deletion request (optional)",
    )
    requested_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when citizen requested deletion",
    )
    scheduled_for = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="Timestamp when deletion should be executed after statutory retention",
    )
    processed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when deletion was processed by administration",
    )

    # Relationships
    user = relationship("User", back_populates="deletion_requests")

    def __repr__(self) -> str:
        return f"<AccountDeletionRequest id={self.id} user_id={self.user_id} status='{self.status}'>"

