import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Union
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.rate_limiter import rate_limiter
from app.core.security import (
    hash_password,
    verify_password,
    hash_token,
    generate_secure_random_token,
    create_access_token,
    ensure_utc,
    normalize_mobile_number,
)
from app.models.user import User
from app.models.profile import UserProfile
from app.models.session import UserSession
from app.models.password_reset import PasswordResetToken
from app.services.email_service import EmailService
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    SetCredentialsRequest,
    TokenResponse,
    ForgotPasswordResponse,
    ResetPasswordResponse,
)


class AuthService:
    """Authentication service orchestrating Email + Password authentication, sessions, and RBAC."""

    @staticmethod
    def register_citizen(
        db: Session,
        request_data: RegisterRequest,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> TokenResponse:
        """Register a new citizen with email and password.

        Public registration strictly assigns the 'citizen' role.
        """
        email_clean = str(request_data.email).strip().lower()

        # Check duplicate email
        existing_user = db.query(User).filter(User.email == email_clean).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email address already exists. Please log in.",
            )

        # Hash password securely using Argon2id (or bcrypt fallback)
        hashed_pw = hash_password(request_data.password)

        mobile_clean = normalize_mobile_number(request_data.mobile_number) if request_data.mobile_number else None
        if mobile_clean:
            existing_mobile = db.query(User).filter(User.mobile_number == mobile_clean).first()
            if existing_mobile:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="An account with this mobile number already exists.",
                )

        new_user = User(
            id=uuid.uuid4(),
            email=email_clean,
            password_hash=hashed_pw,
            mobile_number=mobile_clean,
            role="citizen",  # Public registration strictly creates citizens
            is_active=True,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # Issue access & refresh tokens
        return AuthService._create_session_tokens(
            db=db,
            user=new_user,
            is_new_user=True,
            device_info=device_info,
            ip_address=ip_address,
        )

    @staticmethod
    def login(
        db: Session,
        request_data: LoginRequest,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> TokenResponse:
        """Authenticate user (citizen or admin) with email and password with brute-force rate limiting."""
        email_clean = str(request_data.email).strip().lower()

        # Enforce rate limiting per account and per IP
        rate_limiter.check_rate_limit(
            action="login",
            identifier=email_clean,
            max_attempts=settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS,
            window_seconds=settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
        )
        if ip_address:
            rate_limiter.check_rate_limit(
                action="login_ip",
                identifier=ip_address,
                max_attempts=settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS * 3,
                window_seconds=settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
            )

        user = db.query(User).filter(User.email == email_clean).first()

        if not user or not user.password_hash or not verify_password(request_data.password, user.password_hash):
            rate_limiter.record_attempt(action="login", identifier=email_clean)
            if ip_address:
                rate_limiter.record_attempt(action="login_ip", identifier=ip_address)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account has been deactivated. Please contact support.",
            )

        # Clear login attempt counters on successful authentication
        rate_limiter.clear_attempts(action="login", identifier=email_clean)
        if ip_address:
            rate_limiter.clear_attempts(action="login_ip", identifier=ip_address)

        return AuthService._create_session_tokens(
            db=db,
            user=user,
            is_new_user=False,
            device_info=device_info,
            ip_address=ip_address,
        )

    @staticmethod
    def set_credentials(
        db: Session,
        current_user: User,
        request_data: SetCredentialsRequest,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> TokenResponse:
        """Allow an existing authenticated session (from legacy migration) to set email and password."""
        email_clean = str(request_data.email).strip().lower()

        # Ensure email is not claimed by another user
        conflict = (
            db.query(User)
            .filter(User.email == email_clean, User.id != current_user.id)
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email address is already in use by another account.",
            )

        current_user.email = email_clean
        current_user.password_hash = hash_password(request_data.password)
        db.commit()
        db.refresh(current_user)

        return AuthService._create_session_tokens(
            db=db,
            user=current_user,
            is_new_user=False,
            device_info=device_info,
            ip_address=ip_address,
        )

    @staticmethod
    def _create_session_tokens(
        db: Session,
        user: User,
        is_new_user: bool,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> TokenResponse:
        """Internal helper to create JWT access and refresh token session."""
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

        # Check if citizen profile is completed
        profile_completed = bool(user.profile and user.profile.state != "Default")

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            is_new_user=is_new_user,
            user_id=str(user.id),
            email=user.email,
            mobile_number=user.mobile_number,
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
        """Rotate refresh token: invalidate previous refresh token and issue a fresh pair."""
        token_hash = hash_token(raw_refresh_token)
        now = datetime.now(timezone.utc)

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

        # Invalidate old session
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

        profile_completed = bool(user.profile and user.profile.state != "Default")

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_raw_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            is_new_user=False,
            user_id=str(user.id),
            email=user.email,
            mobile_number=user.mobile_number,
            role=user.role,
            profile_completed=profile_completed,
        )

    @staticmethod
    def revoke_session(
        db: Session,
        user_id: Union[str, uuid.UUID],
        raw_refresh_token: Optional[str] = None,
        all_sessions: bool = False,
    ) -> None:
        """Revoke active user sessions."""
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

    @staticmethod
    def forgot_password(
        db: Session,
        email: str,
        client_ip: Optional[str] = None,
    ) -> ForgotPasswordResponse:
        """Process password reset request with rate limiting and secure single-use token generation."""
        email_clean = str(email).strip().lower()

        # Enforce rate limiting on password reset requests (per-account and per-IP)
        rate_limiter.check_rate_limit(
            action="forgot_password",
            identifier=email_clean,
            max_attempts=settings.PASSWORD_RESET_RATE_LIMIT_MAX_ATTEMPTS,
            window_seconds=settings.PASSWORD_RESET_RATE_LIMIT_WINDOW_SECONDS,
        )
        rate_limiter.record_attempt(action="forgot_password", identifier=email_clean)

        if client_ip:
            rate_limiter.check_rate_limit(
                action="forgot_password_ip",
                identifier=client_ip,
                max_attempts=settings.PASSWORD_RESET_RATE_LIMIT_MAX_ATTEMPTS * 3,
                window_seconds=settings.PASSWORD_RESET_RATE_LIMIT_WINDOW_SECONDS,
            )
            rate_limiter.record_attempt(action="forgot_password_ip", identifier=client_ip)

        user = db.query(User).filter(User.email == email_clean).first()

        # Generic response returned whether user exists or not (account enumeration protection)
        if not user or not user.is_active:
            return ForgotPasswordResponse(
                status="success",
                message="If an account with that email exists, password reset instructions have been sent.",
            )

        # Invalidate any existing unused reset tokens for this user
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.is_used == False,
        ).update({"is_used": True})

        # Generate cryptographically secure random token
        raw_token = generate_secure_random_token(32)
        token_hash = hash_token(raw_token)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)

        reset_record = PasswordResetToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_used=False,
            ip_address=client_ip,
        )
        db.add(reset_record)
        db.commit()

        # Construct single-use frontend reset link
        reset_link = f"{settings.FRONTEND_BASE_URL}/reset-password?token={raw_token}"
        recipient_name = user.profile.full_name if (user.profile and user.profile.full_name) else None

        # Dispatch email
        EmailService.send_password_reset_email(
            to_email=user.email,
            reset_link=reset_link,
            recipient_name=recipient_name,
        )

        return ForgotPasswordResponse(
            status="success",
            message="If an account with that email exists, password reset instructions have been sent.",
        )

    @staticmethod
    def reset_password(
        db: Session,
        token: str,
        new_password: str,
        client_ip: Optional[str] = None,
    ) -> ResetPasswordResponse:
        """Validate single-use reset token, update password hash, and revoke existing sessions."""
        rate_limiter.check_rate_limit(
            action="reset_password",
            identifier=client_ip or "global",
            max_attempts=10,
            window_seconds=300,
        )

        token_hash = hash_token(token)
        now = datetime.now(timezone.utc)

        token_record = (
            db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.is_used == False,
            )
            .first()
        )

        if not token_record or now > ensure_utc(token_record.expires_at):
            if token_record:
                token_record.is_used = True
                db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The password reset link is invalid or has expired.",
            )

        user = db.query(User).filter(User.id == token_record.user_id).first()
        if not user or not user.is_active:
            token_record.is_used = True
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is inactive or not found.",
            )

        # Update password hash
        user.password_hash = hash_password(new_password)

        # Invalidate reset token (single-use enforcement)
        token_record.is_used = True
        token_record.used_at = now

        # Revoke all existing sessions for this user upon password reset
        AuthService.revoke_session(db=db, user_id=user.id, all_sessions=True)

        db.commit()

        return ResetPasswordResponse(
            status="success",
            message="Password has been successfully updated. Please sign in with your new password.",
        )
