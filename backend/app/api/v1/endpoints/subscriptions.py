from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_citizen
from app.models.user import User
from app.schemas.subscription import (
    SubscriptionPlansResponse,
    CitizenSubscriptionResponse,
    SubscriptionCancellationResponse,
    SubscriptionHistoryResponse,
    SubscriptionHistoryItem,
    FeatureAccessCheckResponse,
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


@router.post(
    "/cancel",
    response_model=SubscriptionCancellationResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel active Premium subscription",
    description="Cancels citizen's active Premium subscription and returns updated status.",
)
def cancel_my_subscription(
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Cancel citizen's active premium subscription with idempotent repeated support."""
    sub, was_already_cancelled = SubscriptionService.cancel_subscription(
        db=db, user_id=current_user.id
    )
    sub_response = SubscriptionService.get_citizen_subscription_response(
        db=db, user_id=current_user.id
    )
    message = (
        "Subscription is already cancelled. Citizen is on Free tier."
        if was_already_cancelled
        else "Premium subscription has been cancelled. Reverted to Free tier."
    )
    return SubscriptionCancellationResponse(
        success=True,
        message=message,
        subscription=sub_response,
    )


@router.get(
    "/history",
    response_model=SubscriptionHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get citizen's subscription history",
    description="Returns chronological ledger of all subscriptions, renewals, and cancellations for authenticated citizen.",
)
def get_subscription_history(
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Retrieve historical subscription logs for current citizen."""
    subs = SubscriptionService.get_subscription_history(db=db, user_id=current_user.id)
    items = [
        SubscriptionHistoryItem(
            id=s.id,
            plan_type=s.plan_type,
            billing_cycle=s.billing_cycle,
            status=s.status,
            start_date=s.start_date,
            end_date=s.end_date,
            created_at=s.created_at,
        )
        for s in subs
    ]
    return SubscriptionHistoryResponse(
        total=len(items),
        items=items,
    )


@router.get(
    "/features/check",
    response_model=FeatureAccessCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Check feature entitlement under current subscription tier",
    description="Verifies whether authenticated citizen is entitled to use a specific premium platform feature.",
)
def check_feature(
    feature: str = Query(..., description="Feature code (e.g. advanced_document_consistency, advanced_completeness_analysis)"),
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Query feature availability for the authenticated citizen."""
    res = SubscriptionService.check_feature_access(
        db=db, user_id=current_user.id, feature_name=feature
    )
    return FeatureAccessCheckResponse(
        feature=res["feature"],
        has_access=res["has_access"],
        plan_type=res["plan_type"],
        upgrade_required=res["upgrade_required"],
        message=res["message"],
    )
