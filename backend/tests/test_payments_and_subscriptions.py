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
