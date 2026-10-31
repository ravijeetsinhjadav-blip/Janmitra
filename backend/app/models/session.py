import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class UserSession(Base):
    """User Session and Refresh Token Tracking Entity.
    
    Security Rules:
    1. Raw refresh tokens are never persisted in the database; only SHA-256 hashes are stored.
    2. Enforces refresh token rotation: old tokens are invalidated upon renewal.
    3. Logout sets is_revoked=True immediately.
    """
    __tablename__ = "user_sessions"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Primary UUID key for session record",
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Owner citizen user ID",
    )
    token_hash = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Cryptographic SHA-256 hash of the refresh token",
    )
    device_info = Column(
        String(255),
        nullable=True,
        comment="Client device metadata / User-Agent",
    )
    ip_address = Column(
        String(50),
        nullable=True,
        comment="Client IP address at issuance",
    )
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="Session expiration timestamp",
    )
    is_revoked = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Flag indicating if token session was explicitly revoked or refreshed",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Session issuance timestamp",
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Session modification timestamp",
    )

    # Relationships
    user = relationship("User", back_populates="sessions")

    def __repr__(self) -> str:
        return f"<UserSession id={self.id} user_id={self.user_id} revoked={self.is_revoked}>"

