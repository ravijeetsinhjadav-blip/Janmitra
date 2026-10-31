from typing import Dict, Any
from fastapi import APIRouter, Depends, Header, Request, status, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_citizen
from app.models.user import User
from app.schemas.payment import (
    RazorpayOrderCreateRequest,
    RazorpayOrderResponse,
    PaymentVerificationRequest,
    PaymentVerificationResponse,
    PaymentHistoryResponse,
)
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments & Checkout"])


@router.post(
    "/create-order",
    response_model=RazorpayOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create secure Razorpay order",
    description="Initiates an authenticated server-side order for JanMitra Premium subscription.",
)
def create_order(
    request: RazorpayOrderCreateRequest,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Create a new Razorpay checkout order."""
    return PaymentService.create_razorpay_order(
        db=db,
        user_id=current_user.id,
        plan_type=request.plan_type,
        billing_cycle=request.billing_cycle,
    )


@router.post(
    "/verify",
    response_model=PaymentVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify payment and activate Premium subscription",
    description="Verifies the cryptographic HMAC-SHA256 signature of the Razorpay checkout and upgrades citizen tier.",
)
def verify_payment(
    request: PaymentVerificationRequest,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Verify payment signature and activate subscription."""
    return PaymentService.verify_and_capture_payment(
        db=db,
        user_id=current_user.id,
        order_id=request.razorpay_order_id,
        payment_id=request.razorpay_payment_id,
        signature=request.razorpay_signature,
        payment_method=request.payment_method,
    )


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Razorpay server-to-server webhook endpoint",
    description="Handles Razorpay webhooks (payment.captured, payment.failed) with signature validation and idempotency.",
)
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(..., description="Razorpay cryptographic webhook signature"),
    db: Session = Depends(get_db),
):
    """Receive and process Razorpay webhook notifications."""
    raw_body = await request.body()
    try:
        import json
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON in webhook request body.",
        )

    return PaymentService.process_webhook(
        db=db,
        payload=payload,
        raw_body=raw_body,
        signature_header=x_razorpay_signature,
    )


@router.get(
    "/history",
    response_model=PaymentHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get citizen's payment transaction history",
    description="Returns chronological log of authenticated citizen's payment transactions.",
)
def get_payment_history(
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Retrieve payment history for current authenticated citizen."""
    return PaymentService.get_user_payment_history(
        db=db,
        user_id=current_user.id,
    )
