import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from fastapi import HTTPException, status
from app.core.config import settings


def ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime object is timezone-aware in UTC (supports SQLite and PostgreSQL)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def hash_token(token: str) -> str:
    """Compute SHA-256 hex digest of a token or OTP to avoid storing plaintext in database."""
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()


def generate_secure_random_token(nbytes: int = 32) -> str:
    """Generate a cryptographically secure random token string for refresh tokens."""
    return secrets.token_urlsafe(nbytes)


def generate_numeric_otp(length: int = 6) -> str:
    """Generate a cryptographically secure numeric OTP of specified length."""
    return "".join(secrets.choice("0123456789") for _ in range(length))


def normalize_mobile_number(mobile: str) -> str:
    """Normalize mobile number to standard 10-digit Indian format or clean international format."""
    cleaned = "".join(ch for ch in mobile if ch.isdigit() or ch == "+")
    if len(cleaned) == 10 and cleaned.isdigit():
        return f"+91{cleaned}"
    if cleaned.startswith("0") and len(cleaned) == 11:
        return f"+91{cleaned[1:]}"
    if not cleaned.startswith("+"):
        return f"+{cleaned}"
    return cleaned


def create_access_token(
    user_id: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generate a signed short-lived JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    encoded_jwt = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a signed JWT access token.
    
    Raises:
        HTTPException 401 if invalid, expired, or incorrect token type.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.InvalidTokenError, Exception):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
