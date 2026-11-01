import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, AliasPath, model_validator, field_validator

from app.models.application import APPLICATION_STATUSES


class ApplicationCreate(BaseModel):
    """Citizen request payload to register an application already submitted on an official portal.
    
    Status is intentionally omitted; all new tracking entries are initialized to 'Submitted'.
    Extra fields (such as user_id, status, id) are strictly forbidden.
    """
    model_config = ConfigDict(extra="forbid")

    scheme_id: uuid.UUID = Field(
        ...,
        description="Target government scheme UUID applied for on the official portal."
    )
    submission_date: datetime = Field(
        ...,
        description="Date and time when the application was formally submitted on the portal. Must include timezone offset."
    )
    application_reference_number: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Official acknowledgement / reference number issued by the portal."
    )
    reference_number_not_issued: bool = Field(
        default=False,
        description="Explicit request declaration confirming the portal did not issue a reference number."
    )

    @field_validator("submission_date")
    @classmethod
    def validate_submission_date(cls, v: datetime) -> datetime:
        # 1. Reject naive datetime inputs
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError(
                "Submission date must include timezone offset (e.g. '2026-11-01T10:00:00+05:30' or '2026-11-01T04:30:00Z'). "
                "Naive datetimes without timezone are rejected."
            )
        # 2. Normalize to UTC
        dt_utc = v.astimezone(timezone.utc)
        # 3. Future-date check with 5 minutes clock-skew tolerance
        now_utc = datetime.now(timezone.utc)
        if dt_utc > now_utc + timedelta(minutes=5):
            raise ValueError("Submission date cannot be in the future.")
        return dt_utc

    @model_validator(mode="after")
    def validate_reference_number_policy(self) -> "ApplicationCreate":
        ref = (self.application_reference_number or "").strip()
        if ref:
            if self.reference_number_not_issued:
                raise ValueError(
                    "Contradictory reference-number payload: "
                    "cannot provide an application_reference_number when 'reference_number_not_issued' is set to true."
                )
            self.application_reference_number = ref
        else:
            self.application_reference_number = None
            if not self.reference_number_not_issued:
                raise ValueError(
                    "Official application reference number is required. "
                    "If the government portal does not issue an acknowledgement number for this scheme, "
                    "you must explicitly set 'reference_number_not_issued' to true."
                )
        return self


class ApplicationUpdate(BaseModel):
    """Citizen request payload to update an existing application tracking record.
    
    Empty bodies, unknown fields, and explicit null values for status/submission_date are rejected with HTTP 422.
    Omitted fields remain completely unchanged.
    """
    model_config = ConfigDict(extra="forbid")

    status: Optional[str] = None
    application_reference_number: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Official acknowledgement / reference number issued by the portal."
    )
    clear_reference_number: bool = False
    submission_date: Optional[datetime] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            raise ValueError("Status cannot be null.")
        val = v.strip()
        if val not in APPLICATION_STATUSES:
            raise ValueError(
                f"Invalid status '{val}'. Allowed statuses are: {', '.join(APPLICATION_STATUSES)}"
            )
        return val

    @field_validator("submission_date")
    @classmethod
    def validate_submission_date(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is None:
            raise ValueError("Submission date cannot be null.")
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError(
                "Submission date must include timezone offset (e.g. '2026-11-01T10:00:00+05:30' or '2026-11-01T04:30:00Z'). "
                "Naive datetimes without timezone are rejected."
            )
        dt_utc = v.astimezone(timezone.utc)
        now_utc = datetime.now(timezone.utc)
        if dt_utc > now_utc + timedelta(minutes=5):
            raise ValueError("Submission date cannot be in the future.")
        return dt_utc

    @model_validator(mode="after")
    def validate_patch_semantics(self) -> "ApplicationUpdate":
        fields = self.model_fields_set
        # 1. Reject empty PATCH payload ({})
        if not fields:
            raise ValueError("PATCH payload cannot be empty. At least one field must be provided for update.")

        # 2. clear_reference_number alone is not a valid substantive update
        substantive = {"status", "application_reference_number", "submission_date"}
        if not any(f in fields for f in substantive):
            raise ValueError("PATCH payload must contain at least one updateable attribute.")

        # 3. Reference number clearing and whitespace normalization rules
        if "application_reference_number" in fields:
            ref = (self.application_reference_number or "").strip()
            if ref:
                # Reference number is non-empty after stripping
                if self.clear_reference_number:
                    raise ValueError(
                        "Cannot provide both a non-empty application_reference_number and clear_reference_number=true."
                    )
                self.application_reference_number = ref
            else:
                # Reference number is null, empty string, or whitespace-only
                if not self.clear_reference_number:
                    raise ValueError(
                        "Cannot clear application_reference_number without explicitly providing clear_reference_number=true."
                    )
                self.application_reference_number = None
        else:
            # application_reference_number was not provided in the payload
            if self.clear_reference_number:
                raise ValueError(
                    "clear_reference_number=true is valid only when application_reference_number is explicitly included in the payload."
                )

        return self


class ApplicationResponse(BaseModel):
    """Response object representing a citizen's tracked application with eager-loaded scheme metadata."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    scheme_id: uuid.UUID
    scheme_name: str = Field(
        ...,
        validation_alias=AliasPath("scheme", "scheme_name"),
        description="Official name of the applied government scheme."
    )
    category: Optional[str] = Field(
        default=None,
        validation_alias=AliasPath("scheme", "category"),
        description="Sector category of the scheme."
    )
    department: Optional[str] = Field(
        default=None,
        validation_alias=AliasPath("scheme", "department"),
        description="Nodal government department or ministry."
    )
    official_application_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasPath("scheme", "official_application_url"),
        description="Official online government portal URL for application submission and tracking."
    )
    application_reference_number: Optional[str] = None
    submission_date: Optional[datetime] = None
    status: str
    created_at: datetime
    updated_at: datetime


class ApplicationListResponse(BaseModel):
    """Paginated collection of citizen application tracking records."""
    total: int
    page: int
    page_size: int
    total_pages: int
    applications: List[ApplicationResponse]


class ApplicationDeleteResponse(BaseModel):
    """Confirmation response upon removing a local tracking record."""
    id: uuid.UUID
    message: str = (
        "Local tracking entry deleted successfully. Please note: This action only removes "
        "the tracking record from JanMitra Assist. It does NOT withdraw, cancel, or modify "
        "your formal application on the official government portal."
    )

