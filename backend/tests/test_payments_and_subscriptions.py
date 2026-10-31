import hmac
import hashlib
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import httpx

from app.main import app
from app.models.user import User
from app.models.profile import UserProfile
from app.models.subscription import Subscription
from app.models.payment import PaymentTransaction, WebhookEvent
from app.models.document import DocumentMetadata, DocumentProcessingStatus
from app.models.assessment import Assessment
from app.models.scheme import Scheme
from app.core.config import Settings, settings
from app.core.dependencies import get_db, get_current_active_citizen
from app.services.subscription_service import SubscriptionService
from app.services.payment_service import PaymentService, _mask_string, _sanitize_payment_entity


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

    def test_quota_counting_excludes_ocr_failed_documents(
        self, db_session: Session, auth_citizen: User
    ):
        """SEC-05: Ensure OCR_FAILED documents are NOT counted towards citizen's monthly quota."""
        # 1 failed document
        doc_failed = DocumentMetadata(
            id=uuid.uuid4(),
            user_id=auth_citizen.id,
            document_type="income_certificate",
            original_filename="income_blurry.pdf",
            storage_reference="/vault/income_blurry.pdf",
            mime_type="application/pdf",
            file_size=1024,
            ocr_status=DocumentProcessingStatus.OCR_FAILED,
        )
        # 1 completed document
        doc_completed = DocumentMetadata(
            id=uuid.uuid4(),
            user_id=auth_citizen.id,
            document_type="aadhaar_card",
            original_filename="aadhaar_clear.pdf",
            storage_reference="/vault/aadhaar_clear.pdf",
            mime_type="application/pdf",
            file_size=2048,
            ocr_status=DocumentProcessingStatus.OCR_COMPLETED,
        )
        db_session.add_all([doc_failed, doc_completed])
        db_session.commit()

        quota = SubscriptionService.get_quota_status(db_session, auth_citizen.id)
        # Only 1 completed doc counted, 1 failed doc ignored
        assert quota.ai_document_analyses_used == 1
        assert quota.can_analyze_document is True

    def test_document_quota_enforcement_blocks_when_exceeded(
        self, db_session: Session, auth_citizen: User
    ):
        """Citizens exceeding free quota (3 docs) are blocked with 403 Forbidden."""
        for i in range(3):
            doc = DocumentMetadata(
                id=uuid.uuid4(),
                user_id=auth_citizen.id,
                document_type=f"doc_{i}",
                original_filename=f"doc_{i}.pdf",
                storage_reference=f"/vault/doc_{i}.pdf",
                mime_type="application/pdf",
                file_size=1000,
                ocr_status=DocumentProcessingStatus.OCR_COMPLETED,
            )
            db_session.add(doc)
        db_session.commit()

        # Quota should now be exhausted
        quota = SubscriptionService.get_quota_status(db_session, auth_citizen.id)
        assert quota.ai_document_analyses_used == 3
        assert quota.can_analyze_document is False

        with pytest.raises(Exception) as excinfo:
            SubscriptionService.enforce_document_analysis_quota(db_session, auth_citizen.id)
        assert "403" in str(excinfo.value)
        assert "quota reached" in str(excinfo.value).lower()

    def test_ai_guidance_quota_enforcement_blocks_when_exceeded(
        self, db_session: Session, auth_citizen: User
    ):
        """Citizens exceeding free guidance limit (5 sessions) are blocked with 403."""
        scheme = Scheme(
            id=uuid.uuid4(),
            scheme_name="Test Welfare Scheme",
            description="Detailed description for testing",
            department="Agriculture Dept",
            state_applicability="All India",
            eligibility_summary="All small farmers",
            official_application_url="https://welfare.gov.in",
            official_source_url="https://welfare.gov.in/rules",
            required_documents=["Aadhaar"],
            application_process=[],
        )
        db_session.add(scheme)
        db_session.commit()

        # Add 5 assessments with non-empty advisory guidance
        for i in range(5):
            ast = Assessment(
                id=uuid.uuid4(),
                user_id=auth_citizen.id,
                scheme_id=scheme.id,
                result_data={"eligible": True},
                advisory_guidance={"tips": [f"Tip {i}"]},
            )
            db_session.add(ast)
        db_session.commit()

        quota = SubscriptionService.get_quota_status(db_session, auth_citizen.id)
        assert quota.ai_guidance_sessions_used == 5
        assert quota.can_request_guidance is False

        with pytest.raises(Exception) as excinfo:
            SubscriptionService.enforce_ai_guidance_quota(db_session, auth_citizen.id)
        assert "403" in str(excinfo.value)

    def test_subscription_auto_expiry(
        self, client_for_user: TestClient, db_session: Session, auth_citizen: User
    ):
        """Expired premium subscriptions are automatically transitioned to expired."""
        expired_sub = Subscription(
            id=uuid.uuid4(),
            user_id=auth_citizen.id,
            plan_type="premium",
            billing_cycle="monthly",
            status="active",
            start_date=datetime.now(timezone.utc) - timedelta(days=60),
            end_date=datetime.now(timezone.utc) - timedelta(days=30),
        )
        db_session.add(expired_sub)
        db_session.commit()

        resp = client_for_user.get("/api/v1/subscriptions/me")
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan_type"] == "free"

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
        resp_plan = client_for_user.post(
            "/api/v1/payments/create-order",
            json={"plan_type": "free", "billing_cycle": "monthly"},
        )
        assert resp_plan.status_code == 400

        resp_cycle = client_for_user.post(
            "/api/v1/payments/create-order",
            json={"plan_type": "premium", "billing_cycle": "weekly"},
        )
        assert resp_cycle.status_code == 400

    def test_verify_payment_success_and_subscription_activation(
        self, client_for_user: TestClient, db_session: Session, auth_citizen: User
    ):
        order_res = client_for_user.post(
            "/api/v1/payments/create-order",
            json={"plan_type": "premium", "billing_cycle": "monthly"},
        ).json()
        order_id = order_res["order_id"]
        payment_id = f"pay_{uuid.uuid4().hex[:14]}"

        payload_bytes = f"{order_id}|{payment_id}".encode("utf-8")
        secret = settings.RAZORPAY_KEY_SECRET.encode("utf-8")
        signature = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()

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

        # Idempotent re-verify check
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

    def test_verify_payment_production_gateway_verification(
        self, client_for_user: TestClient, db_session: Session, auth_citizen: User, monkeypatch
    ):
        """SEC-03: In non-dev mode, verify_and_capture_payment checks payment status with Razorpay API."""
        # 1. Create order in dev mode
        order_res = client_for_user.post(
            "/api/v1/payments/create-order",
            json={"plan_type": "premium", "billing_cycle": "monthly"},
        ).json()
        order_id = order_res["order_id"]
        payment_id = f"pay_{uuid.uuid4().hex[:14]}"

        payload_bytes = f"{order_id}|{payment_id}".encode("utf-8")
        secret = settings.RAZORPAY_KEY_SECRET.encode("utf-8")
        signature = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()

        # Now switch to production mode to test gateway-side verification
        monkeypatch.setattr(settings, "RAZORPAY_DEV_MODE", False)

        # Case 1: Gateway returns captured with correct amount & currency -> Succeeds
        class MockSuccessResponse:
            status_code = 200
            def raise_for_status(self): pass
            def json(self):
                return {
                    "id": payment_id,
                    "order_id": order_id,
                    "status": "captured",
                    "amount": 9900,
                    "currency": "INR",
                    "method": "card",
                }

        monkeypatch.setattr(httpx.Client, "get", lambda *args, **kwargs: MockSuccessResponse())

        verify_res = client_for_user.post(
            "/api/v1/payments/verify",
            json={
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            },
        )
        assert verify_res.status_code == 200
        assert verify_res.json()["success"] is True

        # Case 2: Gateway returns authorized (not captured) -> Rejected 400
        # Re-enable dev mode briefly to create a second order
        monkeypatch.setattr(settings, "RAZORPAY_DEV_MODE", True)
        order_res2 = client_for_user.post(
            "/api/v1/payments/create-order",
            json={"plan_type": "premium", "billing_cycle": "monthly"},
        ).json()
        order_id2 = order_res2["order_id"]
        pay_id2 = "pay_failed_status"
        sig2 = hmac.new(secret, f"{order_id2}|{pay_id2}".encode("utf-8"), hashlib.sha256).hexdigest()

        # Switch back to production mode with a failed status mock
        monkeypatch.setattr(settings, "RAZORPAY_DEV_MODE", False)

        class MockFailedStatusResponse:
            status_code = 200
            def raise_for_status(self): pass
            def json(self):
                return {
                    "id": pay_id2,
                    "order_id": order_id2,
                    "status": "failed",
                    "amount": 9900,
                    "currency": "INR",
                }

        monkeypatch.setattr(httpx.Client, "get", lambda *args, **kwargs: MockFailedStatusResponse())

        verify_res2 = client_for_user.post(
            "/api/v1/payments/verify",
            json={
                "razorpay_order_id": order_id2,
                "razorpay_payment_id": pay_id2,
                "razorpay_signature": sig2,
            },
        )
        assert verify_res2.status_code == 400
        assert "expected 'captured'" in verify_res2.json()["detail"].lower()

    def test_webhook_deduplication_via_webhook_events(
        self, client_for_user: TestClient, db_session: Session, auth_citizen: User
    ):
        """SEC-04: Test deduplication via WebhookEvent table."""
        order_res = client_for_user.post(
            "/api/v1/payments/create-order",
            json={"plan_type": "premium", "billing_cycle": "yearly"},
        ).json()
        order_id = order_res["order_id"]
        payment_id = f"pay_{uuid.uuid4().hex[:14]}"
        event_id = f"evt_{uuid.uuid4().hex[:16]}"

        webhook_body = json.dumps({
            "event_id": event_id,
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
                        "contact": "9876543210",
                        "email": "citizen@example.com",
                    }
                }
            }
        })
        raw_bytes = webhook_body.encode("utf-8")
        wh_signature = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), raw_bytes, hashlib.sha256
        ).hexdigest()

        # First webhook arrival
        resp1 = client_for_user.post(
            "/api/v1/payments/webhook",
            content=raw_bytes,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": wh_signature},
        )
        assert resp1.status_code == 200
        assert resp1.json()["status"] == "captured"

        # WebhookEvent record should exist in database
        event_record = db_session.query(WebhookEvent).filter_by(event_id=event_id).first()
        assert event_record is not None
        assert event_record.event_type == "payment.captured"

        # Duplicate webhook arrival with same event_id
        resp2 = client_for_user.post(
            "/api/v1/payments/webhook",
            content=raw_bytes,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": wh_signature},
        )
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "idempotent_duplicate"

    def test_webhook_refund_full_and_partial(
        self, client_for_user: TestClient, db_session: Session, auth_citizen: User
    ):
        """SEC-07: Full refund revokes subscription; partial refund retains subscription."""
        # 1. Activate monthly premium via order & capture
        order_res = client_for_user.post(
            "/api/v1/payments/create-order",
            json={"plan_type": "premium", "billing_cycle": "monthly"},
        ).json()
        order_id = order_res["order_id"]
        payment_id = f"pay_{uuid.uuid4().hex[:14]}"

        payload_bytes = f"{order_id}|{payment_id}".encode("utf-8")
        secret = settings.RAZORPAY_KEY_SECRET.encode("utf-8")
        signature = hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()

        client_for_user.post(
            "/api/v1/payments/verify",
            json={
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            },
        )

        sub_before = client_for_user.get("/api/v1/subscriptions/me").json()
        assert sub_before["plan_type"] == "premium"

        # 2. Send Partial Refund (₹40 -> 4000 paise out of 9900 paise)
        part_refund_body = json.dumps({
            "event_id": f"evt_{uuid.uuid4().hex[:12]}",
            "event": "refund.processed",
            "payload": {
                "refund": {
                    "entity": {
                        "id": f"rfnd_{uuid.uuid4().hex[:10]}",
                        "payment_id": payment_id,
                        "amount": 4000,
                        "currency": "INR",
                    }
                },
                "payment": {
                    "entity": {
                        "id": payment_id,
                        "order_id": order_id,
                    }
                }
            }
        })
        raw_part = part_refund_body.encode("utf-8")
        sig_part = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), raw_part, hashlib.sha256
        ).hexdigest()

        resp_part = client_for_user.post(
            "/api/v1/payments/webhook",
            content=raw_part,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig_part},
        )
        assert resp_part.status_code == 200
        assert resp_part.json()["status"] == "refunded_partial"

        # Premium subscription is retained after partial refund
        sub_part = client_for_user.get("/api/v1/subscriptions/me").json()
        assert sub_part["plan_type"] == "premium"

        # 3. Send Full Refund (₹99 -> 9900 paise)
        full_refund_body = json.dumps({
            "event_id": f"evt_{uuid.uuid4().hex[:12]}",
            "event": "refund.processed",
            "payload": {
                "refund": {
                    "entity": {
                        "id": f"rfnd_{uuid.uuid4().hex[:10]}",
                        "payment_id": payment_id,
                        "amount": 9900,
                        "currency": "INR",
                    }
                },
                "payment": {
                    "entity": {
                        "id": payment_id,
                        "order_id": order_id,
                    }
                }
            }
        })
        raw_full = full_refund_body.encode("utf-8")
        sig_full = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), raw_full, hashlib.sha256
        ).hexdigest()

        resp_full = client_for_user.post(
            "/api/v1/payments/webhook",
            content=raw_full,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig_full},
        )
        assert resp_full.status_code == 200
        assert resp_full.json()["status"] == "refunded_full"

        # Premium subscription is now revoked (defaults back to Free)
        sub_full = client_for_user.get("/api/v1/subscriptions/me").json()
        assert sub_full["plan_type"] == "free"

    def test_pii_sanitization_in_payment_metadata(
        self, client_for_user: TestClient, db_session: Session, auth_citizen: User
    ):
        """SEC-10: Raw contact, email, and VPA identifiers are masked before DB persistence."""
        order_res = client_for_user.post(
            "/api/v1/payments/create-order",
            json={"plan_type": "premium", "billing_cycle": "monthly"},
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
                        "amount": 9900,
                        "currency": "INR",
                        "status": "captured",
                        "contact": "+919876543210",
                        "email": "rajesh.patel@gmail.com",
                        "vpa": "rajesh@okhdfcbank",
                    }
                }
            }
        })
        raw_bytes = webhook_body.encode("utf-8")
        wh_signature = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), raw_bytes, hashlib.sha256
        ).hexdigest()

        client_for_user.post(
            "/api/v1/payments/webhook",
            content=raw_bytes,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": wh_signature},
        )

        tx = db_session.query(PaymentTransaction).filter_by(razorpay_order_id=order_id).first()
        payload = tx.payment_metadata.get("payload", {})
        assert payload.get("contact") != "+919876543210"
        assert payload.get("contact").endswith("3210")
        assert payload.get("email") != "rajesh.patel@gmail.com"
        assert payload.get("vpa") != "rajesh@okhdfcbank"

    def test_production_config_validation(self):
        """SEC-08: Ensure Settings model_validator rejects dev mode or placeholders in production."""
        with pytest.raises(ValidationError):
            Settings(
                ENVIRONMENT="production",
                RAZORPAY_DEV_MODE=True,
            )

        with pytest.raises(ValidationError):
            Settings(
                ENVIRONMENT="production",
                RAZORPAY_DEV_MODE=False,
                RAZORPAY_KEY_ID="rzp_test_placeholder_key_id",
            )

    def test_assistance_prepare_enforces_ai_guidance_quota(
        self, client_for_user: TestClient, db_session: Session, auth_citizen: User
    ):
        """SEC-06: Assistance /prepare route enforces monthly AI guidance quota."""
        scheme = Scheme(
            id=uuid.uuid4(),
            scheme_name="PM Kisan Test Assistance",
            description="PM Kisan scheme description",
            department="Agriculture Dept",
            state_applicability="All India",
            eligibility_summary="All small farmers",
            official_application_url="https://pmkisan.gov.in",
            official_source_url="https://pmkisan.gov.in/rules",
            required_documents=["Aadhaar", "Land Records"],
            application_process=[],
        )
        db_session.add(scheme)
        db_session.commit()

        # Add 5 assessments to exhaust quota
        for i in range(5):
            ast = Assessment(
                id=uuid.uuid4(),
                user_id=auth_citizen.id,
                scheme_id=scheme.id,
                result_data={"eligible": True},
                advisory_guidance={"tips": [f"Tip {i}"]},
            )
            db_session.add(ast)
        db_session.commit()

        resp = client_for_user.post(f"/api/v1/assistance/schemes/{scheme.id}/prepare")
        assert resp.status_code == 403
        assert "quota reached" in resp.json()["detail"].lower()

    def test_scheme_guide_caching(
        self, client_for_user: TestClient, db_session: Session
    ):
        """SEC-06: GET /schemes/{scheme_id}/guide caches general guides to prevent LLM abuse."""
        scheme = Scheme(
            id=uuid.uuid4(),
            scheme_name="Guide Cache Scheme Test",
            description="Welfare scheme description",
            department="Welfare Dept",
            state_applicability="All India",
            eligibility_summary="Eligible citizens",
            official_application_url="https://welfare.gov.in",
            official_source_url="https://welfare.gov.in/rules",
            required_documents=["Aadhaar"],
            application_process=[],
            application_guide_cache={},
        )
        db_session.add(scheme)
        db_session.commit()

        # Pre-seed cache with known data
        cached_guide = {
            "applicant_info_required": [
                {
                    "field_name": "Full Name",
                    "description": "Must match Aadhaar name",
                    "importance": "Mandatory",
                }
            ],
            "supporting_documents_specs": [
                {
                    "document_type": "Aadhaar",
                    "specifications": "Clear PDF under 2MB",
                    "issuing_authority": "UIDAI",
                }
            ],
            "important_declarations": ["Non-exclusion declaration"],
            "common_mistakes_to_avoid": ["Blurry scan"],
            "submission_precautions": ["Double check IFSC"],
            "portal_steps": [
                {
                    "step_number": 1,
                    "title": "Visit Portal",
                    "instruction": "Click register",
                }
            ],
            "disclaimer": "Cached test disclaimer",
        }
        scheme.application_guide_cache = {"en": cached_guide}
        db_session.commit()

        # Fetch guide
        resp = client_for_user.get(f"/api/v1/assistance/schemes/{scheme.id}/guide?language=en")
        assert resp.status_code == 200
        data = resp.json()
        assert data["disclaimer"] == "Cached test disclaimer"
        assert len(data["common_mistakes_to_avoid"]) == 1
        assert data["common_mistakes_to_avoid"][0] == "Blurry scan"

    def test_cumulative_partial_refunds_and_revocation(
        self, client_for_user: TestClient, db_session: Session, auth_citizen: User
    ):
        """SEC-07: Multiple partial refunds aggregate cumulatively and revoke subscription when >= 100%."""
        order_res = client_for_user.post(
            "/api/v1/payments/create-order",
            json={"plan_type": "premium", "billing_cycle": "monthly"},
        ).json()
        order_id = order_res["order_id"]
        payment_id = f"pay_{uuid.uuid4().hex[:14]}"

        # 1. Capture payment
        SubscriptionService.activate_premium_subscription(
            db=db_session, user_id=auth_citizen.id, billing_cycle="monthly"
        )
        tx = db_session.query(PaymentTransaction).filter_by(razorpay_order_id=order_id).first()
        tx.payment_status = "captured"
        tx.razorpay_payment_id = payment_id
        db_session.commit()

        # 2. First partial refund of ₹50.00 (5,000 paise)
        rfnd_1 = f"rfnd_{uuid.uuid4().hex[:12]}"
        body_1 = json.dumps({
            "event": "refund.processed",
            "payload": {
                "refund": {
                    "entity": {
                        "id": rfnd_1,
                        "payment_id": payment_id,
                        "amount": 5000,
                        "currency": "INR",
                        "status": "processed",
                    }
                }
            }
        }).encode("utf-8")
        sig_1 = hmac.new(settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), body_1, hashlib.sha256).hexdigest()

        res_1 = client_for_user.post(
            "/api/v1/payments/webhook",
            content=body_1,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig_1},
        )
        assert res_1.status_code == 200
        assert res_1.json()["status"] == "refunded_partial"

        db_session.refresh(tx)
        assert float(tx.amount_refunded) == 50.0
        assert tx.payment_status == "partially_refunded"
        sub = SubscriptionService.get_active_subscription(db_session, auth_citizen.id)
        assert sub.plan_type == "premium"
        assert sub.status == "active"

        # 3. Second partial refund of ₹49.00 (4,900 paise) -> total ₹99.00 == 100%
        rfnd_2 = f"rfnd_{uuid.uuid4().hex[:12]}"
        body_2 = json.dumps({
            "event": "refund.processed",
            "payload": {
                "refund": {
                    "entity": {
                        "id": rfnd_2,
                        "payment_id": payment_id,
                        "amount": 4900,
                        "currency": "INR",
                        "status": "processed",
                    }
                }
            }
        }).encode("utf-8")
        sig_2 = hmac.new(settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), body_2, hashlib.sha256).hexdigest()

        res_2 = client_for_user.post(
            "/api/v1/payments/webhook",
            content=body_2,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig_2},
        )
        assert res_2.status_code == 200
        assert res_2.json()["status"] == "refunded_full"

        db_session.refresh(tx)
        assert float(tx.amount_refunded) == 99.0
        assert tx.payment_status == "refunded"

    def test_duplicate_refund_event_idempotency(
        self, client_for_user: TestClient, db_session: Session, auth_citizen: User
    ):
        """SEC-07: refund.created followed by refund.processed for same rfnd_id does not double-count."""
        order_res = client_for_user.post(
            "/api/v1/payments/create-order",
            json={"plan_type": "premium", "billing_cycle": "monthly"},
        ).json()
        order_id = order_res["order_id"]
        payment_id = f"pay_{uuid.uuid4().hex[:14]}"

        tx = db_session.query(PaymentTransaction).filter_by(razorpay_order_id=order_id).first()
        tx.payment_status = "captured"
        tx.razorpay_payment_id = payment_id
        db_session.commit()

        rfnd_id = f"rfnd_{uuid.uuid4().hex[:12]}"

        # Send refund.created
        body_created = json.dumps({
            "event": "refund.created",
            "payload": {
                "refund": {
                    "entity": {
                        "id": rfnd_id,
                        "payment_id": payment_id,
                        "amount": 3000,
                        "currency": "INR",
                        "status": "created",
                    }
                }
            }
        }).encode("utf-8")
        sig = hmac.new(settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), body_created, hashlib.sha256).hexdigest()
        client_for_user.post(
            "/api/v1/payments/webhook",
            content=body_created,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig},
        )

        # Send refund.processed for same refund ID
        body_processed = json.dumps({
            "event": "refund.processed",
            "payload": {
                "refund": {
                    "entity": {
                        "id": rfnd_id,
                        "payment_id": payment_id,
                        "amount": 3000,
                        "currency": "INR",
                        "status": "processed",
                    }
                }
            }
        }).encode("utf-8")
        sig_p = hmac.new(settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), body_processed, hashlib.sha256).hexdigest()
        client_for_user.post(
            "/api/v1/payments/webhook",
            content=body_processed,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig_p},
        )

        db_session.refresh(tx)
        # Should be exactly 30.0, NOT 60.0
        assert float(tx.amount_refunded) == 30.0

    def test_payment_dispute_lifecycle(
        self, client_for_user: TestClient, db_session: Session, auth_citizen: User
    ):
        """SEC-07: Dispute events update dispute_status and chargeback revokes access on dispute.lost."""
        order_res = client_for_user.post(
            "/api/v1/payments/create-order",
            json={"plan_type": "premium", "billing_cycle": "monthly"},
        ).json()
        order_id = order_res["order_id"]
        payment_id = f"pay_{uuid.uuid4().hex[:14]}"

        sub = SubscriptionService.activate_premium_subscription(
            db=db_session, user_id=auth_citizen.id, billing_cycle="monthly"
        )
        tx = db_session.query(PaymentTransaction).filter_by(razorpay_order_id=order_id).first()
        tx.payment_status = "captured"
        tx.razorpay_payment_id = payment_id
        tx.subscription_id = sub.id
        db_session.commit()

        # 1. Dispute Created
        body_disp = json.dumps({
            "event": "payment.dispute.created",
            "payload": {
                "dispute": {
                    "entity": {
                        "id": "disp_12345",
                        "payment_id": payment_id,
                        "amount": 9900,
                        "currency": "INR",
                        "reason_code": "fraud",
                        "status": "open",
                    }
                }
            }
        }).encode("utf-8")
        sig = hmac.new(settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), body_disp, hashlib.sha256).hexdigest()
        res = client_for_user.post(
            "/api/v1/payments/webhook",
            content=body_disp,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "dispute_created"
        db_session.refresh(tx)
        assert tx.dispute_status == "created"

        # 2. Dispute Lost -> Revokes subscription
        body_lost = json.dumps({
            "event": "payment.dispute.lost",
            "payload": {
                "dispute": {
                    "entity": {
                        "id": "disp_12345",
                        "payment_id": payment_id,
                        "amount": 9900,
                        "currency": "INR",
                        "reason_code": "fraud",
                        "status": "lost",
                    }
                }
            }
        }).encode("utf-8")
        sig_l = hmac.new(settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"), body_lost, hashlib.sha256).hexdigest()
        res_l = client_for_user.post(
            "/api/v1/payments/webhook",
            content=body_lost,
            headers={"Content-Type": "application/json", "X-Razorpay-Signature": sig_l},
        )
        assert res_l.status_code == 200
        assert res_l.json()["status"] == "dispute_lost"
        db_session.refresh(tx)
        assert tx.dispute_status == "lost"
        db_session.refresh(sub)
        assert sub.status == "revoked_chargeback"
        assert sub.is_active is False

    def test_atomic_quota_ledger_and_rollback(
        self, db_session: Session, auth_citizen: User
    ):
        """SEC-06: Atomic quota reservation increments counter, and rollback releases reserved unit."""
        quota_before = SubscriptionService.get_quota_status(db_session, auth_citizen.id)
        init_used = quota_before.ai_guidance_sessions_used

        # Consume 1 unit
        SubscriptionService.reserve_and_consume_guidance_quota(db_session, auth_citizen.id)
        quota_after = SubscriptionService.get_quota_status(db_session, auth_citizen.id)
        assert quota_after.ai_guidance_sessions_used == init_used + 1

        # Simulate LLM exception and release quota
        SubscriptionService.release_guidance_quota(db_session, auth_citizen.id)
        quota_released = SubscriptionService.get_quota_status(db_session, auth_citizen.id)
        assert quota_released.ai_guidance_sessions_used == init_used

    def test_failed_ocr_upload_consumes_zero_quota(
        self, client_for_user: TestClient, db_session: Session, auth_citizen: User
    ):
        """SEC-05: Upload with failed OCR creates document in vault but consumes ZERO quota units."""
        from unittest.mock import patch
        from app.services.ocr_service import OCRResult
        import io

        valid_pdf = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n>>\n%%EOF"

        with patch("app.services.ocr_service.ocr_service.process_document") as mock_ocr:
            mock_ocr.return_value = OCRResult(
                extracted_text="",
                confidence=0.0,
                metadata={"error": "Image blur too high"},
                status=DocumentProcessingStatus.OCR_FAILED,
                manual_review_required=True,
                error_message="Image blur too high",
            )

            res = client_for_user.post(
                "/api/v1/documents/upload",
                files={"file": ("blurry_cert.pdf", io.BytesIO(valid_pdf), "application/pdf")},
                data={"document_type": "income_certificate"},
            )

            assert res.status_code == 201
            data = res.json()["document"]
            assert data["ocr_status"] == DocumentProcessingStatus.OCR_FAILED

            # Quota status MUST be 0 used!
            quota = SubscriptionService.get_quota_status(db_session, auth_citizen.id)
            assert quota.ai_document_analyses_used == 0
            assert quota.can_analyze_document is True

    def test_invalid_file_upload_consumes_zero_quota(
        self, client_for_user: TestClient, db_session: Session, auth_citizen: User
    ):
        """SEC-05: Invalid file upload rejected with 400 Bad Request leaves quota completely untouched."""
        import io

        res = client_for_user.post(
            "/api/v1/documents/upload",
            files={"file": ("corrupted.pdf", io.BytesIO(b"NOT_A_REAL_PDF_HEADER"), "application/pdf")},
            data={"document_type": "income_certificate"},
        )
        assert res.status_code == 400

        quota = SubscriptionService.get_quota_status(db_session, auth_citizen.id)
        assert quota.ai_document_analyses_used == 0
        assert quota.can_analyze_document is True

    def test_successful_ocr_upload_consumes_exactly_one_quota(
        self, client_for_user: TestClient, db_session: Session, auth_citizen: User
    ):
        """SEC-05: Valid document upload with successful OCR consumes exactly 1 quota unit."""
        import io
        valid_pdf = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n>>\n%%EOF"

        res = client_for_user.post(
            "/api/v1/documents/upload",
            files={"file": ("income_cert.pdf", io.BytesIO(valid_pdf), "application/pdf")},
            data={"document_type": "income_certificate"},
        )
        assert res.status_code == 201
        data = res.json()["document"]
        assert data["ocr_status"] == DocumentProcessingStatus.OCR_COMPLETED

        quota = SubscriptionService.get_quota_status(db_session, auth_citizen.id)
        assert quota.ai_document_analyses_used == 1
        assert quota.can_analyze_document is True

    def test_retry_ocr_on_failed_document_consumes_quota_only_on_success(
        self, client_for_user: TestClient, db_session: Session, auth_citizen: User
    ):
        """SEC-05: Retrying a failed document charges quota only when OCR succeeds."""
        from unittest.mock import patch
        from app.services.ocr_service import OCRResult
        import io

        valid_pdf = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n>>\n%%EOF"

        # 1. Initial upload fails OCR -> 0 quota used
        with patch("app.services.ocr_service.ocr_service.process_document") as mock_ocr:
            mock_ocr.return_value = OCRResult(
                extracted_text="",
                confidence=0.0,
                metadata={},
                status=DocumentProcessingStatus.OCR_FAILED,
                manual_review_required=True,
                error_message="OCR error",
            )
            res1 = client_for_user.post(
                "/api/v1/documents/upload",
                files={"file": ("doc_retry.pdf", io.BytesIO(valid_pdf), "application/pdf")},
                data={"document_type": "income_certificate"},
            )
            assert res1.status_code == 201
            doc_id = res1.json()["document"]["id"]

        quota1 = SubscriptionService.get_quota_status(db_session, auth_citizen.id)
        assert quota1.ai_document_analyses_used == 0

        # 2. Retry OCR succeeds -> now 1 quota used
        with patch("app.services.ocr_service.ocr_service.process_document") as mock_ocr_success:
            mock_ocr_success.return_value = OCRResult(
                extracted_text="INCOME CERTIFICATE Rs 50,000",
                confidence=0.95,
                metadata={},
                status=DocumentProcessingStatus.OCR_COMPLETED,
                manual_review_required=False,
            )
            res2 = client_for_user.post(f"/api/v1/documents/{doc_id}/retry-ocr")
            assert res2.status_code == 200
            assert res2.json()["ocr_status"] == DocumentProcessingStatus.OCR_COMPLETED

        quota2 = SubscriptionService.get_quota_status(db_session, auth_citizen.id)
        assert quota2.ai_document_analyses_used == 1

        # 3. Retrying an already COMPLETED document returns HTTP 409 Conflict (AUD-05)
        res3 = client_for_user.post(f"/api/v1/documents/{doc_id}/retry-ocr")
        assert res3.status_code == 409
        quota3 = SubscriptionService.get_quota_status(db_session, auth_citizen.id)
        assert quota3.ai_document_analyses_used == 1

    def test_stale_processing_document_auto_healed(
        self, db_session: Session, auth_citizen: User
    ):
        """SEC-05: Abandoned PROCESSING document older than 5 minutes is auto-healed to OCR_FAILED."""
        stale_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        stale_doc = DocumentMetadata(
            id=uuid.uuid4(),
            user_id=auth_citizen.id,
            document_type="income_certificate",
            original_filename="crashed_job.pdf",
            storage_reference="/vault/crashed_job.pdf",
            mime_type="application/pdf",
            file_size=2048,
            ocr_status=DocumentProcessingStatus.PROCESSING,
            created_at=stale_time,
            updated_at=stale_time,
        )
        db_session.add(stale_doc)
        db_session.commit()

        # Quota check should auto-heal this stale record
        quota = SubscriptionService.get_quota_status(db_session, auth_citizen.id)
        assert quota.ai_document_analyses_used == 0
        assert quota.can_analyze_document is True

        db_session.refresh(stale_doc)
        assert stale_doc.ocr_status == DocumentProcessingStatus.OCR_FAILED
        assert "timed out" in stale_doc.ocr_error_message.lower()

    def test_retry_already_successful_document_returns_409_and_preserves_data(
        self, client_for_user: TestClient, db_session: Session, auth_citizen: User
    ):
        """AUD-05: Retrying an already OCR_COMPLETED document returns HTTP 409 and preserves all existing text."""
        doc = DocumentMetadata(
            id=uuid.uuid4(),
            user_id=auth_citizen.id,
            document_type="income_certificate",
            original_filename="verified_income.pdf",
            storage_reference="/vault/verified_income.pdf",
            mime_type="application/pdf",
            file_size=2048,
            ocr_status=DocumentProcessingStatus.OCR_COMPLETED,
            ocr_extracted_text="ANNUAL FAMILY INCOME RS 120,000",
            ocr_confidence=0.94,
            ocr_metadata={"issuer": "Tehsildar"},
            manual_review_required=False,
        )
        db_session.add(doc)
        db_session.commit()

        res = client_for_user.post(f"/api/v1/documents/{doc.id}/retry-ocr")
        assert res.status_code == 409
        assert "cannot be retried" in res.json()["detail"].lower()

        # Verify existing data is 100% preserved
        db_session.refresh(doc)
        assert doc.ocr_status == DocumentProcessingStatus.OCR_COMPLETED
        assert doc.ocr_extracted_text == "ANNUAL FAMILY INCOME RS 120,000"
        assert doc.ocr_confidence == 0.94
        assert doc.ocr_metadata == {"issuer": "Tehsildar"}

    def test_expired_worker_token_cannot_finalize(
        self, db_session: Session, auth_citizen: User
    ):
        """AUD-04: Worker with incorrect or expired processing token cannot finalize quota."""
        token_a = uuid.uuid4()
        token_b = uuid.uuid4()
        doc = DocumentMetadata(
            id=uuid.uuid4(),
            user_id=auth_citizen.id,
            document_type="income_certificate",
            original_filename="worker_test.pdf",
            storage_reference="/vault/worker_test.pdf",
            mime_type="application/pdf",
            file_size=1024,
            ocr_status=DocumentProcessingStatus.PROCESSING,
            processing_token=token_a,
            lease_expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        db_session.add(doc)
        db_session.commit()

        # Worker B tries to finalize using token_b (mismatch)
        success = SubscriptionService.finalize_document_analysis(
            db=db_session,
            user_id=auth_citizen.id,
            doc_id=doc.id,
            processing_token=token_b,
        )
        assert success is False

        # Quota remains 0
        quota = SubscriptionService.get_quota_status(db_session, auth_citizen.id)
        assert quota.ai_document_analyses_used == 0

    def test_recovered_document_rejects_old_worker_result(
        self, db_session: Session, auth_citizen: User
    ):
        """AUD-03, AUD-04: Stale recovered document rejects late finalization by expired worker."""
        token_old = uuid.uuid4()
        past_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        doc = DocumentMetadata(
            id=uuid.uuid4(),
            user_id=auth_citizen.id,
            document_type="income_certificate",
            original_filename="stale_worker.pdf",
            storage_reference="/vault/stale_worker.pdf",
            mime_type="application/pdf",
            file_size=1024,
            ocr_status=DocumentProcessingStatus.PROCESSING,
            processing_token=token_old,
            lease_expires_at=past_time,
            created_at=past_time,
        )
        db_session.add(doc)
        db_session.commit()

        # Auto-heal runs and revokes lease
        SubscriptionService.auto_heal_stale_processing_documents(db_session, auth_citizen.id)
        db_session.refresh(doc)
        assert doc.ocr_status == DocumentProcessingStatus.OCR_FAILED
        assert doc.processing_token is None

        # Old worker finishes late and attempts to finalize with token_old
        success = SubscriptionService.finalize_document_analysis(
            db=db_session,
            user_id=auth_citizen.id,
            doc_id=doc.id,
            processing_token=token_old,
        )
        assert success is False
        db_session.refresh(doc)
        assert doc.ocr_status == DocumentProcessingStatus.OCR_FAILED

    def test_active_worker_with_renewed_lease_not_marked_failed(
        self, db_session: Session, auth_citizen: User
    ):
        """AUD-03: Active worker with renewed lease is not revoked by auto-heal even if created_at > 300s."""
        token = uuid.uuid4()
        now = datetime.now(timezone.utc)
        doc = DocumentMetadata(
            id=uuid.uuid4(),
            user_id=auth_citizen.id,
            document_type="income_certificate",
            original_filename="long_running.pdf",
            storage_reference="/vault/long_running.pdf",
            mime_type="application/pdf",
            file_size=5000,
            ocr_status=DocumentProcessingStatus.PROCESSING,
            processing_token=token,
            created_at=now - timedelta(minutes=6),  # created 6 mins ago
            lease_expires_at=now + timedelta(minutes=4),  # but heartbeat renewed lease
        )
        db_session.add(doc)
        db_session.commit()

        # Auto-heal should NOT revoke this document because lease_expires_at > now
        healed = SubscriptionService.auto_heal_stale_processing_documents(db_session, auth_citizen.id)
        assert healed == 0

        db_session.refresh(doc)
        assert doc.ocr_status == DocumentProcessingStatus.PROCESSING
        assert doc.processing_token == token

    def test_failed_retry_consumes_zero_quota(
        self, client_for_user: TestClient, db_session: Session, auth_citizen: User
    ):
        """AUD-01: Eligible failed document retry that fails again still consumes zero quota."""
        from unittest.mock import patch
        from app.services.ocr_service import OCRResult
        from app.services.storage_service import storage_service

        valid_pdf = b"%PDF-1.4\n1 0 obj\n<<\n>>\nendobj\ntrailer\n<<\n>>\n%%EOF"
        storage_ref = storage_service.save_file(auth_citizen.id, valid_pdf, "pdf")

        doc = DocumentMetadata(
            id=uuid.uuid4(),
            user_id=auth_citizen.id,
            document_type="income_certificate",
            original_filename="unreadable_scan.pdf",
            storage_reference=storage_ref,
            mime_type="application/pdf",
            file_size=len(valid_pdf),
            ocr_status=DocumentProcessingStatus.OCR_FAILED,
        )
        db_session.add(doc)
        db_session.commit()

        # Mock OCR service to fail again
        with patch("app.services.ocr_service.ocr_service.process_document") as mock_ocr:
            mock_ocr.return_value = OCRResult(
                extracted_text="",
                confidence=0.0,
                metadata={},
                status=DocumentProcessingStatus.OCR_FAILED,
                manual_review_required=True,
                error_message="Still unreadable",
            )
            res = client_for_user.post(f"/api/v1/documents/{doc.id}/retry-ocr")
            assert res.status_code == 200
            assert res.json()["ocr_status"] == DocumentProcessingStatus.OCR_FAILED

        quota = SubscriptionService.get_quota_status(db_session, auth_citizen.id)
        assert quota.ai_document_analyses_used == 0

    def test_duplicate_finalization_is_idempotent(
        self, db_session: Session, auth_citizen: User
    ):
        """AUD-07: Multiple finalize calls do not double count usage."""
        doc = DocumentMetadata(
            id=uuid.uuid4(),
            user_id=auth_citizen.id,
            document_type="income_certificate",
            original_filename="idempotent.pdf",
            storage_reference="/vault/idempotent.pdf",
            mime_type="application/pdf",
            file_size=1024,
            ocr_status=DocumentProcessingStatus.OCR_COMPLETED,
        )
        db_session.add(doc)
        db_session.commit()

        # Call finalize 3 times
        for _ in range(3):
            SubscriptionService.finalize_document_analysis(db_session, auth_citizen.id)

        quota = SubscriptionService.get_quota_status(db_session, auth_citizen.id)
        assert quota.ai_document_analyses_used == 1

