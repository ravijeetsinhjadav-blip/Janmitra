import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class PasswordResetToken(Base):
    """Password Reset Token Entity.
    
    Security Rules:
    1. Raw reset tokens are NEVER stored in the database. Only SHA-256 hashes are persisted.
    2. Tokens are strictly single-use: is_used=True is set upon successful password reset.
    3. Tokens expire after a short duration (configured via PASSWORD_RESET_TOKEN_EXPIRE_MINUTES, default 15m).
    4. Upon successful reset, all existing refresh sessions for the user are revoked.
    """
    __tablename__ = "password_reset_tokens"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Primary UUID key for password reset token",
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key referencing the user requesting password reset",
    )
    token_hash = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Cryptographic SHA-256 hash of the password reset token",
    )
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Timestamp when the reset token expires",
    )
    is_used = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Flag indicating whether token has already been consumed",
    )
    used_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when token was consumed",
    )
    ip_address = Column(
        String(50),
        nullable=True,
        comment="Client IP address where reset was requested",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when reset request was initiated",
    )

    user = relationship("User", backref="password_reset_tokens")

    def __repr__(self) -> str:
        return f"<PasswordResetToken id={self.id} user_id={self.user_id} is_used={self.is_used}>"

