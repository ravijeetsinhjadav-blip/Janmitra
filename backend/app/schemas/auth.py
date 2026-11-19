from typing import Optional
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator
from app.core.security import validate_password_strength


class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="Citizen's primary email address")
    password: str = Field(..., min_length=8, max_length=128, description="Strong password")
    confirm_password: str = Field(..., min_length=8, max_length=128, description="Confirmation password")
    full_name: str = Field(..., min_length=2, max_length=150, description="Citizen full name")
    mobile_number: Optional[str] = Field(None, description="Optional contact mobile number")

    @field_validator("password")
    @classmethod
    def check_password_complexity(cls, v: str) -> str:
        validate_password_strength(v)
        return v

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., min_length=1, description="Password")


class SetCredentialsRequest(BaseModel):
    email: EmailStr = Field(..., description="New email address to link")
    password: str = Field(..., min_length=8, max_length=128, description="New strong password")
    confirm_password: str = Field(..., min_length=8, max_length=128, description="Confirmation password")

    @field_validator("password")
    @classmethod
    def check_password_complexity(cls, v: str) -> str:
        validate_password_strength(v)
        return v

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    is_new_user: bool = False
    user_id: str
    email: Optional[str] = None
    role: str
    profile_completed: bool = False
    csrf_token: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    refresh_token: Optional[str] = Field(None, description="Valid refresh token for session rotation (optional if provided via cookie)")


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = Field(None, description="Specific refresh token to revoke (optional if provided via cookie)")
    all_sessions: bool = Field(False, description="Whether to revoke all active sessions for user")


class MessageResponse(BaseModel):
    status: str = "success"
    message: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered email address")


class ForgotPasswordResponse(BaseModel):
    status: str = "success"
    message: str = "If an account with that email exists, password reset instructions have been sent."


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=16, description="Cryptographic password reset token from email link")
    password: str = Field(..., min_length=8, max_length=128, description="New strong password")
    confirm_password: str = Field(..., min_length=8, max_length=128, description="Confirmation of new password")

    @field_validator("password")
    @classmethod
    def check_password_complexity(cls, v: str) -> str:
        validate_password_strength(v)
        return v

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class ResetPasswordResponse(BaseModel):
    status: str = "success"
    message: str = "Password has been successfully updated. Please sign in with your new password."
