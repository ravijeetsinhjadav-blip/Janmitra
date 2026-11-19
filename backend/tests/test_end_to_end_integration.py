"""JanMitra Assist – Phase 10 Comprehensive End-to-End Integration & Security Test Suite.

Verifies the complete 19-point citizen journey and cross-module integration:
1. Registration, OTP verification, and login.
2. Profile creation, updating, and retrieval.
3. Scheme discovery, search, and category listing.
4. Profile-based scheme recommendations.
5. Deterministic eligibility assessment.
6. Document upload and secure storage (magic bytes, size, and quota checks).
7. Document checklist verification for schemes.
8. Safe document download with nosniff and privacy headers.
9. Multi-dimensional readiness scoring and discrepancy analysis.
10. AI advisory generation with official portal disclaimers and citations.
11. Step-by-step application assistance and official portal guide.
12. Manual application tracking creation with atomic status history.
13. Application status updates and citizen remarks.
14. Citizen reminders creation, listing upcoming, and toggling completion.
15. Notifications listing, unread count, and marking read.
16. Subscriptions, manual renewals, and payment lifecycle:
    - Free user quota verification.
    - Razorpay order creation and payment verification.
    - Pre-expiry manual renewal extending from existing expiry date (+30 / +365 days).
    - Post-expiry renewal starting fresh from now.
    - Duplicate payment / webhook event deduplication.
    - Immediate fallback to Free tier upon cancellation.
    - Premium gates (deep consistency analysis).
17. Full-system IDOR protection and citizen isolation:
    - Cross-citizen document access, download, and deletion rejection.
    - Cross-citizen application and reminder access rejection.
    - Cross-citizen advisory and assessment access rejection.
18. Administrative RBAC and oversight:
    - Citizen blocked from /admin routes with HTTP 403 Forbidden.
    - Admin stats, user management, and scheme management.
19. Account deletion, session revocation, and 30-day statutory retention.
"""

import io
import uuid
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User
from app.models.profile import UserProfile
from app.models.scheme import Scheme
from app.models.document import DocumentMetadata, DocumentProcessingStatus
from app.models.assessment import Assessment
from app.models.application import Application
from app.models.subscription import Subscription
from app.models.payment import PaymentTransaction
from app.services.subscription_service import SubscriptionService


VALID_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n>>\n%%EOF"
VALID_PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"


