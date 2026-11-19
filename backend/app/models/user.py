import uuid
from sqlalchemy import Column, String, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, foreign
from app.core.database import Base


class User(Base):
    """User account entity.
    
    Serves as the root citizen or admin identity.
    Note: Password authentication is replaced with secure mobile OTP authentication in Phase 3.
    """
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Primary UUID key for the user",
    )
    role = Column(
        String(20),
        nullable=False,
        default="citizen",
        index=True,
        comment="Account role: citizen or admin",
    )
    email = Column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
        comment="Citizen email address (unique)",
    )
    password_hash = Column(
        String(255),
        nullable=True,
        comment="Argon2id or bcrypt password hash",
    )
    mobile_number = Column(
        String(20),
        unique=True,
        nullable=True,
        index=True,
        comment="Citizen mobile number (optional, unique when provided)",
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Flag indicating active account status",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when user was registered",
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Timestamp when user record was last modified",
    )

    # Relationships
    profile = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    documents = relationship(
        "DocumentMetadata",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    assessments = relationship(
        "Assessment",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    applications = relationship(
        "Application",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    application_reminders = relationship(
        "ApplicationReminder",
        back_populates="user",
        cascade="all, delete-orphan",
        primaryjoin="User.id == foreign(ApplicationReminder.user_id)",
        overlaps="application,reminders",
    )
    subscriptions = relationship(
        "Subscription",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    payments = relationship(
        "PaymentTransaction",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    device_tokens = relationship(
        "DeviceToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    sessions = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    deletion_requests = relationship(
        "AccountDeletionRequest",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @property
    def has_password(self) -> bool:
        return bool(self.password_hash)

    def __repr__(self) -> str:
        return f"<User id={self.id} role={self.role} mobile={self.mobile_number}>"
