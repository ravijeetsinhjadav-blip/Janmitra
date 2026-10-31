from uuid import UUID
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class SubscriptionPlanItem(BaseModel):
    """Details for a single subscription tier."""
    plan_type: str = Field(..., description="Plan identifier: free or premium")
    name: str = Field(..., description="Plan display title")
    description: str = Field(..., description="Short plan summary")
    price_monthly: float = Field(default=0.0, description="Monthly price in INR")
    price_yearly: float = Field(default=0.0, description="Yearly price in INR")
    currency: str = Field(default="INR", description="Currency symbol/code")
    features: List[str] = Field(default_factory=list, description="List of entitlements included")
    doc_analyses_limit: int = Field(..., description="Monthly limit of AI document OCR extractions")
    ai_guidance_limit: int = Field(..., description="Monthly limit of personalized AI guidance sessions")
    is_popular: bool = Field(default=False, description="Flag for UI highlighting")


class SubscriptionPlansResponse(BaseModel):
    """Response containing available subscription plans."""
    plans: List[SubscriptionPlanItem]
    disclaimer: str = (
        "Subscription fees support platform intelligence and AI advisory services. "
        "Subscription does not constitute government application fees or guarantee scheme approval."
    )


class UsageQuotaStatus(BaseModel):
    """Citizen's current monthly usage counters and remaining limits."""
    ai_document_analyses_used: int = 0
    ai_document_analyses_limit: int = 3
    ai_guidance_sessions_used: int = 0
    ai_guidance_sessions_limit: int = 5
    can_analyze_document: bool = True
    can_request_guidance: bool = True
    quota_reset_date: datetime


class CitizenSubscriptionResponse(BaseModel):
    """Current subscription and quota status of authenticated citizen."""
    user_id: UUID
    plan_type: str = "free"
    billing_cycle: Optional[str] = None
    status: str = "active"
    is_active: bool = True
    start_date: datetime
    end_date: Optional[datetime] = None
    days_remaining: Optional[int] = None
    usage: UsageQuotaStatus
    disclaimer: str = (
        "JanMitra Assist subscription provides application preparation and AI guidance. "
        "It does not submit government applications on your behalf."
    )
