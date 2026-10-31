import hmac
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
import httpx

from app.models.payment import PaymentTransaction, WebhookEvent
from app.models.subscription import Subscription
from app.schemas.payment import (
    RazorpayOrderResponse,
    PaymentVerificationResponse,
    PaymentTransactionResponse,
    PaymentHistoryResponse,
)
from app.services.subscription_service import SubscriptionService
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("janmitra.payment_service")

# Approved plan pricing:
# Monthly: ₹99.00 -> 9,900 paise
# Yearly:  ₹799.00 -> 79,900 paise
PLAN_PRICES_INR = {
    "monthly": 99.0,
    "yearly": 799.0,
}
PLAN_PRICES_PAISE = {
    "monthly": 9900,
    "yearly": 79900,
}


# SEC-10: Strict field allowlists for financial audit without customer PII
PAYMENT_ENTITY_ALLOWLIST = {
    "id", "order_id", "status", "amount", "currency",
    "method", "bank", "wallet", "international",
    "error_code", "error_description", "created_at"
}

REFUND_ENTITY_ALLOWLIST = {
    "id", "payment_id", "amount", "currency",
    "status", "speed_processed", "created_at"
}

DISPUTE_ENTITY_ALLOWLIST = {
    "id", "payment_id", "amount", "currency",
    "reason_code", "status", "created_at"
}


def _mask_string(value: Optional[str], visible_suffix: int = 4) -> Optional[str]:
    """Mask sensitive string, showing only trailing characters."""
    if not value or not isinstance(value, str):
        return value
    if len(value) <= visible_suffix:
        return "*" * len(value)
    return "*" * (len(value) - visible_suffix) + value[-visible_suffix:]


def _extract_safe_entity(entity: Dict[str, Any], allowlist: set) -> Dict[str, Any]:
    """Extract allowlisted financial fields and masked identifiers, omitting raw customer PII (SEC-10)."""
    if not isinstance(entity, dict):
        return {}
    result = {k: entity[k] for k in allowlist if k in entity and entity[k] is not None}
    for pii_key in ["contact", "email", "vpa"]:
        if pii_key in entity and entity[pii_key]:
            result[pii_key] = _mask_string(str(entity[pii_key]))
    return result


