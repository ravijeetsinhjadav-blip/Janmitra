import hmac
import hashlib
import json
import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User
from app.models.profile import UserProfile
from app.models.subscription import Subscription
from app.models.payment import PaymentTransaction
from app.models.document import DocumentMetadata, DocumentProcessingStatus
from app.models.assessment import Assessment
from app.models.scheme import Scheme
from app.core.config import settings
from app.core.dependencies import get_db, get_current_active_citizen
from app.services.subscription_service import SubscriptionService
from app.services.payment_service import PaymentService


@pytest.fixture
def auth_citizen(db_session: Session) -> User:
    """Fixture providing an authenticated citizen."""
    user = User(
        id=uuid.uuid4(),
        role="citizen",
        mobile_number=f"98{uuid.uuid4().int % 100000000:08d}",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    profile = UserProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        full_name="Rajesh Patel",
        date_of_birth=datetime(1985, 6, 15).date(),
        state="Gujarat",
        district="Ahmedabad",
        residence_type="rural",
        annual_family_income=120000.0,
        occupation="Small Farmer",
        education_level="Secondary",
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def client_for_user(db_session: Session, auth_citizen: User):
    """TestClient overriding get_db and get_current_active_citizen with auth_citizen."""
    def override_get_db():
        yield db_session

    def override_citizen():
        return auth_citizen

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_citizen] = override_citizen
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class TestSubscriptionPlansAndQuotas:
    """Tests for subscription plan definitions, quota status, and enforcement."""

    def test_get_subscription_plans_catalog(self, client_for_user: TestClient):
        response = client_for_user.get("/api/v1/subscriptions/plans")
        assert response.status_code == 200
        data = response.json()
        assert "plans" in data
        assert len(data["plans"]) == 2

        free_plan = next(p for p in data["plans"] if p["plan_type"] == "free")
        assert free_plan["price_monthly"] == 0.0
        assert free_plan["doc_analyses_limit"] == 3
        assert free_plan["ai_guidance_limit"] == 5

        premium_plan = next(p for p in data["plans"] if p["plan_type"] == "premium")
        assert premium_plan["price_monthly"] == 99.0
        assert premium_plan["price_yearly"] == 799.0
        assert premium_plan["doc_analyses_limit"] == 30
        assert premium_plan["ai_guidance_limit"] == 100

    def test_get_my_subscription_defaults_to_active_free(self, client_for_user: TestClient):
        response = client_for_user.get("/api/v1/subscriptions/me")
        assert response.status_code == 200
        data = response.json()
        assert data["plan_type"] == "free"
        assert data["status"] == "active"
        assert data["is_active"] is True
        assert data["usage"]["ai_document_analyses_used"] == 0
        assert data["usage"]["ai_document_analyses_limit"] == 3
        assert data["usage"]["ai_guidance_sessions_used"] == 0
        assert data["usage"]["ai_guidance_sessions_limit"] == 5
        assert data["usage"]["can_analyze_document"] is True
        assert data["usage"]["can_request_guidance"] is True

    def test_free_tier_document_quota_enforcement(
        self, client_for_user: TestClient, db_session: Session, auth_citizen: User
    ):
        # Insert 3 uploaded documents in current month
        now = datetime.now(timezone.utc)
        for i in range(3):
            doc = DocumentMetadata(
                id=uuid.uuid4(),
                user_id=auth_citizen.id,
                document_type="income_certificate",
                original_filename=f"income_{i}.pdf",
                storage_reference=f"storage/income_{i}.pdf",
                mime_type="application/pdf",
                file_size=1024,
                ocr_status=DocumentProcessingStatus.OCR_COMPLETED,
                created_at=now,
            )
            db_session.add(doc)
        db_session.commit()

        # Check quota status endpoint
        sub_resp = client_for_user.get("/api/v1/subscriptions/me").json()
        assert sub_resp["usage"]["ai_document_analyses_used"] == 3
        assert sub_resp["usage"]["can_analyze_document"] is False

        # Attempt 4th upload via upload endpoint
        files = {"file": ("test.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"mock", "image/png")}
        data = {"document_type": "caste_certificate"}
        upload_resp = client_for_user.post("/api/v1/documents/upload", files=files, data=data)
        assert upload_resp.status_code == 403
        assert "quota reached" in upload_resp.json()["detail"].lower()
        assert "upgrade to janmitra premium" in upload_resp.json()["detail"].lower()

    def test_free_tier_guidance_quota_enforcement(
        self, client_for_user: TestClient, db_session: Session, auth_citizen: User
    ):
        now = datetime.now(timezone.utc)
        # Create a mock scheme
        scheme = Scheme(
            id=uuid.uuid4(),
            scheme_name="Test Welfare Scheme",
            description="Scheme for quota testing",
            department="Dept of Social Welfare",
            state_applicability="All India",
            eligibility_summary="Citizens below ₹2L",
            official_source_url="https://myscheme.gov.in/",
            official_application_url="https://myscheme.gov.in/",
            is_active=True,
            is_demo_data=True,
        )
        db_session.add(scheme)
        db_session.flush()

        # Insert 5 advisory assessments in current month
        for i in range(5):
            assess = Assessment(
                id=uuid.uuid4(),
                user_id=auth_citizen.id,
                scheme_id=scheme.id,
                assessment_type="scheme_eligibility",
                result_data={"overall_status": "Potentially Eligible"},
                overall_readiness_score=80.0,
                advisory_guidance={"summary": f"Guidance session {i}"},
                created_at=now,
            )
            db_session.add(assess)
        db_session.commit()

        # Check quota status
        sub_resp = client_for_user.get("/api/v1/subscriptions/me").json()
        assert sub_resp["usage"]["ai_guidance_sessions_used"] == 5
        assert sub_resp["usage"]["can_request_guidance"] is False

        # Attempt 6th advisory session
        adv_resp = client_for_user.post(
            f"/api/v1/advisory/schemes/{scheme.id}/assess-and-advise",
            json={"language": "en"},
        )
        assert adv_resp.status_code == 403
        assert "quota reached" in adv_resp.json()["detail"].lower()

    def test_expired_subscription_reverts_to_free_tier(
        self, client_for_user: TestClient, db_session: Session, auth_citizen: User
    ):
        # Create an expired premium subscription
        past_end = datetime.now(timezone.utc) - timedelta(days=2)
        past_start = past_end - timedelta(days=30)
        expired_sub = Subscription(
            id=uuid.uuid4(),
            user_id=auth_citizen.id,
            plan_type="premium",
            billing_cycle="monthly",
            status="active",  # Marked active in DB but end_date is past
            start_date=past_start,
            end_date=past_end,
        )
        db_session.add(expired_sub)
        db_session.commit()

        # Calling /subscriptions/me should automatically expire it and return free tier
        resp = client_for_user.get("/api/v1/subscriptions/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan_type"] == "free"

        # Verify DB updated to expired
        db_session.refresh(expired_sub)
        assert expired_sub.status == "expired"


class TestRazorpayPaymentsModule:
    """Tests for order creation, HMAC signature verification, webhooks, and history."""

    def test_create_razorpay_order_monthly_and_yearly(self, client_for_user: TestClient):
        # Monthly order (₹99 -> 9900 paise)
        resp_m = client_for_user.post(
            "/api/v1/payments/create-order",
            json={"plan_type": "premium", "billing_cycle": "monthly"},
        )
        assert resp_m.status_code == 201
        data_m = resp_m.json()
        assert data_m["amount"] == 9900
        assert data_m["amount_inr"] == 99.0
        assert data_m["billing_cycle"] == "monthly"
        assert data_m["order_id"].startswith("order_")
        assert data_m["key_id"] == settings.RAZORPAY_KEY_ID

        # Yearly order (₹799 -> 79900 paise)
        resp_y = client_for_user.post(
            "/api/v1/payments/create-order",
            json={"plan_type": "premium", "billing_cycle": "yearly"},
        )
        assert resp_y.status_code == 201
        data_y = resp_y.json()
        assert data_y["amount"] == 79900
        assert data_y["amount_inr"] == 799.0
        assert data_y["billing_cycle"] == "yearly"

    def test_create_order_invalid_inputs_rejected(self, client_for_user: TestClient):
        # Invalid plan type
        resp_plan = client_for_user.post(
            "/api/v1/payments/create-order",
            json={"plan_type": "free", "billing_cycle": "monthly"},
        )
        assert resp_plan.status_code == 400

        # Invalid billing cycle
        resp_cycle = client_for_user.post(
            "/api/v1/payments/create-order",
            json={"plan_type": "premium", "billing_cycle": "weekly"},
        )
        assert resp_cycle.status_code == 400

    def test_verify_payment_success_and_subscription_activation(
        self, client_for_user: TestClient, db_session: Session, auth_citizen: User
    ):
        # 1. Create order
        order_res = client_for_user.post(
            "/api/v1/payments/create-order",
            json={"plan_type": "premium", "billing_cycle": "monthly"},
        ).json()
        order_id = order_res["order_id"]
        payment_id = f"pay_{uuid.uuid4().hex[:14]}"

        # 2. Generate authentic HMAC signature
        payload_bytes = f"{order_id}|{payment_id}".encode("utf-8")
        secret = settings.RAZORPAY_KEY_SECRET.encode("utf-8")
        signature = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()

        # 3. Verify payment
        verify_res = client_for_user.post(
            "/api/v1/payments/verify",
            json={
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
                "payment_method": "upi",
            },
        )
        assert verify_res.status_code == 200
        data = verify_res.json()
        assert data["success"] is True
        assert data["subscription"]["plan_type"] == "premium"
        assert data["subscription"]["is_active"] is True
        assert data["subscription"]["billing_cycle"] == "monthly"
        assert data["subscription"]["usage"]["ai_document_analyses_limit"] == 30

        # 4. Idempotent re-verify check
        re_verify = client_for_user.post(
            "/api/v1/payments/verify",
            json={
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            },
        )
        assert re_verify.status_code == 200
        assert re_verify.json()["success"] is True

    def test_verify_payment_invalid_signature_rejected(self, client_for_user: TestClient):
        order_res = client_for_user.post(
            "/api/v1/payments/create-order",
            json={"plan_type": "premium", "billing_cycle": "monthly"},
        ).json()
        order_id = order_res["order_id"]

        tampered_sig = "invalid_tampered_hmac_signature_hex_code_12345"
        verify_res = client_for_user.post(
            "/api/v1/payments/verify",
            json={
                "razorpay_order_id": order_id,
                "razorpay_payment_id": "pay_fake123",
                "razorpay_signature": tampered_sig,
            },
        )
        assert verify_res.status_code == 400
        assert "signature verification failed" in verify_res.json()["detail"].lower()

    def test_webhook_payment_captured_and_idempotency(
        self, client_for_user: TestClient, db_session: Session, auth_citizen: User
    ):
        # Create order
        order_res = client_for_user.post(
            "/api/v1/payments/create-order",
            json={"plan_type": "premium", "billing_cycle": "yearly"},
        ).json()
        order_id = order_res["order_id"]
        payment_id = f"pay_{uuid.uuid4().hex[:14]}"

        webhook_body = json.dumps({
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": payment_id,
                        "order_id": order_id,
                        "amount": 79900,
                        "currency": "INR",
                        "status": "captured",
                        "method": "card",
                    }
                }
            }
        })
        raw_bytes = webhook_body.encode("utf-8")

        # Generate authentic webhook signature
        wh_secret = settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8")
        wh_signature = hmac.new(wh_secret, raw_bytes, hashlib.sha256).hexdigest()

        # Send webhook
        wh_resp = client_for_user.post(
            "/api/v1/payments/webhook",
            content=raw_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": wh_signature,
            },
        )
        assert wh_resp.status_code == 200
        assert wh_resp.json()["status"] == "captured"

        # Check citizen subscription is now Premium yearly
        sub_resp = client_for_user.get("/api/v1/subscriptions/me").json()
        assert sub_resp["plan_type"] == "premium"
        assert sub_resp["billing_cycle"] == "yearly"
        assert sub_resp["days_remaining"] >= 360

        # Duplicate webhook replay should be handled safely and idempotently
        dup_resp = client_for_user.post(
            "/api/v1/payments/webhook",
            content=raw_bytes,
            headers={
                "Content-Type": "application/json",
                "X-Razorpay-Signature": wh_signature,
            },
        )
        assert dup_resp.status_code == 200
        assert dup_resp.json()["status"] == "idempotent_success"

    def test_webhook_payment_failed_event(
        self, client_for_user: TestClient, db_session: Session, auth_citizen: User
    ):
        order_res = client_for_user.post(
            "/api/v1/payments/create-order",
            json={"plan_type": "premium", "billing_cycle": "monthly"},
        ).json()
        order_id = order_res["order_id"]

        webhook_body = json.dumps({
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": f"pay_{uuid.uuid4().hex[:14]}",
                        "order_id": order_id,
                        "status": "failed",
                        "error_code": "BAD_REQUEST_ERROR",
                        "error_description": "Payment was cancelled by the user",
                    }
                }
            }
        })
        raw_bytes = webhook_body.encode("utf-8")
        wh_signature = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), raw_bytes, hashlib.sha256
        ).hexdigest()

        wh_resp = client_for_user.post(
            "/api/v1/payments/webhook",
            content=raw_bytes,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": wh_signature},
        )
        assert wh_resp.status_code == 200
        assert wh_resp.json()["status"] == "failed"

        # Transaction in DB should be marked failed
        tx = db_session.query(PaymentTransaction).filter_by(razorpay_order_id=order_id).first()
        assert tx.payment_status == "failed"
        assert tx.error_code == "BAD_REQUEST_ERROR"

    def test_webhook_invalid_signature_rejected(self, client_for_user: TestClient):
        wh_resp = client_for_user.post(
            "/api/v1/payments/webhook",
            content=b'{"event": "payment.captured"}',
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": "invalid_sig"},
        )
        assert wh_resp.status_code == 400
        assert "invalid razorpay webhook signature" in wh_resp.json()["detail"].lower()

    def test_payment_history_retrieval_and_isolation(
        self, client_for_user: TestClient, db_session: Session, auth_citizen: User
    ):
        # Create orders
        client_for_user.post(
            "/api/v1/payments/create-order",
            json={"plan_type": "premium", "billing_cycle": "monthly"},
        )
        client_for_user.post(
            "/api/v1/payments/create-order",
            json={"plan_type": "premium", "billing_cycle": "yearly"},
        )

        # Another citizen creates an order
        other_user = User(id=uuid.uuid4(), role="citizen", mobile_number="9999988888")
        db_session.add(other_user)
        db_session.commit()
        other_tx = PaymentTransaction(
            id=uuid.uuid4(),
            user_id=other_user.id,
            razorpay_order_id="order_other_citizen_123",
            amount=99.0,
            currency="INR",
            plan_type="premium",
            billing_cycle="monthly",
            payment_status="created",
        )
        db_session.add(other_tx)
        db_session.commit()

        # Fetch history for current citizen
        hist_resp = client_for_user.get("/api/v1/payments/history")
        assert hist_resp.status_code == 200
        data = hist_resp.json()
        assert data["total"] == 2
        order_ids = [item["razorpay_order_id"] for item in data["items"]]
        assert "order_other_citizen_123" not in order_ids

    def test_idor_unauthorized_order_verification_blocked(
        self, client_for_user: TestClient, db_session: Session, auth_citizen: User
    ):
        # Create an order belonging to another citizen
        other_user = User(id=uuid.uuid4(), role="citizen", mobile_number="9999977777")
        db_session.add(other_user)
        db_session.commit()

        order_id = "order_belonging_to_other_citizen"
        other_tx = PaymentTransaction(
            id=uuid.uuid4(),
            user_id=other_user.id,
            razorpay_order_id=order_id,
            amount=99.0,
            currency="INR",
            plan_type="premium",
            billing_cycle="monthly",
            payment_status="created",
        )
        db_session.add(other_tx)
        db_session.commit()

        payment_id = "pay_test_idor_attempt"
        payload_bytes = f"{order_id}|{payment_id}".encode("utf-8")
        signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode("utf-8"), payload_bytes, hashlib.sha256
        ).hexdigest()

        # Auth citizen attempts to verify other user's order
        verify_resp = client_for_user.post(
            "/api/v1/payments/verify",
            json={
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            },
        )
        assert verify_resp.status_code == 403
        assert "permission" in verify_resp.json()["detail"].lower()