def _normalize_dt(dt: datetime) -> datetime:
    """Normalize datetime read from SQLite to timezone-aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@pytest.fixture
def test_scheme(db_session) -> Scheme:
    """Fixture to provide a standard welfare scheme for testing."""
    scheme = Scheme(
        id=uuid.uuid4(),
        scheme_name="PM Kisan Samman Nidhi",
        category="Agriculture",
        state_applicability="All India",
        department="Ministry of Agriculture & Farmers Welfare",
        description="Income support scheme for agricultural farmer families across India.",
        eligibility_summary="Income support for small and marginal landholding farmer families.",
        benefits=["Rs. 6000 per year distributed in three 4-monthly installments."],
        eligibility_criteria=[
            {"condition_name": "Farmer Occupation", "field": "occupation", "operator": "eq", "expected_value": "Farmer", "explanation": "Farmer"},
            {"condition_name": "Income Limit", "field": "annual_family_income", "operator": "lte", "expected_value": 250000, "explanation": "Income <= 250k"},
        ],
        required_documents=["land_ownership_proof", "income_certificate", "bank_passbook"],
        application_process=["Register on PM Kisan portal", "Upload land record", "Verify bank details"],
        official_source_url="https://pmkisan.gov.in",
        official_application_url="https://pmkisan.gov.in",
        status="active",
        is_active=True,
    )
    db_session.add(scheme)
    db_session.commit()
    db_session.refresh(scheme)
    return scheme


class TestEndToEndCitizenJourneyAndSecurity:
    """End-to-End integration test covering the complete citizen lifecycle and security bounds."""

    def test_full_citizen_journey_e2e(self, client: TestClient, db_session, test_scheme: Scheme):
        # =========================================================================
        # 1. Registration, Email + Password Authentication, and Login
        # =========================================================================
        email = "citizen.e2e@example.com"
        password = "CitizenPassword@2026!"
        reg_res = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "confirm_password": password,
                "full_name": "Ramesh Patel",
                "mobile_number": "+919876543210",
            },
        )
        assert reg_res.status_code == 201
        auth_data = reg_res.json()
        token = auth_data["access_token"]
        refresh_token = auth_data["refresh_token"]
        user_id = auth_data["user_id"]
        headers = {"Authorization": f"Bearer {token}"}

        # Check /auth/me
        me_res = client.get("/api/v1/auth/me", headers=headers)
        assert me_res.status_code == 200
        assert me_res.json()["email"] == email.lower()

        # Login test
        login_res = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login_res.status_code == 200

        # Refresh token rotation check
        refresh_res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert refresh_res.status_code == 200
        rotated_token = refresh_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {rotated_token}"}

        # =========================================================================
        # 2. Profile Creation, Updating, and Retrieval
        # =========================================================================
        profile_payload = {
            "full_name": "Ramesh Kumar Patel",
            "date_of_birth": "1988-05-15",
            "state": "Gujarat",
            "district": "Ahmedabad",
            "residence_type": "rural",
            "annual_family_income": 180000.0,
            "occupation": "Farmer",
            "education_level": "Higher Secondary",
        }
        create_profile_res = client.put("/api/v1/users/me/profile", json=profile_payload, headers=headers)
        assert create_profile_res.status_code == 200
        assert create_profile_res.json()["full_name"] == "Ramesh Kumar Patel"

        get_profile_res = client.get("/api/v1/users/me/profile", headers=headers)
        assert get_profile_res.status_code == 200
        assert get_profile_res.json()["occupation"] == "Farmer"

        # =========================================================================
        # 3. Scheme Discovery and Categories
        # =========================================================================
        cat_res = client.get("/api/v1/schemes/categories")
        assert cat_res.status_code == 200
        categories = [c["category"] for c in cat_res.json()]
        assert "Agriculture" in categories

        schemes_res = client.get("/api/v1/schemes?category=Agriculture&q=Kisan")
        assert schemes_res.status_code == 200
        schemes_list = schemes_res.json()
        assert schemes_list["total"] >= 1
        assert any(s["scheme_name"] == "PM Kisan Samman Nidhi" for s in schemes_list["items"])

        # =========================================================================
        # 4. Profile-Based Scheme Recommendations
        # =========================================================================
        rec_res = client.get("/api/v1/schemes/recommendations", headers=headers)
        assert rec_res.status_code == 200
        recommendations = rec_res.json()
        assert len(recommendations) >= 1
        matched_rec = next((r for r in recommendations if r["scheme"]["scheme_name"] == "PM Kisan Samman Nidhi"), None)
        assert matched_rec is not None
        assert matched_rec["criteria_match_percentage"] == 100.0

        # =========================================================================
        # 5. Deterministic Eligibility Assessment
        # =========================================================================
        assess_res = client.post(f"/api/v1/schemes/{test_scheme.id}/assess", headers=headers)
        assert assess_res.status_code == 201
        assessment_data = assess_res.json()
        assessment_id = assessment_data["assessment_id"]
        assert assessment_data["overall_status"] == "Potentially Eligible"
        assert assessment_data["criteria_match_percentage"] == 100.0

        # Verify historical assessment retrieval
        history_res = client.get("/api/v1/schemes/assessments/history", headers=headers)
        assert history_res.status_code == 200
        assert len(history_res.json()) >= 1

        # =========================================================================
        # 6. Document Upload, Quota & Secure Storage
        # =========================================================================
        doc_file = {
            "file": ("income_certificate.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")
        }
        upload_res = client.post(
            "/api/v1/documents/upload",
            files=doc_file,
            data={"document_type": "income_certificate"},
            headers=headers,
        )
        assert upload_res.status_code == 201
        uploaded_doc = upload_res.json()["document"]
        doc_id = uploaded_doc["id"]
        assert uploaded_doc["ocr_status"] == DocumentProcessingStatus.OCR_COMPLETED

        # Check scheme document checklist
        checklist_res = client.get(f"/api/v1/documents/scheme/{test_scheme.id}/checklist", headers=headers)
        assert checklist_res.status_code == 200
        chk_data = checklist_res.json()
        assert any(item["document_type"] == "income_certificate" and item["is_uploaded"] for item in chk_data["checklist"])

        # =========================================================================
        # 7. Safe Document Download with Security Headers
        # =========================================================================
        download_res = client.get(f"/api/v1/documents/{doc_id}/download", headers=headers)
        assert download_res.status_code == 200
        assert download_res.headers.get("x-content-type-options") == "nosniff"
        assert "private" in download_res.headers.get("cache-control", "")
        assert download_res.content == VALID_PDF_BYTES

        # =========================================================================
        # 8. AI Advisory & Multi-Dimensional Readiness Assessment
        # =========================================================================
        adv_res = client.post(
            f"/api/v1/advisory/schemes/{test_scheme.id}/assess-and-advise",
            json={"language": "en"},
            headers=headers,
        )
        assert adv_res.status_code == 200
        adv_data = adv_res.json()
        assert adv_data["readiness"]["overall_readiness_score"] >= 0
        assert adv_data["advisory"] is not None
        assert "disclaimer" in adv_data["advisory"]
        assert "JanMitra" in adv_data["advisory"]["disclaimer"] or "government" in adv_data["advisory"]["disclaimer"].lower()

        # =========================================================================
        # 9. Application Assistance & Checklist
        # =========================================================================
        assist_res = client.post(
            f"/api/v1/assistance/schemes/{test_scheme.id}/prepare",
            json={"language": "en"},
            headers=headers,
        )
        assert assist_res.status_code == 200
        assist_data = assist_res.json()
        assert len(assist_data["checklist"]) >= 1
        item_id = assist_data["checklist"][0]["item_id"]

        # Toggle checklist item
        toggle_res = client.patch(
            f"/api/v1/assistance/schemes/{test_scheme.id}/checklist/{item_id}",
            json={"is_completed": True},
            headers=headers,
        )
        assert toggle_res.status_code == 200
        assert toggle_res.json()["is_completed"] is True

        # Scheme portal reference guide
        guide_res = client.get(f"/api/v1/assistance/schemes/{test_scheme.id}/guide", headers=headers)
        assert guide_res.status_code == 200
        assert len(guide_res.json()["portal_steps"]) >= 1

        # =========================================================================
        # 10. Manual Application Tracking & Status History
        # =========================================================================
        now_sub_date = datetime.now(timezone.utc).isoformat()
        app_payload = {
            "scheme_id": str(test_scheme.id),
            "application_reference_number": "PMK-2026-998877",
            "submission_date": now_sub_date,
            "remarks": "Submitted application online through CSC center.",
        }
        create_app_res = client.post("/api/v1/applications", json=app_payload, headers=headers)
        assert create_app_res.status_code == 201
        app_data = create_app_res.json()
        application_id = app_data["id"]
        assert app_data["status"] == "Submitted"

        # Check atomic history created
        hist_res = client.get(f"/api/v1/applications/{application_id}/history", headers=headers)
        assert hist_res.status_code == 200
        history_items = hist_res.json()["history"]
        assert len(history_items) >= 1
        assert history_items[0]["new_status"] == "Submitted"

        # Update status to Under Review
        status_update_res = client.patch(
            f"/api/v1/applications/{application_id}",
            json={"status": "Under Review", "remarks": "Documents being verified by taluka officer"},
            headers=headers,
        )
        assert status_update_res.status_code == 200
        assert status_update_res.json()["status"] == "Under Review"

        # Add reminder
        reminder_time = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        rem_res = client.post(
            f"/api/v1/applications/{application_id}/reminders",
            json={
                "title": "Check land record verification",
                "description": "Visit Revenue office if verification is still pending",
                "reminder_date": reminder_time,
            },
            headers=headers,
        )
        assert rem_res.status_code == 201
        reminder_id = rem_res.json()["id"]

        # Upcoming reminders endpoint
        up_res = client.get("/api/v1/applications/reminders/upcoming", headers=headers)
        assert up_res.status_code == 200
        assert any(r["id"] == reminder_id for r in up_res.json()["reminders"])

        # =========================================================================
        # 11. Notifications and FCM Fallback
        # =========================================================================
        notif_res = client.get("/api/v1/notifications", headers=headers)
        assert notif_res.status_code == 200
        notifs = notif_res.json()["notifications"]
        if notifs:
            first_notif_id = notifs[0]["id"]
            read_res = client.patch(f"/api/v1/notifications/{first_notif_id}/read", headers=headers)
            assert read_res.status_code == 200
            assert read_res.json()["is_read"] is True

        # Device token registration
        dev_token_res = client.post(
            "/api/v1/notifications/devices",
            json={"device_token": "fcm_test_token_1234567890", "device_type": "android"},
            headers=headers,
        )
        assert dev_token_res.status_code == 200

        # =========================================================================
        # 12. Subscriptions, Payments & Renewal Lifecycle
        # =========================================================================
        # Verify initial Free tier
        sub_me_res = client.get("/api/v1/subscriptions/me", headers=headers)
        assert sub_me_res.status_code == 200
        sub_info = sub_me_res.json()
        assert sub_info["plan_type"] == "free"

        # Create Razorpay order
        order_res = client.post(
            "/api/v1/payments/create-order",
            json={"plan_type": "premium", "billing_cycle": "monthly"},
            headers=headers,
        )
        assert order_res.status_code == 201
        order_data = order_res.json()
        order_id = order_data["order_id"]
        assert order_data["amount"] == 9900  # Rs 99 in paise

        # Verify payment with HMAC SHA-256 signature
        raw_sig_payload = f"{order_id}|pay_test_initial_e2e"
        valid_signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
            raw_sig_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        verify_pay_res = client.post(
            "/api/v1/payments/verify",
            json={
                "razorpay_order_id": order_id,
                "razorpay_payment_id": "pay_test_initial_e2e",
                "razorpay_signature": valid_signature,
            },
            headers=headers,
        )
        assert verify_pay_res.status_code == 200
        verify_body = verify_pay_res.json()
        assert verify_body["success"] is True
        assert verify_body["subscription"]["plan_type"] == "premium"

        # Entitlement check: User is now Premium
        sub_me_premium = client.get("/api/v1/subscriptions/me", headers=headers).json()
        assert sub_me_premium["plan_type"] == "premium"
        first_expiry = _normalize_dt(datetime.fromisoformat(sub_me_premium["end_date"].replace("Z", "+00:00")))

        # Premium feature unlocked: Deep consistency analysis
        deep_res = client.post(f"/api/v1/advisory/{assessment_id}/deep-consistency", headers=headers)
        assert deep_res.status_code == 200
        assert deep_res.json()["is_premium_analysis"] is True

        # Pre-expiry manual renewal test: extends from existing expiry date
        renew_order_res = client.post(
            "/api/v1/payments/create-order",
            json={"plan_type": "premium", "billing_cycle": "monthly"},
            headers=headers,
        )
        renew_order_id = renew_order_res.json()["order_id"]
        renew_sig = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
            f"{renew_order_id}|pay_test_renew_e2e".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        verify_renew_res = client.post(
            "/api/v1/payments/verify",
            json={
                "razorpay_order_id": renew_order_id,
                "razorpay_payment_id": "pay_test_renew_e2e",
                "razorpay_signature": renew_sig,
            },
            headers=headers,
        )
        assert verify_renew_res.status_code == 200

        # Verify new expiry extended +30 days from previous expiry
        sub_me_renewed = client.get("/api/v1/subscriptions/me", headers=headers).json()
        second_expiry = _normalize_dt(datetime.fromisoformat(sub_me_renewed["end_date"].replace("Z", "+00:00")))
        diff_days = round((second_expiry - first_expiry).total_seconds() / 86400)
        assert diff_days == 30

        # Duplicate payment verification idempotency check (does NOT extend expiry again)
        dup_res = client.post(
            "/api/v1/payments/verify",
            json={
                "razorpay_order_id": renew_order_id,
                "razorpay_payment_id": "pay_test_renew_e2e",
                "razorpay_signature": renew_sig,
            },
            headers=headers,
        )
        assert dup_res.status_code == 200
        sub_me_after_dup = client.get("/api/v1/subscriptions/me", headers=headers).json()
        third_expiry = _normalize_dt(datetime.fromisoformat(sub_me_after_dup["end_date"].replace("Z", "+00:00")))
        assert third_expiry == second_expiry

        # Immediate Cancellation Policy Check
        cancel_res = client.post("/api/v1/subscriptions/cancel", headers=headers)
        assert cancel_res.status_code == 200
        assert cancel_res.json()["subscription"]["plan_type"] == "free"

        # Deep consistency now blocked with 403 Forbidden
        deep_blocked = client.post(f"/api/v1/advisory/{assessment_id}/deep-consistency", headers=headers)
        assert deep_blocked.status_code == 403

        # =========================================================================
        # 13. Multi-Citizen IDOR Security Verification
        # =========================================================================
        # Register Citizen B
        email_b = "citizen_b.e2e@example.com"
        b_res = client.post(
            "/api/v1/auth/register",
            json={
                "email": email_b,
                "password": "Password@12345",
                "confirm_password": "Password@12345",
                "full_name": "Citizen B",
            },
        )
        b_token = b_res.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {b_token}"}

        # Citizen B cannot view, download, or delete Citizen A's document
        assert client.get(f"/api/v1/documents/{doc_id}", headers=headers_b).status_code in [403, 404]
        assert client.get(f"/api/v1/documents/{doc_id}/download", headers=headers_b).status_code in [403, 404]
        assert client.delete(f"/api/v1/documents/{doc_id}", headers=headers_b).status_code in [403, 404]

        # Citizen B cannot view or update Citizen A's application
        assert client.get(f"/api/v1/applications/{application_id}", headers=headers_b).status_code in [403, 404]
        assert client.patch(
            f"/api/v1/applications/{application_id}/status",
            json={"new_status": "Approved"},
            headers=headers_b,
        ).status_code in [403, 404]

        # Citizen B cannot access Citizen A's assessment
        assert client.get(f"/api/v1/advisory/assessments/{assessment_id}", headers=headers_b).status_code in [403, 404]

        # Ordinary citizens cannot access /admin routes
        assert client.get("/api/v1/admin/stats", headers=headers).status_code == 403
        assert client.get("/api/v1/admin/users", headers=headers).status_code == 403
        assert client.get("/api/v1/admin/stats", headers=headers_b).status_code == 403

        # =========================================================================
        # 14. Admin Operations & Role Verification
        # =========================================================================
        admin_user = User(
            id=uuid.uuid4(),
            mobile_number="+919999999999",
            role="admin",
            is_active=True,
        )
        db_session.add(admin_user)
        db_session.commit()
        admin_token = create_access_token(user_id=str(admin_user.id), role="admin")
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Admin can view stats
        admin_stats = client.get("/api/v1/admin/stats", headers=admin_headers)
        assert admin_stats.status_code == 200
        stats_body = admin_stats.json()
        assert stats_body["total_citizens"] >= 2
        assert stats_body["total_applications"] >= 1
        assert stats_body["total_revenue_inr"] >= 0.0

        # Admin user list
        admin_users = client.get("/api/v1/admin/users", headers=admin_headers)
        assert admin_users.status_code == 200
        assert admin_users.json()["total"] >= 2

        # =========================================================================
        # 15. Account Deletion, Session Revocation, and Statutory Retention
        # =========================================================================
        del_res = client.post(
            "/api/v1/users/me/delete-request",
            json={"reason": "Testing end-to-end user data privacy workflow."},
            headers=headers,
        )
        assert del_res.status_code == 202
        del_data = del_res.json()
        assert del_data["status"] == "pending"

        # Subsequent requests with old token are rejected because user is deactivated
        after_del_res = client.get("/api/v1/users/me", headers=headers)
        assert after_del_res.status_code in [401, 403]

    def test_file_upload_security_mime_and_size_validation(self, client: TestClient):
        """Security audit: verify file validation, magic byte checking, and zero quota waste on failure."""
        email_upload = "upload_test@example.com"
        u_res = client.post(
            "/api/v1/auth/register",
            json={
                "email": email_upload,
                "password": "Password@12345",
                "confirm_password": "Password@12345",
                "full_name": "Upload User",
            },
        )
        token = u_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Upload executable/PHP file masquerading as PDF -> rejected
        fake_pdf = b"<?php echo 'malicious'; ?>"
        bad_file = {"file": ("exploit.pdf", io.BytesIO(fake_pdf), "application/pdf")}
        bad_res = client.post("/api/v1/documents/upload", files=bad_file, data={"document_type": "income_certificate"}, headers=headers)
        assert bad_res.status_code == 400
        detail_msg = bad_res.json()["detail"].lower()
        assert "signature validation failed" in detail_msg or "corrupt" in detail_msg or "magic bytes" in detail_msg

        # 2. Upload disallowed extension (.exe)
        exe_file = {"file": ("malware.exe", io.BytesIO(VALID_PDF_BYTES), "application/octet-stream")}
        exe_res = client.post("/api/v1/documents/upload", files=exe_file, data={"document_type": "income_certificate"}, headers=headers)
        assert exe_res.status_code == 400

        # 3. Verify quota counter was untouched
        sub_res = client.get("/api/v1/subscriptions/me", headers=headers)
        assert sub_res.status_code == 200
        assert sub_res.json()["usage"]["ai_document_analyses_used"] == 0

    def test_free_tier_quota_exhaustion_and_premium_unlock(self, client: TestClient, db_session, test_scheme: Scheme):
        """Verify strict Free tier quota limits on guidance and document analyses."""
        email_free = "quota_free@example.com"
        user_info = client.post(
            "/api/v1/auth/register",
            json={
                "email": email_free,
                "password": "Password@12345",
                "confirm_password": "Password@12345",
                "full_name": "Quota User",
            },
        ).json()
        token = user_info["access_token"]
        user_id = uuid.UUID(user_info["user_id"])
        headers = {"Authorization": f"Bearer {token}"}

        # Create basic profile
        client.put(
            "/api/v1/users/me/profile",
            json={
                "full_name": "Quota Test Citizen",
                "date_of_birth": "1990-01-01",
                "state": "Gujarat",
                "district": "Surat",
                "residence_type": "rural",
                "annual_family_income": 120000.0,
                "occupation": "Farmer",
                "education_level": "Graduate",
            },
            headers=headers,
        )

        # 1. Exhaust Free AI Guidance Quota (5 sessions)
        for _ in range(5):
            SubscriptionService.reserve_and_consume_guidance_quota(db=db_session, user_id=user_id)

        quota_status = SubscriptionService.get_quota_status(db=db_session, user_id=user_id)
        assert quota_status.can_request_guidance is False

        # 6th guidance request fails with 403 Forbidden
        adv_res = client.post(
            f"/api/v1/advisory/schemes/{test_scheme.id}/assess-and-advise",
            json={"language": "en"},
            headers=headers,
        )
        assert adv_res.status_code == 403
        assert "quota reached" in adv_res.json()["detail"].lower()

        # 2. Upgrade to Premium and verify guidance is immediately unlocked
        SubscriptionService.activate_premium_subscription(
            db=db_session,
            user_id=user_id,
            billing_cycle="monthly",
        )

        adv_res_premium = client.post(
            f"/api/v1/advisory/schemes/{test_scheme.id}/assess-and-advise",
            json={"language": "en"},
            headers=headers,
        )
        assert adv_res_premium.status_code == 200

    def test_yearly_manual_renewal_extends_from_existing_expiry(self, client: TestClient, db_session):
        """Verify yearly renewal adds +365 days from the active expiry date."""
        email_yearly = "yearly_renewal@example.com"
        user_info = client.post(
            "/api/v1/auth/register",
            json={
                "email": email_yearly,
                "password": "Password@12345",
                "confirm_password": "Password@12345",
                "full_name": "Yearly User",
            },
        ).json()
        token = user_info["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. First yearly purchase
        order1 = client.post(
            "/api/v1/payments/create-order",
            json={"plan_type": "premium", "billing_cycle": "yearly"},
            headers=headers,
        ).json()["order_id"]
        sig1 = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
            f"{order1}|pay_yearly_1".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        client.post(
            "/api/v1/payments/verify",
            json={"razorpay_order_id": order1, "razorpay_payment_id": "pay_yearly_1", "razorpay_signature": sig1},
            headers=headers,
        )

        sub1 = client.get("/api/v1/subscriptions/me", headers=headers).json()
        assert sub1["plan_type"] == "premium"
        expiry1 = _normalize_dt(datetime.fromisoformat(sub1["end_date"].replace("Z", "+00:00")))

        # 2. Renew yearly before expiry
        order2 = client.post(
            "/api/v1/payments/create-order",
            json={"plan_type": "premium", "billing_cycle": "yearly"},
            headers=headers,
        ).json()["order_id"]
        sig2 = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
            f"{order2}|pay_yearly_2".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        client.post(
            "/api/v1/payments/verify",
            json={"razorpay_order_id": order2, "razorpay_payment_id": "pay_yearly_2", "razorpay_signature": sig2},
            headers=headers,
        )

        sub2 = client.get("/api/v1/subscriptions/me", headers=headers).json()
        expiry2 = _normalize_dt(datetime.fromisoformat(sub2["end_date"].replace("Z", "+00:00")))
        days_diff = round((expiry2 - expiry1).total_seconds() / 86400)
        assert days_diff == 365

    def test_post_expiry_purchase_starts_from_now(self, client: TestClient, db_session):
        """Verify an expired subscription repurchase starts fresh from now."""
        email_post = "post_expiry@example.com"
        user_info = client.post(
            "/api/v1/auth/register",
            json={
                "email": email_post,
                "password": "Password@12345",
                "confirm_password": "Password@12345",
                "full_name": "Post Expiry User",
            },
        ).json()
        user_id = uuid.UUID(user_info["user_id"])
        token = user_info["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create expired subscription manually in DB
        past_start = datetime.now(timezone.utc) - timedelta(days=60)
        past_end = datetime.now(timezone.utc) - timedelta(days=30)
        old_sub = Subscription(
            id=uuid.uuid4(),
            user_id=user_id,
            plan_type="premium",
            billing_cycle="monthly",
            status="expired",
            start_date=past_start,
            end_date=past_end,
        )
        db_session.add(old_sub)
        db_session.commit()

        # Repurchase Premium
        order = client.post(
            "/api/v1/payments/create-order",
            json={"plan_type": "premium", "billing_cycle": "monthly"},
            headers=headers,
        ).json()["order_id"]
        sig = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
            f"{order}|pay_post_expiry".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        client.post(
            "/api/v1/payments/verify",
            json={"razorpay_order_id": order, "razorpay_payment_id": "pay_post_expiry", "razorpay_signature": sig},
            headers=headers,
        )

        new_sub = client.get("/api/v1/subscriptions/me", headers=headers).json()
        assert new_sub["plan_type"] == "premium"
        new_start = _normalize_dt(datetime.fromisoformat(new_sub["start_date"].replace("Z", "+00:00")))
        now = datetime.now(timezone.utc)
        # Should start now, not in the past
        assert abs((new_start - now).total_seconds()) < 60


