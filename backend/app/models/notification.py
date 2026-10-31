import uuid
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class Notification(Base):
    """Citizen in-app notification entity.
    
    Architecture Note:
    Stores scheme deadline alerts, status updates, and document verification reminders.
    External dispatch via Firebase Cloud Messaging is implemented in later phases.
    """
    __tablename__ = "notifications"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Primary UUID key for notification record",
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Recipient citizen user ID",
    )
    title = Column(
        String(200),
        nullable=False,
        comment="Notification subject / headline",
    )
    message = Column(
        Text,
        nullable=False,
        comment="Detailed notification content body",
    )
    notification_type = Column(
        String(50),
        nullable=False,
        default="system",
        index=True,
        comment="Category: scheme_alert, document_reminder, status_update, system",
    )
    scheduled_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Scheduled delivery timestamp (null for immediate)",
    )
    is_read = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Read receipt flag",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Notification creation timestamp",
    )

    # Relationships
    user = relationship("User", back_populates="notifications")

    def __repr__(self) -> str:
        return f"<Notification id={self.id} user_id={self.user_id} type='{self.notification_type}' read={self.is_read}>"

