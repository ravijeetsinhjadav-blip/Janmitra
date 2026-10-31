import uuid
from sqlalchemy import Column, String, Integer, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class OTPChallenge(Base):
    """OTP Verification Challenge Entity.
    
    Security & Privacy Rules:
    1. Raw OTPs are NEVER stored. Only the cryptographic hash (SHA-256) is persisted.
    2. Enforces attempt counters, expiration timestamp, and resend cooldown.
    3. Generic errors returned on failures to prevent enumeration.
    """
    __tablename__ = "otp_challenges"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Primary UUID key for OTP challenge",
    )
    mobile_number = Column(
        String(20),
        nullable=False,
        index=True,
        comment="Normalized mobile number receiving the challenge",
    )
    hashed_otp = Column(
        String(255),
        nullable=False,
        comment="Cryptographic SHA-256 hash of the generated OTP",
    )
    purpose = Column(
        String(50),
        nullable=False,
        default="auth",
        comment="Challenge intent: auth, login, register",
    )
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="Expiration timestamp after which OTP is rejected",
    )
    attempts = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Count of verification attempts made against this challenge",
    )
    max_attempts = Column(
        Integer,
        nullable=False,
        default=3,
        comment="Maximum permitted verification attempts before challenge lockout",
    )
    is_verified = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Flag indicating whether challenge was successfully consumed",
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Challenge creation timestamp",
    )

    def __repr__(self) -> str:
        return f"<OTPChallenge id={self.id} mobile={self.mobile_number} verified={self.is_verified}>"

