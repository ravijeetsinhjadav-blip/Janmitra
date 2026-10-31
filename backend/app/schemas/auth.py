import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class SendOTPRequest(BaseModel):
    mobile_number: str = Field(..., description="10-digit Indian mobile number or with +91 prefix")

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        cleaned = "".join(ch for ch in v if ch.isdigit() or ch == "+")
        digits_only = "".join(ch for ch in cleaned if ch.isdigit())
        if len(digits_only) < 10:
            raise ValueError("Mobile number must contain at least 10 digits")
        if len(digits_only) == 10 and not digits_only.startswith(("6", "7", "8", "9")):
            raise ValueError("Invalid Indian mobile number prefix (must start with 6-9)")
        return v.strip()


class SendOTPResponse(BaseModel):
    status: str = "success"
    message: str
    mobile_number: str
    expires_in_seconds: int
    resend_cooldown_seconds: int
    dev_otp: Optional[str] = Field(
        None,
        description="Development-only OTP returned solely when OTP_DEV_MODE=True for testing without SMS charges",
    )


class VerifyOTPRequest(BaseModel):
    mobile_number: str = Field(..., description="Mobile number receiving the OTP")
    otp: str = Field(..., min_length=4, max_length=8, description="Numeric OTP entered by citizen")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    is_new_user: bool = False
    user_id: str
    role: str
    profile_completed: bool = False


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="Valid refresh token for session rotation")


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = Field(None, description="Specific refresh token to revoke")
    all_sessions: bool = Field(False, description="Whether to revoke all active sessions for user")


class MessageResponse(BaseModel):
    status: str = "success"
    message: str
