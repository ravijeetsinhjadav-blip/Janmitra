import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import jwt
from fastapi import HTTPException, status
from app.core.config import settings

# Initialize Argon2id password hasher with OWASP-recommended parameters
try:
    import argon2
    _argon2_hasher = argon2.PasswordHasher(
        time_cost=2,
        memory_cost=65536,
        parallelism=2,
        hash_len=32,
        type=argon2.Type.ID,
    )
except ImportError:
    _argon2_hasher = None

import bcrypt


def validate_password_strength(password: str) -> None:
    """Validate password against security policy.

    Requirements:
    - 8 to 128 characters long
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special symbol

    Raises:
        ValueError if password does not meet criteria.
    """
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if len(password) > 128:
        raise ValueError("Password must not exceed 128 characters")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]", password):
        raise ValueError("Password must contain at least one special symbol (!@#$%^&*()_+-=[]{}|;:,.<>?)")


def hash_password(password: str) -> str:
    """Hash password using Argon2id (primary) or bcrypt with SHA-256 pre-hashing (fallback)."""
    if _argon2_hasher is not None:
        return _argon2_hasher.hash(password)
    # Fallback to bcrypt with SHA-256 pre-hashing to bypass the 72-byte truncation limit
    pre_hashed = hashlib.sha256(password.encode("utf-8")).digest()
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pre_hashed, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against stored hash with support for Argon2id and bcrypt."""
    if not plain_password or not hashed_password:
        return False
    # Check if Argon2id hash
    if hashed_password.startswith("$argon2"):
        if _argon2_hasher is None:
            return False
        try:
            return _argon2_hasher.verify(hashed_password, plain_password)
        except (argon2.exceptions.VerifyMismatchError, argon2.exceptions.VerificationError, Exception):
            return False
    # Check if bcrypt hash
    if hashed_password.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            # First try direct verification
            if bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8")):
                return True
        except Exception:
            pass
        try:
            # Try pre-hashed verification
            pre_hashed = hashlib.sha256(plain_password.encode("utf-8")).digest()
            return bcrypt.checkpw(pre_hashed, hashed_password.encode("utf-8"))
        except Exception:
            return False
    return False


def ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime object is timezone-aware in UTC (supports SQLite and PostgreSQL)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def hash_token(token: str) -> str:
    """Compute SHA-256 hex digest of a token to avoid storing plaintext in database."""
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()


def generate_secure_random_token(nbytes: int = 32) -> str:
    """Generate a cryptographically secure random token string for refresh and password-reset tokens."""
    return secrets.token_urlsafe(nbytes)


def normalize_mobile_number(mobile: Optional[str]) -> Optional[str]:
    """Normalize mobile number to standard 10-digit Indian format or clean international format.
    
    Returns None if no valid mobile digits are provided, avoiding stray '+' or invalid values.
    """
    if not mobile:
        return None
    digits = "".join(ch for ch in mobile if ch.isdigit())
    if not digits or len(digits) < 10:
        return None
    if len(digits) == 10:
        return f"+91{digits}"
    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    if len(digits) == 11 and digits.startswith("0"):
        return f"+91{digits[1:]}"
    return f"+{digits}"


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
