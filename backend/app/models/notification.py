import uuid
from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class Notification(Base):
    """Citizen in-app notification entity.
    
    Architecture Note:
    Stores scheme deadline alerts, status updates, and document verification reminders.
    Supports multi-channel delivery (in-app ledger and push via FCM).
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


class DeviceToken(Base):
    """Citizen mobile/web device token for Firebase Cloud Messaging (FCM) push dispatch."""
    __tablename__ = "device_tokens"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Primary UUID key for device token record",
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Citizen user ID owner",
    )
    device_token = Column(
        String(255),
        nullable=False,
        index=True,
        comment="FCM registration token issued by client SDK",
    )
    device_type = Column(
        String(20),
        nullable=False,
        default="android",
        comment="Device OS platform: android, ios, or web",
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Active delivery status (deactivated on logout or invalidation)",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Registration timestamp",
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Last token refresh / active timestamp",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "device_token", name="uq_device_tokens_user_token"),
    )

    # Relationships
    user = relationship("User", back_populates="device_tokens")

    def __repr__(self) -> str:
        return f"<DeviceToken id={self.id} user_id={self.user_id} type='{self.device_type}' active={self.is_active}>"
