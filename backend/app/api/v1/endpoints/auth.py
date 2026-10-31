from typing import Optional
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    SendOTPRequest,
    SendOTPResponse,
    VerifyOTPRequest,
    TokenResponse,
    RefreshTokenRequest,
    LogoutRequest,
    MessageResponse,
)
from app.schemas.user import UserResponse
from app.services.otp_service import OTPService
from app.services.auth_service import AuthService

router = APIRouter()


@router.post(
    "/send-otp",
    response_model=SendOTPResponse,
    status_code=status.HTTP_200_OK,
    summary="Request a mobile OTP for login or registration",
)
def send_otp(request_data: SendOTPRequest, db: Session = Depends(get_db)):
    """Generate and dispatch a numeric OTP to the citizen's mobile number.
    
    Enforces cooldown timers and maximum attempts.
    In development mode, returns dev_otp in the response for test automation without SMS fees.
    """
    challenge, dev_otp = OTPService.request_otp(db, request_data.mobile_number)
    return SendOTPResponse(
        status="success",
        message="OTP sent successfully.",
        mobile_number=challenge.mobile_number,
        expires_in_seconds=settings.OTP_EXPIRE_SECONDS,
        resend_cooldown_seconds=settings.OTP_RESEND_COOLDOWN_SECONDS,
        dev_otp=dev_otp,
    )


@router.post(
    "/register",
    response_model=SendOTPResponse,
    status_code=status.HTTP_200_OK,
    summary="Start registration process (initiates mobile OTP)",
)
def register(request_data: SendOTPRequest, db: Session = Depends(get_db)):
    """Start registration flow by sending OTP to the citizen mobile number."""
    challenge, dev_otp = OTPService.request_otp(db, request_data.mobile_number)
    return SendOTPResponse(
        status="success",
        message="Registration OTP generated and dispatched.",
        mobile_number=challenge.mobile_number,
        expires_in_seconds=settings.OTP_EXPIRE_SECONDS,
        resend_cooldown_seconds=settings.OTP_RESEND_COOLDOWN_SECONDS,
        dev_otp=dev_otp,
    )


@router.post(
    "/verify-otp",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify OTP, register new citizen or login existing citizen, and issue JWT tokens",
)
def verify_otp(
    request_data: VerifyOTPRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Verify citizen entered OTP, create account if not registered, and issue JWT + refresh token."""
    device_info = request.headers.get("User-Agent")
    ip_address = request.client.host if request.client else None

    return AuthService.authenticate_or_register(
        db=db,
        raw_mobile=request_data.mobile_number,
        entered_otp=request_data.otp,
        device_info=device_info,
        ip_address=ip_address,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token using secure refresh token rotation",
)
def refresh_token(
    request_data: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Rotate refresh token: invalidates used refresh token and issues a new access/refresh pair."""
    device_info = request.headers.get("User-Agent")
    ip_address = request.client.host if request.client else None

    return AuthService.refresh_session(
        db=db,
        raw_refresh_token=request_data.refresh_token,
        device_info=device_info,
        ip_address=ip_address,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke session and logout citizen",
)
def logout(
    request_data: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke active refresh token session for current user."""
    AuthService.revoke_session(
        db=db,
        user_id=str(current_user.id),
        raw_refresh_token=request_data.refresh_token,
        all_sessions=request_data.all_sessions,
    )
    return MessageResponse(
        status="success",
        message="Session revoked and logged out successfully.",
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated citizen user details",
)
def get_auth_me(current_user: User = Depends(get_current_user)):
    """Retrieve currently authenticated citizen identity."""
    return current_user

