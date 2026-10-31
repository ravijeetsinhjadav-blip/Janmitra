import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Union
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.security import (
    hash_token,
    generate_secure_random_token,
    normalize_mobile_number,
    create_access_token,
    ensure_utc,
)
from app.models.user import User
from app.models.session import UserSession
from app.schemas.auth import TokenResponse
from app.services.otp_service import OTPService


class AuthService:
    """Authentication service orchestrating OTP verification, citizen provisioning, and JWT sessions."""

    @staticmethod
    def authenticate_or_register(
        db: Session,
        raw_mobile: str,
        entered_otp: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> TokenResponse:
        # 1. Verify OTP challenge
        OTPService.verify_otp(db, raw_mobile, entered_otp)

        # 2. Find or create citizen user
        mobile = normalize_mobile_number(raw_mobile)
        user = db.query(User).filter(User.mobile_number == mobile).first()
        is_new_user = False

        if not user:
            # Public registration automatically receives citizen role; cannot self-assign admin
            user = User(
                mobile_number=mobile,
                role="citizen",
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            is_new_user = True

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This citizen account has been deactivated. Please contact support.",
            )

        profile_completed = bool(user.profile)

        # 3. Generate Access Token & Refresh Token
        access_token = create_access_token(user_id=str(user.id), role=user.role)
        raw_refresh_token = generate_secure_random_token(32)
        token_hash = hash_token(raw_refresh_token)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        session_record = UserSession(
            user_id=user.id,
            token_hash=token_hash,
            device_info=device_info,
            ip_address=ip_address,
            expires_at=expires_at,
            is_revoked=False,
        )
        db.add(session_record)
        db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            is_new_user=is_new_user,
            user_id=str(user.id),
            role=user.role,
            profile_completed=profile_completed,
        )

    @staticmethod
    def refresh_session(
        db: Session,
        raw_refresh_token: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> TokenResponse:
        token_hash = hash_token(raw_refresh_token)
        now = datetime.now(timezone.utc)

        # Find active session by token hash
        session_record = (
            db.query(UserSession)
            .filter(
                UserSession.token_hash == token_hash,
                UserSession.is_revoked == False,
            )
            .first()
        )

        if not session_record or now > ensure_utc(session_record.expires_at):
            if session_record:
                session_record.is_revoked = True
                db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is invalid or expired. Please sign in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = db.query(User).filter(User.id == session_record.user_id).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account inactive or not found.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Secure Token Rotation: Revoke previous refresh token
        session_record.is_revoked = True

        # Generate new pair
        new_access_token = create_access_token(user_id=str(user.id), role=user.role)
        new_raw_refresh_token = generate_secure_random_token(32)
        new_token_hash = hash_token(new_raw_refresh_token)

        new_expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        new_session = UserSession(
            user_id=user.id,
            token_hash=new_token_hash,
            device_info=device_info or session_record.device_info,
            ip_address=ip_address or session_record.ip_address,
            expires_at=new_expires_at,
            is_revoked=False,
        )
        db.add(new_session)
        db.commit()

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_raw_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            is_new_user=False,
            user_id=str(user.id),
            role=user.role,
            profile_completed=bool(user.profile),
        )

    @staticmethod
    def revoke_session(
        db: Session,
        user_id: Union[str, uuid.UUID],
        raw_refresh_token: Optional[str] = None,
        all_sessions: bool = False,
    ) -> None:
        target_uid = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
        if all_sessions:
            db.query(UserSession).filter(
                UserSession.user_id == target_uid,
                UserSession.is_revoked == False,
            ).update({"is_revoked": True})
        elif raw_refresh_token:
            token_hash = hash_token(raw_refresh_token)
            session_record = (
                db.query(UserSession)
                .filter(
                    UserSession.user_id == target_uid,
                    UserSession.token_hash == token_hash,
                )
                .first()
            )
            if session_record:
                session_record.is_revoked = True
        db.commit()
