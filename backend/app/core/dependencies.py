import hmac
from typing import Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency to extract and authenticate current user from Bearer JWT or HttpOnly session cookie.
    
    1. If an 'Authorization: Bearer <token>' header is present (mobile/API clients), it is authenticated directly.
    2. If no Bearer header is present, falls back to the HttpOnly 'access_token_cookie' (browser clients).
       For cookie-authenticated state-changing requests (POST, PUT, PATCH, DELETE), validates the 'X-CSRF-Token' header
       against the 'csrf_token_cookie'.
    3. Raises 401 Unauthorized if missing, expired, or invalid.
    4. Raises 403 Forbidden if CSRF token is missing/invalid, or if the user account is deactivated.
    """
    token: Optional[str] = None
    is_cookie_auth = False

    if credentials and credentials.credentials:
        token = credentials.credentials
    else:
        cookie_token = request.cookies.get("access_token_cookie")
        if cookie_token:
            token = cookie_token
            is_cookie_auth = True

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a Bearer access token or sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # If authenticated via browser cookie, enforce CSRF protection on mutating methods
    if is_cookie_auth and request.method in ("POST", "PUT", "PATCH", "DELETE"):
        csrf_header = request.headers.get("x-csrf-token")
        csrf_cookie = request.cookies.get("csrf_token_cookie")
        if not csrf_header or not csrf_cookie or not hmac.compare_digest(csrf_header, csrf_cookie):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF validation failed: Missing or invalid X-CSRF-Token header.",
            )

    payload = decode_access_token(token)
    user_id_str = payload.get("sub")

    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_uuid = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed user identifier in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_uuid).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account was removed",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    return user


def get_current_active_citizen(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency verifying that the caller is an active citizen or admin."""
    if current_user.role not in ("citizen", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Citizen privileges required.",
        )
    return current_user


def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency enforcing administrator-only access.
    
    Protects administrative routes from unauthorized citizen access.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required.",
        )
    return current_user

