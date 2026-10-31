import secrets
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logging import logger
from app.core.security import hash_token, generate_numeric_otp, normalize_mobile_number, ensure_utc
from app.models.otp import OTPChallenge


class BaseSMSProvider(ABC):
    """Abstract SMS Delivery Provider Interface."""

    @abstractmethod
    def send_otp(self, mobile_number: str, otp: str) -> bool:
        """Deliver OTP to recipient mobile number."""
        pass


class DevelopmentSMSAdapter(BaseSMSProvider):
    """Local Development SMS Adapter.
    
    Permits testing authentication flows locally without consuming paid SMS quotas.
    Security: In production, OTPs are never exposed or printed.
    """

    def send_otp(self, mobile_number: str, otp: str) -> bool:
        if settings.ENVIRONMENT == "development" or settings.OTP_DEV_MODE:
            logger.info(f"[DEV SMS ADAPTER] Generated OTP for {mobile_number[:6]}****")
        return True


class ProductionSMSAdapter(BaseSMSProvider):
    """Production SMS Gateway Adapter (Configurable placeholder for Twilio / Fast2SMS)."""

    def send_otp(self, mobile_number: str, otp: str) -> bool:
        logger.warning("Production SMS gateway not configured. Set SMS_PROVIDER credentials.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SMS service currently unconfigured for production delivery.",
        )


def get_sms_provider() -> BaseSMSProvider:
    """Factory to retrieve configured SMS delivery provider."""
    if settings.SMS_PROVIDER == "development" or settings.OTP_DEV_MODE:
        return DevelopmentSMSAdapter()
    return ProductionSMSAdapter()


class OTPService:
    """Service managing OTP challenge generation, rate limiting, and verification."""

    @staticmethod
    def request_otp(db: Session, raw_mobile: str) -> Tuple[OTPChallenge, Optional[str]]:
        mobile = normalize_mobile_number(raw_mobile)
        now = datetime.now(timezone.utc)

        # 1. Enforce Resend Cooldown
        latest_challenge = (
            db.query(OTPChallenge)
            .filter(OTPChallenge.mobile_number == mobile)
            .order_by(desc(OTPChallenge.created_at))
            .first()
        )

        if latest_challenge and latest_challenge.created_at:
            created_at_utc = ensure_utc(latest_challenge.created_at)
            elapsed = (now - created_at_utc).total_seconds()
            if elapsed < settings.OTP_RESEND_COOLDOWN_SECONDS:
                remaining = int(settings.OTP_RESEND_COOLDOWN_SECONDS - elapsed)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Please wait {remaining} seconds before requesting a new OTP.",
                )

        # 2. Generate cryptographically random OTP & hash it
        plain_otp = generate_numeric_otp(settings.OTP_LENGTH)
        hashed_otp = hash_token(plain_otp)
        expires_at = now + timedelta(seconds=settings.OTP_EXPIRE_SECONDS)

        # 3. Create persistent challenge
        challenge = OTPChallenge(
            mobile_number=mobile,
            hashed_otp=hashed_otp,
            purpose="auth",
            expires_at=expires_at,
            attempts=0,
            max_attempts=settings.OTP_MAX_ATTEMPTS,
            is_verified=False,
        )
        db.add(challenge)
        db.commit()
        db.refresh(challenge)

        # 4. Dispatch via SMS provider
        provider = get_sms_provider()
        provider.send_otp(mobile, plain_otp)

        # Only return plain_otp if dev mode is enabled
        dev_otp = plain_otp if settings.OTP_DEV_MODE else None
        return challenge, dev_otp

    @staticmethod
    def verify_otp(db: Session, raw_mobile: str, entered_otp: str) -> bool:
        mobile = normalize_mobile_number(raw_mobile)
        now = datetime.now(timezone.utc)

        # Find latest unverified challenge
        challenge = (
            db.query(OTPChallenge)
            .filter(
                OTPChallenge.mobile_number == mobile,
                OTPChallenge.is_verified == False,
            )
            .order_by(desc(OTPChallenge.created_at))
            .first()
        )

        if not challenge:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No pending OTP request found. Please request a new OTP.",
            )

        # Check expiration with ensure_utc
        expires_at_utc = ensure_utc(challenge.expires_at)
        if now > expires_at_utc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The OTP has expired. Please request a new one.",
            )

        # Check maximum attempts to prevent brute-force
        if challenge.attempts >= challenge.max_attempts:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many incorrect attempts. Challenge locked. Request a new OTP.",
            )

        # Increment attempt counter
        challenge.attempts += 1

        # Constant-time comparison of hashed OTP
        entered_hash = hash_token(entered_otp)
        if not secrets.compare_digest(entered_hash, challenge.hashed_otp):
            db.commit()
            remaining = challenge.max_attempts - challenge.attempts
            if remaining <= 0:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Maximum attempts reached. Please request a new OTP.",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid OTP. {remaining} attempt(s) remaining.",
            )

        # Mark challenge consumed
        challenge.is_verified = True
        db.commit()
        return True