def _sanitize_payment_entity(entity: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize entity: combines allowlisting and legacy PII masking for backward compatibility."""
    if not isinstance(entity, dict):
        return {}
    return _extract_safe_entity(entity, PAYMENT_ENTITY_ALLOWLIST)


class PaymentService:
    """Orchestrates secure server-side Razorpay order creation, cryptographic
    signature verification, gateway-side payment validation, webhook idempotency,
    and payment audit history.
    """

    @classmethod
    def create_razorpay_order(
        cls,
        db: Session,
        user_id: uuid.UUID,
        plan_type: str,
        billing_cycle: str,
    ) -> RazorpayOrderResponse:
        """Create a secure Razorpay order and register a pending PaymentTransaction."""
        if plan_type.lower() != "premium":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only 'premium' plan orders can be processed for payment.",
            )

        cycle = billing_cycle.lower()
        if cycle not in PLAN_PRICES_PAISE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid billing cycle: '{billing_cycle}'. Must be 'monthly' or 'yearly'.",
            )

        amount_paise = PLAN_PRICES_PAISE[cycle]
        amount_inr = PLAN_PRICES_INR[cycle]
        currency = settings.RAZORPAY_CURRENCY

        # Create order via Razorpay API or deterministic server generator in dev mode
        if settings.RAZORPAY_DEV_MODE:
            order_id = f"order_dev_{uuid.uuid4().hex[:16]}"
            logger.info(f"Generated dev mode Razorpay order {order_id} for user {user_id}")
        else:
            try:
                # Production Razorpay API integration
                auth = (settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
                payload = {
                    "amount": amount_paise,
                    "currency": currency,
                    "receipt": f"rcpt_{uuid.uuid4().hex[:12]}",
                    "notes": {
                        "user_id": str(user_id),
                        "plan_type": plan_type,
                        "billing_cycle": cycle,
                    },
                }
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(
                        "https://api.razorpay.com/v1/orders",
                        auth=auth,
                        json=payload,
                    )
                    resp.raise_for_status()
                    order_data = resp.json()
                    order_id = order_data["id"]
            except Exception as e:
                logger.error(f"Razorpay order creation failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to initiate order with Razorpay: {str(e)}",
                )

        # Record transaction in database
        transaction = PaymentTransaction(
            id=uuid.uuid4(),
            user_id=user_id,
            subscription_id=None,
            razorpay_order_id=order_id,
            razorpay_payment_id=None,
            razorpay_signature=None,
            amount=amount_inr,
            currency=currency,
            plan_type="premium",
            billing_cycle=cycle,
            payment_status="created",
            payment_method=None,
            idempotency_key=f"idemp_{order_id}",
            payment_metadata={"initiated_at": str(uuid.uuid4())},
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)

        return RazorpayOrderResponse(
            order_id=order_id,
            amount=amount_paise,
            amount_inr=amount_inr,
            currency=currency,
            key_id=settings.RAZORPAY_KEY_ID,
            plan_type="premium",
            billing_cycle=cycle,
            is_dev_mode=settings.RAZORPAY_DEV_MODE,
        )

    @classmethod
    def verify_payment_signature(
        cls,
        order_id: str,
        payment_id: str,
        signature: str,
    ) -> bool:
        """Verify HMAC-SHA256 signature generated by Razorpay."""
        try:
            expected_payload = f"{order_id}|{payment_id}".encode("utf-8")
            secret = settings.RAZORPAY_KEY_SECRET.encode("utf-8")
            expected_sig = hmac.new(secret, expected_payload, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected_sig, signature)
        except Exception as e:
            logger.error(f"Signature computation error: {e}")
            return False

    @classmethod
    def verify_and_capture_payment(
        cls,
        db: Session,
        user_id: uuid.UUID,
        order_id: str,
        payment_id: str,
        signature: str,
        payment_method: Optional[str] = None,
    ) -> PaymentVerificationResponse:
        """Cryptographically verify payment, validate directly with Razorpay gateway,
        and activate Premium subscription.
        """
        # 1. Cryptographic signature verification
        is_valid = cls.verify_payment_signature(order_id, payment_id, signature)
        if not is_valid:
            logger.warning(
                f"Invalid payment signature for order {order_id}, payment {payment_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment signature verification failed. Untrusted payment payload rejected.",
            )

        # 2. Lookup transaction and check ownership (anti-IDOR) with pessimistic lock (SEC-04)
        tx = (
            db.query(PaymentTransaction)
            .filter(PaymentTransaction.razorpay_order_id == order_id)
            .with_for_update()
            .first()
        )
        if not tx:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order '{order_id}' not found.",
            )

        if tx.user_id != user_id:
            logger.warning(f"IDOR attempt: User {user_id} tried to verify order {order_id} of user {tx.user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to verify this transaction.",
            )

        # 3. Idempotent check
        if tx.payment_status in ["captured", "refunded"]:
            logger.info(f"Transaction {tx.id} already {tx.payment_status}. Returning idempotent success.")
            sub_resp = SubscriptionService.get_citizen_subscription_response(db, user_id)
            return PaymentVerificationResponse(
                success=True,
                message="Payment already confirmed and subscription is active.",
                transaction_id=tx.id,
                subscription=sub_resp,
            )

        # 4. Gateway-Side Status Verification (SEC-03)
        expected_amount_paise = PLAN_PRICES_PAISE[tx.billing_cycle]
        if not settings.RAZORPAY_DEV_MODE:
            try:
                auth = (settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
                with httpx.Client(timeout=10.0) as client:
                    resp = client.get(
                        f"https://api.razorpay.com/v1/payments/{payment_id}",
                        auth=auth,
                    )
                    resp.raise_for_status()
                    pay_data = resp.json()

                gateway_status = pay_data.get("status")
                gateway_amount = pay_data.get("amount")
                gateway_currency = pay_data.get("currency")
                gateway_order_id = pay_data.get("order_id")

                if gateway_status != "captured":
                    logger.warning(
                        f"Gateway verification rejected: payment {payment_id} status is '{gateway_status}'"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Gateway reported payment status is '{gateway_status}', expected 'captured'.",
                    )

                if gateway_amount != expected_amount_paise:
                    logger.warning(
                        f"Gateway verification rejected: amount mismatch ({gateway_amount} != {expected_amount_paise})"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Payment amount mismatch detected from gateway verification.",
                    )

                if gateway_currency != settings.RAZORPAY_CURRENCY:
                    logger.warning(
                        f"Gateway verification rejected: currency mismatch ({gateway_currency} != {settings.RAZORPAY_CURRENCY})"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Payment currency mismatch detected from gateway verification.",
                    )

                if gateway_order_id != order_id:
                    logger.warning(
                        f"Gateway verification rejected: order_id mismatch ({gateway_order_id} != {order_id})"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Payment order mismatch detected from gateway verification.",
                    )

                # Capture actual payment method from gateway if available
                if not payment_method and pay_data.get("method"):
                    payment_method = pay_data.get("method")

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Razorpay gateway verification error for payment {payment_id}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to verify payment status with Razorpay gateway: {str(e)}",
                )
        else:
            logger.info(
                f"[DEV MODE] Bypassing external Razorpay API check for payment {payment_id} on order {order_id}"
            )

        # 5. Activate Premium Subscription
        sub = SubscriptionService.activate_premium_subscription(
            db=db,
            user_id=user_id,
            billing_cycle=tx.billing_cycle,
            transaction_id=tx.id,
        )

        # 6. Update transaction state
        tx.razorpay_payment_id = payment_id
        tx.razorpay_signature = signature
        tx.payment_status = "captured"
        tx.subscription_id = sub.id
        if payment_method:
            tx.payment_method = payment_method.lower()
        db.commit()
        db.refresh(tx)

        sub_resp = SubscriptionService.get_citizen_subscription_response(db, user_id)
        return PaymentVerificationResponse(
            success=True,
            message="Payment successfully verified! JanMitra Premium activated.",
            transaction_id=tx.id,
            subscription=sub_resp,
        )

    @classmethod
    def verify_webhook_signature(
        cls,
        payload_bytes: bytes,
        signature_header: str,
    ) -> bool:
        """Verify Razorpay webhook HMAC-SHA256 signature."""
        try:
            secret = settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8")
            expected_sig = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()
            return hmac.compare_digest(expected_sig, signature_header)
        except Exception as e:
            logger.error(f"Webhook signature calculation error: {e}")
            return False

    @classmethod
    def process_webhook(
        cls,
        db: Session,
        payload: Dict[str, Any],
        raw_body: bytes,
        signature_header: str,
    ) -> Dict[str, Any]:
        """Process incoming Razorpay webhook with signature verification,
        idempotent event tracking (SEC-04), row-level pessimistic locking,
        refund handling (SEC-07), and PII sanitization (SEC-10).
        """
        # 1. Verify webhook signature
        if not cls.verify_webhook_signature(raw_body, signature_header):
            logger.warning("Rejected webhook with invalid signature")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Razorpay webhook signature.",
            )

        event = payload.get("event", "")
        event_id = payload.get("event_id") or payload.get("id")
        logger.info(f"Processing Razorpay webhook event: {event} (event_id: {event_id})")

        # 2. Webhook Deduplication Check (SEC-04)
        if event_id:
            existing_event = (
                db.query(WebhookEvent)
                .filter(WebhookEvent.event_id == event_id)
                .first()
            )
            if existing_event:
                logger.info(f"Duplicate webhook event {event_id} already processed. Returning idempotent response.")
                return {
                    "status": "idempotent_duplicate",
                    "event_id": event_id,
                    "event": event,
                }

        # 3. Extract entities (payment, refund, order, dispute)
        payment_entity = (
            payload.get("payload", {})
            .get("payment", {})
            .get("entity", {})
        )
        refund_entity = (
            payload.get("payload", {})
            .get("refund", {})
            .get("entity", {})
        )
        order_entity = (
            payload.get("payload", {})
            .get("order", {})
            .get("entity", {})
        )
        dispute_entity = (
            payload.get("payload", {})
            .get("dispute", {})
            .get("entity", {})
        )

        order_id = payment_entity.get("order_id") or order_entity.get("id")
        payment_id = payment_entity.get("id") or refund_entity.get("payment_id") or dispute_entity.get("payment_id")

        # 4. Lookup transaction with pessimistic row lock (SEC-04)
        query = db.query(PaymentTransaction).with_for_update()
        if order_id:
            tx = query.filter(PaymentTransaction.razorpay_order_id == order_id).first()
        elif payment_id:
            tx = query.filter(PaymentTransaction.razorpay_payment_id == payment_id).first()
        else:
            tx = None

        if not tx:
            logger.warning(f"Webhook received for unknown transaction: order_id={order_id}, payment_id={payment_id}")
            return {"status": "ignored", "reason": "Transaction not found"}

        # 5. Handle webhook events
        result_status = "unhandled_event"

        if event in ["payment.captured", "order.paid"]:
            if tx.payment_status == "captured":
                logger.info(f"Duplicate webhook: Transaction {tx.id} already captured.")
                result_status = "idempotent_success"
            else:
                # Capture payment and activate subscription
                sub = SubscriptionService.activate_premium_subscription(
                    db=db,
                    user_id=tx.user_id,
                    billing_cycle=tx.billing_cycle,
                    transaction_id=tx.id,
                )
                tx.razorpay_payment_id = payment_id or tx.razorpay_payment_id
                tx.payment_status = "captured"
                tx.subscription_id = sub.id
                tx.payment_method = payment_entity.get("method", tx.payment_method)
                tx.payment_metadata = {
                    "webhook_event": event,
                    "payload": _extract_safe_entity(payment_entity, PAYMENT_ENTITY_ALLOWLIST),
                }
                result_status = "captured"

        elif event == "payment.failed":
            tx.payment_status = "failed"
            tx.error_code = payment_entity.get("error_code")
            tx.error_description = payment_entity.get("error_description")
            tx.payment_metadata = {
                "webhook_event": event,
                "payload": _extract_safe_entity(payment_entity, PAYMENT_ENTITY_ALLOWLIST),
            }
            result_status = "failed"

        elif event in ["refund.processed", "refund.created"]:
            # SEC-07: Cumulative refund handling & tracking
            refund_id = refund_entity.get("id") or f"rfnd_{uuid.uuid4().hex[:12]}"
            refund_amt_paise = refund_entity.get("amount", 0)
            refund_amt_inr = round(float(refund_amt_paise) / 100.0, 2)

            # Record in refunds_log to prevent double counting on duplicate/retry events
            current_log = dict(tx.refunds_log or {})
            current_log[refund_id] = {
                "amount_paise": refund_amt_paise,
                "amount_inr": refund_amt_inr,
                "event": event,
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }
            tx.refunds_log = current_log

            # Calculate total cumulative refund
            total_refunded_inr = round(sum(float(r["amount_inr"]) for r in current_log.values()), 2)
            tx.amount_refunded = total_refunded_inr
            full_amount_inr = float(tx.amount)

            sanitized_refund = _extract_safe_entity(refund_entity, REFUND_ENTITY_ALLOWLIST)

            if total_refunded_inr >= full_amount_inr:
                # Cumulative full refund: revoke active subscription
                tx.payment_status = "refunded"
                if tx.subscription_id:
                    sub = (
                        db.query(Subscription)
                        .filter(Subscription.id == tx.subscription_id)
                        .first()
                    )
                    if sub:
                        sub.status = "refunded"
                        sub.is_active = False
                        sub.end_date = datetime.now(timezone.utc)
                        logger.info(f"Full refund reached ({total_refunded_inr} >= {full_amount_inr}): Revoked subscription {sub.id} for user {tx.user_id}")

                tx.payment_metadata = {
                    **(tx.payment_metadata or {}),
                    "webhook_event": event,
                    "refund_type": "full",
                    "total_refunded_inr": total_refunded_inr,
                    "refund_payload": sanitized_refund,
                }
                result_status = "refunded_full"
            else:
                # Cumulative partial refund: retain active subscription
                tx.payment_status = "partially_refunded"
                tx.payment_metadata = {
                    **(tx.payment_metadata or {}),
                    "webhook_event": event,
                    "refund_type": "partial",
                    "total_refunded_inr": total_refunded_inr,
                    "refund_payload": sanitized_refund,
                }
                logger.info(
                    f"Cumulative partial refund of {total_refunded_inr} INR recorded for tx {tx.id}. Subscription retained."
                )
                result_status = "refunded_partial"

        elif event == "payment.dispute.created":
            tx.dispute_status = "created"
            tx.payment_metadata = {
                **(tx.payment_metadata or {}),
                "webhook_event": event,
                "dispute_payload": _extract_safe_entity(dispute_entity, DISPUTE_ENTITY_ALLOWLIST),
            }
            result_status = "dispute_created"
            logger.warning(f"Payment dispute created for transaction {tx.id}")

        elif event == "payment.dispute.under_review":
            tx.dispute_status = "under_review"
            tx.payment_metadata = {
                **(tx.payment_metadata or {}),
                "webhook_event": event,
                "dispute_payload": _extract_safe_entity(dispute_entity, DISPUTE_ENTITY_ALLOWLIST),
            }
            result_status = "dispute_under_review"

        elif event == "payment.dispute.won":
            tx.dispute_status = "won"
            tx.payment_metadata = {
                **(tx.payment_metadata or {}),
                "webhook_event": event,
                "dispute_payload": _extract_safe_entity(dispute_entity, DISPUTE_ENTITY_ALLOWLIST),
            }
            result_status = "dispute_won"
            logger.info(f"Payment dispute won for transaction {tx.id}")

        elif event == "payment.dispute.lost":
            tx.dispute_status = "lost"
            tx.payment_status = "refunded"
            if tx.subscription_id:
                sub = (
                    db.query(Subscription)
                    .filter(Subscription.id == tx.subscription_id)
                    .first()
                )
                if sub:
                    sub.status = "revoked_chargeback"
                    sub.is_active = False
                    sub.end_date = datetime.now(timezone.utc)
                    logger.info(f"Dispute lost: Revoked subscription {sub.id} due to bank chargeback.")
            tx.payment_metadata = {
                **(tx.payment_metadata or {}),
                "webhook_event": event,
                "dispute_payload": _extract_safe_entity(dispute_entity, DISPUTE_ENTITY_ALLOWLIST),
            }
            result_status = "dispute_lost"

        elif event == "payment.dispute.closed":
            tx.dispute_status = "closed"
            tx.payment_metadata = {
                **(tx.payment_metadata or {}),
                "webhook_event": event,
            }
            result_status = "dispute_closed"

        # 6. Record processed WebhookEvent for deduplication (SEC-04)
        if event_id:
            wh_record = WebhookEvent(
                id=uuid.uuid4(),
                event_id=event_id,
                event_type=event,
                order_id=tx.razorpay_order_id,
                payment_id=payment_id or tx.razorpay_payment_id,
                status=result_status,
                payload_summary={
                    "event": event,
                    "amount": payment_entity.get("amount") or refund_entity.get("amount") or dispute_entity.get("amount"),
                    "currency": payment_entity.get("currency") or refund_entity.get("currency") or dispute_entity.get("currency"),
                    "method": payment_entity.get("method"),
                    "status": result_status,
                },
            )
            db.add(wh_record)

        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            logger.info(f"Concurrent duplicate webhook event {event_id} caught by unique constraint.")
            return {
                "status": "idempotent_duplicate",
                "event_id": event_id,
                "event": event,
            }
        return {"status": result_status, "transaction_id": str(tx.id), "event": event}

    @classmethod
    def get_user_payment_history(
        cls,
        db: Session,
        user_id: uuid.UUID,
    ) -> PaymentHistoryResponse:
        """Return citizen's chronological payment transactions."""
        txs = (
            db.query(PaymentTransaction)
            .filter(PaymentTransaction.user_id == user_id)
            .order_by(PaymentTransaction.created_at.desc())
            .all()
        )

        items = [
            PaymentTransactionResponse(
                id=t.id,
                razorpay_order_id=t.razorpay_order_id,
                razorpay_payment_id=t.razorpay_payment_id,
                amount=float(t.amount),
                currency=t.currency,
                plan_type=t.plan_type,
                billing_cycle=t.billing_cycle,
                payment_status=t.payment_status,
                amount_refunded=float(t.amount_refunded or 0.0),
                dispute_status=t.dispute_status or "none",
                payment_method=t.payment_method,
                error_code=t.error_code,
                error_description=t.error_description,
                created_at=t.created_at,
            )
            for t in txs
        ]
        return PaymentHistoryResponse(total=len(items), items=items)
