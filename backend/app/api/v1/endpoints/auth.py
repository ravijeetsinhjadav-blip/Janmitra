import hmac
import secrets
from fastapi import APIRouter, Depends, Request, Response, status, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    SetCredentialsRequest,
    TokenResponse,
    RefreshTokenRequest,
    LogoutRequest,
    MessageResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter()


def _is_secure_request(request: Request) -> bool:
    return settings.ENVIRONMENT == "production" or request.url.scheme == "https"


def _set_auth_cookies(response: Response, request: Request, access_token: str, refresh_token: str, csrf_token: str):
    is_secure = _is_secure_request(request)
    response.set_cookie(
        key="access_token_cookie",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=is_secure,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token_cookie",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=is_secure,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth",
    )
    response.set_cookie(
        key="csrf_token_cookie",
        value=csrf_token,
        httponly=False,
        samesite="lax",
        secure=is_secure,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/",
    )


def _clear_auth_cookies(response: Response):
    response.delete_cookie("access_token_cookie", path="/")
    response.delete_cookie("refresh_token_cookie", path="/api/v1/auth")
    response.delete_cookie("csrf_token_cookie", path="/")


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new citizen account with Email and Password",
    description="Registers a citizen with email, password, and name. Role is strictly assigned as 'citizen'. Sets HttpOnly session cookies.",
)
def register(
    request_data: RegisterRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Register citizen with email and password, returning JWT tokens and setting secure browser cookies."""
    device_info = request.headers.get("User-Agent")
    ip_address = request.client.host if request.client else None

    result = AuthService.register_citizen(
        db=db,
        request_data=request_data,
        device_info=device_info,
        ip_address=ip_address,
    )
    csrf_token = secrets.token_urlsafe(32)
    _set_auth_cookies(response, request, result.access_token, result.refresh_token, csrf_token)
    result.csrf_token = csrf_token
    return result


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate citizen or admin using Email and Password",
    description="Validates credentials, returns JWT tokens, and sets secure HttpOnly cookies with CSRF token.",
)
def login(
    request_data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Login with email and password, setting secure HttpOnly browser cookies."""
    device_info = request.headers.get("User-Agent")
    ip_address = request.client.host if request.client else None

    result = AuthService.login(
        db=db,
        request_data=request_data,
        device_info=device_info,
        ip_address=ip_address,
    )
    csrf_token = secrets.token_urlsafe(32)
    _set_auth_cookies(response, request, result.access_token, result.refresh_token, csrf_token)
    result.csrf_token = csrf_token
    return result


@router.post(
    "/set-credentials",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Set or update email and password for an authenticated session",
    description="Enables existing authenticated sessions to establish or change their email and password.",
)
def set_credentials(
    request_data: SetCredentialsRequest,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Link or update email and password for the currently authenticated user."""
    device_info = request.headers.get("User-Agent")
    ip_address = request.client.host if request.client else None

    result = AuthService.set_credentials(
        db=db,
        current_user=current_user,
        request_data=request_data,
        device_info=device_info,
        ip_address=ip_address,
    )
    csrf_token = secrets.token_urlsafe(32)
    _set_auth_cookies(response, request, result.access_token, result.refresh_token, csrf_token)
    result.csrf_token = csrf_token
    return result


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token using secure refresh token rotation",
)
def refresh_token(
    request_data: RefreshTokenRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Rotate refresh token: accepts refresh token from request body or HttpOnly cookie."""
    raw_refresh = request_data.refresh_token or request.cookies.get("refresh_token_cookie")
    if not raw_refresh:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token required in body or via refresh_token_cookie.",
        )

    # If refresh token came from cookie, enforce CSRF protection
    if not request_data.refresh_token and request.cookies.get("refresh_token_cookie"):
        csrf_header = request.headers.get("x-csrf-token")
        csrf_cookie = request.cookies.get("csrf_token_cookie")
        if not csrf_header or not csrf_cookie or not hmac.compare_digest(csrf_header, csrf_cookie):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF validation failed on session refresh: Missing or invalid X-CSRF-Token header.",
            )

    device_info = request.headers.get("User-Agent")
    ip_address = request.client.host if request.client else None

    result = AuthService.refresh_session(
        db=db,
        raw_refresh_token=raw_refresh,
        device_info=device_info,
        ip_address=ip_address,
    )
    new_csrf_token = secrets.token_urlsafe(32)
    _set_auth_cookies(response, request, result.access_token, result.refresh_token, new_csrf_token)
    result.csrf_token = new_csrf_token
    return result


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke session and logout user",
)
def logout(
    request_data: LogoutRequest,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke active refresh token session for current user and clear browser cookies."""
    raw_refresh = request_data.refresh_token or request.cookies.get("refresh_token_cookie")

    AuthService.revoke_session(
        db=db,
        user_id=str(current_user.id),
        raw_refresh_token=raw_refresh,
        all_sessions=request_data.all_sessions,
    )
    _clear_auth_cookies(response)
    return MessageResponse(
        status="success",
        message="Session revoked and logged out successfully.",
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated citizen or admin user details",
)
def get_auth_me(current_user: User = Depends(get_current_user)):
    """Retrieve currently authenticated identity."""
    return current_user


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Request a secure password reset link via email",
    description="Generates a single-use time-limited reset token and sends an email. Returns generic response to prevent account enumeration.",
)
def forgot_password(
    request_data: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Initiate password recovery for registered email."""
    client_ip = request.client.host if request.client else None
    return AuthService.forgot_password(
        db=db,
        email=request_data.email,
        client_ip=client_ip,
    )


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset password using a verified single-use reset token",
    description="Validates the reset token, updates the password with Argon2id hash, invalidates the token, and revokes all active sessions.",
)
def reset_password(
    request_data: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Complete password reset using email reset token."""
    client_ip = request.client.host if request.client else None
    return AuthService.reset_password(
        db=db,
        token=request_data.token,
        new_password=request_data.password,
        client_ip=client_ip,
    )
