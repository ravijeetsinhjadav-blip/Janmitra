from datetime import date, datetime
from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, ConfigDict


class UserProfileBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=150, description="Citizen's legal full name")
    date_of_birth: date = Field(..., description="Date of birth in YYYY-MM-DD format")
    state: str = Field(..., min_length=2, max_length=100, description="State / UT of residence")
    district: str = Field(..., min_length=2, max_length=100, description="District of residence")
    residence_type: Literal["rural", "urban"] = Field("rural", description="'rural' or 'urban'")
    annual_family_income: Optional[float] = Field(None, ge=0, description="Annual family income in INR")
    occupation: Optional[str] = Field(None, max_length=100, description="Citizen occupation")
    education_level: Optional[str] = Field(None, max_length=100, description="Highest education completed")

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Date of birth cannot be in the future")
        if (date.today().year - v.year) > 130:
            raise ValueError("Invalid date of birth")
        return v


class UserProfileCreate(UserProfileBase):
    pass


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=150)
    date_of_birth: Optional[date] = None
    state: Optional[str] = Field(None, min_length=2, max_length=100)
    district: Optional[str] = Field(None, min_length=2, max_length=100)
    residence_type: Optional[Literal["rural", "urban"]] = None
    annual_family_income: Optional[float] = Field(None, ge=0)
    occupation: Optional[str] = Field(None, max_length=100)
    education_level: Optional[str] = Field(None, max_length=100)


class UserProfileResponse(UserProfileBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    id: UUID
    role: str
    mobile_number: Optional[str] = None
    email: Optional[str] = None
    has_password: Optional[bool] = False
    is_active: bool
    created_at: datetime
    profile: Optional[UserProfileResponse] = None

    model_config = ConfigDict(from_attributes=True)


class AccountDeletionCreate(BaseModel):
    reason: Optional[str] = Field(None, max_length=1000, description="Reason for requesting account deletion")


class AccountDeletionResponse(BaseModel):
    status: str = "pending"
    message: str
    request_id: UUID
    requested_at: datetime
    scheduled_for: datetime
