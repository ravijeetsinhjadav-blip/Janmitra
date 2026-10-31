from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_citizen
from app.models.user import User
from app.schemas.subscription import (
    SubscriptionPlansResponse,
    CitizenSubscriptionResponse,
)
from app.services.subscription_service import SubscriptionService

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.get(
    "/plans",
    response_model=SubscriptionPlansResponse,
    status_code=status.HTTP_200_OK,
    summary="Get available subscription plans",
    description="Returns public catalog of subscription tiers (Free vs Premium), pricing, and feature quotas.",
)
def get_subscription_plans():
    """Retrieve official JanMitra subscription plans."""
    return SubscriptionService.get_plans_catalog()


@router.get(
    "/me",
    response_model=CitizenSubscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get citizen's active subscription and usage quotas",
    description="Returns authenticated citizen's current subscription tier, active status, expiration, and monthly quota usage.",
)
def get_my_subscription(
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Retrieve authenticated citizen's subscription status."""
    return SubscriptionService.get_citizen_subscription_response(
        db=db,
        user_id=current_user.id,
    )
