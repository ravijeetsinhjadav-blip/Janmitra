import uuid
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class AdminLoginRequest(BaseModel):
    mobile_number: str = Field(..., description="Admin mobile number")
    otp: str = Field(..., min_length=6, max_length=6, description="OTP code")


class AdminStatsResponse(BaseModel):
    total_citizens: int
    active_citizens: int
    total_schemes: int
    active_schemes: int
    total_applications: int
    applications_by_status: Dict[str, int]
    total_documents: int
    ocr_completed_documents: int
    manual_review_documents: int
    total_assessments: int
    total_active_premium_subscriptions: int
    total_payments_captured: int
    total_free_users: int = 0
    total_premium_users: int = 0
    active_subscriptions: int = 0
    expired_subscriptions: int = 0
    cancelled_subscriptions: int = 0
    total_revenue_inr: float = 0.0
    system_status: str = "operational"


class AdminUserListItem(BaseModel):
    id: uuid.UUID
    mobile_number: Optional[str] = None
    email: Optional[str] = None
    role: str
    is_active: bool
    full_name: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminUserListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    users: List[AdminUserListItem]


class AdminUserDetailResponse(BaseModel):
    id: uuid.UUID
    mobile_number: Optional[str] = None
    email: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    profile: Optional[Dict[str, Any]] = None
    documents_count: int
    applications_count: int
    subscription_plan: str
    subscription_active: bool


class AdminUserStatusUpdate(BaseModel):
    is_active: bool


class AdminSchemeCreate(BaseModel):
    scheme_name: str = Field(..., min_length=3, max_length=255)
    category: str = Field(..., min_length=2, max_length=100)
    department: str = Field(..., min_length=2, max_length=200)
    description: str = Field(..., min_length=10)
    short_description: Optional[str] = None
    state_applicability: str = "All India"
    eligibility_summary: str = Field(..., min_length=5)
    official_source_url: str = Field(..., min_length=5, max_length=500)
    official_application_url: str = Field(..., min_length=5, max_length=500)
    benefits: List[str] = Field(default_factory=list)
    eligibility_criteria: List[Dict[str, Any]] = Field(default_factory=list)
    required_profile_fields: List[str] = Field(default_factory=list)
    required_documents: List[str] = Field(default_factory=list)
    application_process: List[str] = Field(default_factory=list)
    source_verification_details: Optional[str] = None
    is_demo_data: bool = False


class AdminSchemeUpdate(BaseModel):
    scheme_name: Optional[str] = None
    category: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    state_applicability: Optional[str] = None
    eligibility_summary: Optional[str] = None
    official_source_url: Optional[str] = None
    official_application_url: Optional[str] = None
    benefits: Optional[List[str]] = None
    eligibility_criteria: Optional[List[Dict[str, Any]]] = None
    required_documents: Optional[List[str]] = None
    source_freshness_status: Optional[str] = None
    source_verification_details: Optional[str] = None
    is_active: Optional[bool] = None


class AdminApplicationListItem(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    scheme_id: uuid.UUID
    scheme_name: str
    category: Optional[str] = None
    status: str
    application_reference_number: Optional[str] = None
    submission_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    source_qualification: str = "Citizen Reported"


class AdminApplicationListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    applications: List[AdminApplicationListItem]
    status_summary: Dict[str, int]
    disclaimer: str = (
        "Application statuses monitored here reflect manual tracking entries logged by citizens. "
        "JanMitra Assist does not issue official government approvals or rejections."
    )


class AdminSubscriptionListItem(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    citizen_name: Optional[str] = None
    mobile_number: Optional[str] = None
    plan_type: str
    billing_cycle: Optional[str] = None
    status: str
    start_date: datetime
    end_date: Optional[datetime] = None
    days_remaining: Optional[int] = None
    created_at: datetime


class AdminSubscriptionListResponse(BaseModel):
    total: int
    items: List[AdminSubscriptionListItem]
    page: int = 1
    page_size: int = 20
    total_pages: int = 1


class AdminPaymentListItem(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    citizen_name: Optional[str] = None
    mobile_number: Optional[str] = None
    razorpay_order_id: str
    razorpay_payment_id: Optional[str] = None
    amount: float
    currency: str = "INR"
    plan_type: str = "premium"
    billing_cycle: str
    payment_status: str
    payment_method: Optional[str] = None
    error_description: Optional[str] = None
    created_at: datetime


class AdminPaymentListResponse(BaseModel):
    total: int
    items: List[AdminPaymentListItem]
    page: int = 1
    page_size: int = 20
    total_pages: int = 1
