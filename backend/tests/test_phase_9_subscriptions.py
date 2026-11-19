"""Phase 9 Comprehensive Test Suite: Subscriptions, Premium Gates, and Admin Oversight.

Covers:
1. Subscription cancellation: Reverts to Free tier and updates status.
2. Subscription history: Chronological log of past/active plans.
3. Feature access checks: Real-time entitlement endpoint.
4. Premium feature gates:
   - Deep consistency cross-checks (/advisory/{id}/deep-consistency)
   - Advanced completeness gap profiling (/assistance/schemes/{id}/advanced-completeness)
5. Admin oversight & RBAC:
   - Admin subscriptions list with filters
   - Admin payments list with search and zero secrets exposed
   - Admin stats metrics (Free/Premium citizen breakdowns, revenue sum)
"""

import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User
from app.models.profile import UserProfile
from app.models.subscription import Subscription
from app.models.payment import PaymentTransaction
from app.models.scheme import Scheme
from app.models.assessment import Assessment
from app.core.security import create_access_token
from app.services.subscription_service import SubscriptionService


@pytest.fixture
def admin_auth(db_session):
    """Fixture providing verified admin user and auth header."""
    admin = User(
        id=uuid.uuid4(),
        mobile_number="+919800000001",
        role="admin",
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()
    token = create_access_token(user_id=str(admin.id), role="admin")
    return {"user": admin, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture
def citizen_auth(db_session):
    """Fixture providing verified citizen user and auth header."""
    citizen = User(
        id=uuid.uuid4(),
        mobile_number="+919800000002",
        role="citizen",
        is_active=True,
    )
    db_session.add(citizen)
    db_session.flush()

    profile = UserProfile(
        id=uuid.uuid4(),
        user_id=citizen.id,
        full_name="Anil Kumar",
        date_of_birth=datetime(1990, 1, 1).date(),
        state="Gujarat",
        district="Ahmedabad",
        residence_type="rural",
        annual_family_income=150000.0,
        occupation="Shopkeeper",
        education_level="Secondary",
    )
    db_session.add(profile)
    db_session.commit()
    token = create_access_token(user_id=str(citizen.id), role="citizen")
    return {"user": citizen, "profile": profile, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture
def sample_scheme(db_session):
    """Fixture providing an active government scheme."""
    scheme = Scheme(
        id=uuid.uuid4(),
        scheme_name="JanMitra Demo Solar Scheme",
        category="Agriculture",
        department="Ministry of New & Renewable Energy",
        description="Subsidized solar pump scheme for registered farmers.",
        eligibility_summary="Farmer with active agricultural land.",
        official_source_url="https://mnre.gov.in/solar",
        official_application_url="https://mnre.gov.in/apply",
        is_active=True,
    )
    db_session.add(scheme)
    db_session.commit()
    db_session.refresh(scheme)
    return scheme


@pytest.fixture
def sample_assessment(db_session, citizen_auth, sample_scheme):
    """Fixture providing an assessment record with readiness breakdown."""
    assessment = Assessment(
        id=uuid.uuid4(),
        user_id=citizen_auth["user"].id,
        scheme_id=sample_scheme.id,
        overall_readiness_score=85.0,
        readiness_breakdown={
            "overall_readiness_score": 85.0,
            "criteria_match_percentage": 100.0,
            "document_coverage_percentage": 80.0,
            "information_completeness_percentage": 100.0,
            "consistency_score": 90.0,
            "consistency_status": "Consistent",
            "discrepancies": [],
            "low_confidence_documents": [],
        },
        advisory_guidance={"summary": "Eligible for subsidy"},
        language="en",
    )
    db_session.add(assessment)
    db_session.commit()
    db_session.refresh(assessment)
    return assessment


class TestPhase9SubscriptionManagement:
    """Verifies citizen subscription cancellation, history, and feature access checks."""

    def test_cancel_active_premium_subscription_reverts_to_free(
        self, client: TestClient, db_session, citizen_auth
    ):
        user = citizen_auth["user"]
        headers = citizen_auth["headers"]

        # 1. Give citizen an active Premium subscription
        now = datetime.now(timezone.utc)
        sub = Subscription(
            id=uuid.uuid4(),
            user_id=user.id,
            plan_type="premium",
            billing_cycle="monthly",
            status="active",
            start_date=now,
            end_date=now + timedelta(days=30),
        )
        db_session.add(sub)
        db_session.commit()

        # 2. Cancel subscription
        resp = client.post("/api/v1/subscriptions/cancel", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "cancelled" in data["message"].lower()

        # 3. Verify status reverted to free
        me_resp = client.get("/api/v1/subscriptions/me", headers=headers)
        assert me_resp.status_code == 200
        me_data = me_resp.json()
        assert me_data["plan_type"] == "free"
        assert me_data["status"] == "active"

    def test_cancel_when_no_active_premium_returns_404(
        self, client: TestClient, citizen_auth
    ):
        headers = citizen_auth["headers"]
        resp = client.post("/api/v1/subscriptions/cancel", headers=headers)
        assert resp.status_code == 404
        assert "No active Premium subscription found" in resp.json()["detail"]

    def test_subscription_history_endpoint(
        self, client: TestClient, db_session, citizen_auth
    ):
        user = citizen_auth["user"]
        headers = citizen_auth["headers"]

        # Add history entries
        now = datetime.now(timezone.utc)
        s1 = Subscription(
            id=uuid.uuid4(),
            user_id=user.id,
            plan_type="free",
            status="superseded",
            start_date=now - timedelta(days=60),
            end_date=None,
        )
        s2 = Subscription(
            id=uuid.uuid4(),
            user_id=user.id,
            plan_type="premium",
            billing_cycle="monthly",
            status="expired",
            start_date=now - timedelta(days=60),
            end_date=now - timedelta(days=30),
        )
        db_session.add_all([s1, s2])
        db_session.commit()

        resp = client.get("/api/v1/subscriptions/history", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2
        assert len(data["items"]) >= 2
        assert any(i["plan_type"] == "premium" for i in data["items"])

    def test_feature_access_check_endpoint(
        self, client: TestClient, db_session, citizen_auth
    ):
        headers = citizen_auth["headers"]

        # Free tier citizen checking advanced consistency
        resp_free = client.get(
            "/api/v1/subscriptions/features/check?feature=advanced_document_consistency",
            headers=headers,
        )
        assert resp_free.status_code == 200
        data_free = resp_free.json()
        assert data_free["has_access"] is False
        assert data_free["upgrade_required"] is True
        assert "Upgrade to JanMitra Premium" in data_free["message"]

        # Upgrade citizen to Premium
        SubscriptionService.activate_premium_subscription(
            db=db_session,
            user_id=citizen_auth["user"].id,
            billing_cycle="monthly",
        )

        # Check again
        resp_prem = client.get(
            "/api/v1/subscriptions/features/check?feature=advanced_document_consistency",
            headers=headers,
        )
        assert resp_prem.status_code == 200
        data_prem = resp_prem.json()
        assert data_prem["has_access"] is True
        assert data_prem["upgrade_required"] is False
        assert "Access granted" in data_prem["message"]


class TestPhase9FeatureGates:
    """Verifies that Premium features reject Free citizens with 403 and allow Premium citizens."""

    def test_deep_consistency_requires_premium(
        self, client: TestClient, db_session, citizen_auth, sample_assessment
    ):
        user = citizen_auth["user"]
        headers = citizen_auth["headers"]
        assessment_id = str(sample_assessment.id)

        # 1. As Free citizen: Expect HTTP 403 Forbidden with upgrade guidance
        resp_free = client.post(
            f"/api/v1/advisory/{assessment_id}/deep-consistency",
            headers=headers,
        )
        assert resp_free.status_code == 403
        assert "Upgrade to JanMitra Premium" in resp_free.json()["detail"]

        # 2. Upgrade citizen to active Premium
        SubscriptionService.activate_premium_subscription(
            db=db_session,
            user_id=user.id,
            billing_cycle="yearly",
        )

        # 3. As Premium citizen: Expect HTTP 200 OK with premium analysis
        resp_prem = client.post(
            f"/api/v1/advisory/{assessment_id}/deep-consistency",
            headers=headers,
        )
        assert resp_prem.status_code == 200
        data = resp_prem.json()
        assert data["is_premium_analysis"] is True
        assert len(data["cross_document_audit"]) > 0
        assert len(data["recommendations"]) > 0

    def test_advanced_completeness_requires_premium(
        self, client: TestClient, db_session, citizen_auth, sample_scheme
    ):
        user = citizen_auth["user"]
        headers = citizen_auth["headers"]
        scheme_id = str(sample_scheme.id)

        # 1. As Free citizen: Expect HTTP 403 Forbidden with upgrade guidance
        resp_free = client.post(
            f"/api/v1/assistance/schemes/{scheme_id}/advanced-completeness",
            headers=headers,
        )
        assert resp_free.status_code == 403
        assert "Upgrade to JanMitra Premium" in resp_free.json()["detail"]

        # 2. Upgrade to active Premium
        SubscriptionService.activate_premium_subscription(
            db=db_session,
            user_id=user.id,
            billing_cycle="monthly",
        )

        # 3. As Premium citizen: Expect HTTP 200 OK
        resp_prem = client.post(
            f"/api/v1/assistance/schemes/{scheme_id}/advanced-completeness",
            headers=headers,
        )
        assert resp_prem.status_code == 200
        data = resp_prem.json()
        assert data["is_premium_analysis"] is True
        assert "completeness_score" in data
        assert len(data["expedited_action_plan"]) > 0


class TestPhase9AdminOversight:
    """Verifies administrative subscription monitoring, payments audit log, and metrics."""

    def test_admin_subscriptions_endpoint_rbac_and_filters(
        self, client: TestClient, db_session, admin_auth, citizen_auth
    ):
        # 1. Non-admin citizen access rejected with 403
        resp_unauth = client.get(
            "/api/v1/admin/subscriptions",
            headers=citizen_auth["headers"],
        )
        assert resp_unauth.status_code == 403

        # 2. Create sample subscription
        SubscriptionService.activate_premium_subscription(
            db=db_session,
            user_id=citizen_auth["user"].id,
            billing_cycle="yearly",
        )

        # 3. Admin access succeeds
        resp = client.get(
            "/api/v1/admin/subscriptions?plan_type=premium&status=active",
            headers=admin_auth["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        item = data["items"][0]
        assert item["plan_type"] == "premium"
        assert item["status"] == "active"
        assert item["mobile_number"] == citizen_auth["user"].mobile_number
        assert item["citizen_name"] == citizen_auth["profile"].full_name

    def test_admin_payments_endpoint_rbac_and_zero_secret_leakage(
        self, client: TestClient, db_session, admin_auth, citizen_auth
    ):
        # 1. Citizen access blocked
        resp_unauth = client.get(
            "/api/v1/admin/payments",
            headers=citizen_auth["headers"],
        )
        assert resp_unauth.status_code == 403

        # 2. Add test payment transaction
        tx = PaymentTransaction(
            id=uuid.uuid4(),
            user_id=citizen_auth["user"].id,
            razorpay_order_id="order_phase9_test_123",
            razorpay_payment_id="pay_phase9_test_456",
            razorpay_signature="test_sig_hmac_sha256",
            amount=99.0,
            currency="INR",
            plan_type="premium",
            billing_cycle="monthly",
            payment_status="captured",
            payment_method="upi",
        )
        db_session.add(tx)
        db_session.commit()

        # 3. Admin queries payments
        resp = client.get(
            "/api/v1/admin/payments?status=captured",
            headers=admin_auth["headers"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        item = next(p for p in data["items"] if p["razorpay_order_id"] == "order_phase9_test_123")
        assert item["amount"] == 99.0
        assert item["payment_status"] == "captured"

        # Assert zero private secrets exposed in response body
        raw_text = resp.text
        assert "razorpay_secret" not in raw_text.lower()
        assert "webhook_secret" not in raw_text.lower()
        assert "key_secret" not in raw_text.lower()

    def test_admin_stats_metrics_overview(
        self, client: TestClient, db_session, admin_auth, citizen_auth
    ):
        # Create captured payment to test revenue aggregation
        tx = PaymentTransaction(
            id=uuid.uuid4(),
            user_id=citizen_auth["user"].id,
            razorpay_order_id="order_rev_test_789",
            razorpay_payment_id="pay_rev_test_789",
            amount=799.0,
            currency="INR",
            plan_type="premium",
            billing_cycle="yearly",
            payment_status="captured",
        )
        db_session.add(tx)
        db_session.commit()

        resp = client.get("/api/v1/admin/stats", headers=admin_auth["headers"])
        assert resp.status_code == 200
        data = resp.json()
        assert "total_free_users" in data
        assert "total_premium_users" in data
        assert "active_subscriptions" in data
        assert "expired_subscriptions" in data
        assert "cancelled_subscriptions" in data
        assert "total_revenue_inr" in data
        assert data["total_revenue_inr"] >= 799.0

    def test_cancel_repeated_calls_return_idempotent_success_without_state_change(
        self, client: TestClient, db_session, citizen_auth
    ):
        """Repeated cancellation requests return 200 idempotent success without modifying state again."""
        user = citizen_auth["user"]
        headers = citizen_auth["headers"]

        # 1. Activate Premium
        SubscriptionService.activate_premium_subscription(
            db=db_session,
            user_id=user.id,
            billing_cycle="monthly",
        )

        # 2. First cancellation succeeds
        resp1 = client.post("/api/v1/subscriptions/cancel", headers=headers)
        assert resp1.status_code == 200
        assert resp1.json()["success"] is True

        # 3. Second cancellation returns 200 OK idempotent success
        resp2 = client.post("/api/v1/subscriptions/cancel", headers=headers)
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["success"] is True
        assert "already cancelled" in data2["message"].lower()
        assert data2["subscription"]["plan_type"] == "free"

        # 4. Third request also consistent
        resp3 = client.post("/api/v1/subscriptions/cancel", headers=headers)
        assert resp3.status_code == 200
        assert resp3.json()["success"] is True

    def test_cancel_already_expired_subscription_returns_400(
        self, client: TestClient, db_session, citizen_auth
    ):
        """Cancelling an already expired subscription returns 400 Bad Request."""
        user = citizen_auth["user"]
        headers = citizen_auth["headers"]

        now = datetime.now(timezone.utc)
        sub = Subscription(
            id=uuid.uuid4(),
            user_id=user.id,
            plan_type="premium",
            billing_cycle="monthly",
            status="expired",
            start_date=now - timedelta(days=60),
            end_date=now - timedelta(days=30),
        )
        db_session.add(sub)
        db_session.commit()

        resp = client.post("/api/v1/subscriptions/cancel", headers=headers)
        assert resp.status_code == 400
        assert "already expired" in resp.json()["detail"].lower()

    def test_expired_premium_user_enforces_free_quotas_and_blocks_premium_features(
        self, client: TestClient, db_session, citizen_auth, sample_assessment, sample_scheme
    ):
        """Past-expiry Premium subscription immediately falls back to Free tier limits."""
        user = citizen_auth["user"]
        headers = citizen_auth["headers"]

        now = datetime.now(timezone.utc)
        sub = Subscription(
            id=uuid.uuid4(),
            user_id=user.id,
            plan_type="premium",
            billing_cycle="monthly",
            status="active", # set active but date is in the past
            start_date=now - timedelta(days=40),
            end_date=now - timedelta(days=10),
        )
        db_session.add(sub)
        db_session.commit()

        # 1. Inspecting status marks it expired and returns Free tier
        me_resp = client.get("/api/v1/subscriptions/me", headers=headers)
        assert me_resp.status_code == 200
        data = me_resp.json()
        assert data["plan_type"] == "free"
        assert data["usage"]["ai_document_analyses_limit"] == 3
        assert data["usage"]["ai_guidance_sessions_limit"] == 5

        # 2. Premium feature gates reject with 403 Forbidden
        deep_resp = client.post(
            f"/api/v1/advisory/{sample_assessment.id}/deep-consistency",
            headers=headers,
        )
        assert deep_resp.status_code == 403

        comp_resp = client.post(
            f"/api/v1/assistance/schemes/{sample_scheme.id}/advanced-completeness",
            headers=headers,
        )
        assert comp_resp.status_code == 403

    def test_user_cannot_access_another_users_deep_consistency_idor(
        self, client: TestClient, db_session, sample_assessment
    ):
        """Anti-IDOR: Citizen B cannot run consistency audit on Citizen A's assessment."""
        # Create second citizen B with active Premium
        citizen_b = User(
            id=uuid.uuid4(),
            mobile_number="+919800000099",
            role="citizen",
            is_active=True,
        )
        db_session.add(citizen_b)
        db_session.commit()
        token_b = create_access_token(user_id=str(citizen_b.id), role="citizen")
        headers_b = {"Authorization": f"Bearer {token_b}"}

        SubscriptionService.activate_premium_subscription(
            db=db_session,
            user_id=citizen_b.id,
            billing_cycle="yearly",
        )

        # Citizen B attempts to access sample_assessment (belongs to Citizen A)
        resp = client.post(
            f"/api/v1/advisory/{sample_assessment.id}/deep-consistency",
            headers=headers_b,
        )
        assert resp.status_code == 404
        assert "not found or access denied" in resp.json()["detail"].lower()

    def test_admin_revenue_stats_net_partial_refund(
        self, client: TestClient, db_session, admin_auth, citizen_auth
    ):
        """Admin stats subtracts partial refunds from net revenue calculation."""
        # Transaction of 99 INR with 30 INR refunded -> net 69 INR
        tx = PaymentTransaction(
            id=uuid.uuid4(),
            user_id=citizen_auth["user"].id,
            razorpay_order_id="order_partial_rfnd_123",
            razorpay_payment_id="pay_partial_rfnd_123",
            amount=99.0,
            amount_refunded=30.0,
            currency="INR",
            plan_type="premium",
            billing_cycle="monthly",
            payment_status="partially_refunded",
        )
        db_session.add(tx)
        db_session.commit()

        resp = client.get("/api/v1/admin/stats", headers=admin_auth["headers"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_revenue_inr"] >= 69.0
    def test_admin_revenue_stats_excludes_failed_and_pending_payments(
        self, client: TestClient, db_session, admin_auth, citizen_auth
    ):
        """Failed and created/pending transactions are strictly excluded from revenue sum."""
        # Baseline revenue
        base_resp = client.get("/api/v1/admin/stats", headers=admin_auth["headers"])
        base_rev = base_resp.json()["total_revenue_inr"]

        # Add failed transaction
        tx_failed = PaymentTransaction(
            id=uuid.uuid4(),
            user_id=citizen_auth["user"].id,
            razorpay_order_id="order_failed_test_999",
            razorpay_payment_id="pay_failed_test_999",
            amount=999.0,
            currency="INR",
            plan_type="premium",
            billing_cycle="yearly",
            payment_status="failed",
            error_code="BAD_REQUEST_ERROR",
        )
        # Add created/pending transaction
        tx_created = PaymentTransaction(
            id=uuid.uuid4(),
            user_id=citizen_auth["user"].id,
            razorpay_order_id="order_created_test_888",
            razorpay_payment_id=None,
            amount=888.0,
            currency="INR",
            plan_type="premium",
            billing_cycle="yearly",
            payment_status="created",
        )
        db_session.add_all([tx_failed, tx_created])
        db_session.commit()

        resp = client.get("/api/v1/admin/stats", headers=admin_auth["headers"])
        assert resp.status_code == 200
        new_rev = resp.json()["total_revenue_inr"]
        # Revenue must not have increased
        assert new_rev == base_rev

    def test_admin_revenue_stats_handles_null_refund_amounts_safely(
        self, client: TestClient, db_session, admin_auth, citizen_auth
    ):
        """Captured payment with amount_refunded=None is coalesced to 0.0 and counted safely."""
        tx_null_refund = PaymentTransaction(
            id=uuid.uuid4(),
            user_id=citizen_auth["user"].id,
            razorpay_order_id="order_null_rfnd_777",
            razorpay_payment_id="pay_null_rfnd_777",
            amount=150.0,
            amount_refunded=None,  # Null in database
            currency="INR",
            plan_type="premium",
            billing_cycle="monthly",
            payment_status="captured",
        )
        db_session.add(tx_null_refund)
        db_session.commit()

        resp = client.get("/api/v1/admin/stats", headers=admin_auth["headers"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_revenue_inr"] >= 150.0

    def test_admin_revenue_stats_excludes_full_refunds_and_prevents_negative(
        self, client: TestClient, db_session, admin_auth, citizen_auth
    ):
        """Fully refunded payments are excluded and revenue is guaranteed non-negative."""
        tx_refunded = PaymentTransaction(
            id=uuid.uuid4(),
            user_id=citizen_auth["user"].id,
            razorpay_order_id="order_full_rfnd_555",
            razorpay_payment_id="pay_full_rfnd_555",
            amount=500.0,
            amount_refunded=500.0,
            currency="INR",
            plan_type="premium",
            billing_cycle="yearly",
            payment_status="refunded",
        )
        db_session.add(tx_refunded)
        db_session.commit()

        resp = client.get("/api/v1/admin/stats", headers=admin_auth["headers"])
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_revenue_inr"] >= 0.0
    def test_premium_user_is_not_blocked_by_guidance_quota(
        self, db_session, citizen_auth, sample_scheme
    ):
        """Active Premium citizen is not blocked from AI guidance by unapproved 100 ceiling, while Free is limited to 5."""
        user = citizen_auth["user"]

        # 1. Activate Premium
        SubscriptionService.activate_premium_subscription(
            db=db_session,
            user_id=user.id,
            billing_cycle="monthly",
        )

        # 2. Add 105 guidance sessions
        for i in range(105):
            ast = Assessment(
                id=uuid.uuid4(),
                user_id=user.id,
                scheme_id=sample_scheme.id,
                overall_readiness_score=80.0,
                readiness_breakdown={},
                advisory_guidance={"tips": [f"Tip {i}"]},
            )
            db_session.add(ast)
        db_session.commit()

        # 3. Premium citizen quota check returns can_request_guidance=True
        quota = SubscriptionService.get_quota_status(db_session, user.id)
        assert quota.can_request_guidance is True

        # 4. Enforce quota does not raise 403
        SubscriptionService.enforce_ai_guidance_quota(db_session, user.id)

    def test_renewal_extends_from_existing_expiry_date_monthly_and_yearly(
        self, db_session, citizen_auth
    ):
        """Active Premium subscription renewal extends from existing end_date, not current time."""
        from app.services.subscription_service import _normalize_dt
        user = citizen_auth["user"]
        now = datetime.now(timezone.utc)

        # 1. Citizen starts with active subscription expiring in 20 days
        initial_start = now - timedelta(days=10)
        initial_end = now + timedelta(days=20)
        sub = Subscription(
            id=uuid.uuid4(),
            user_id=user.id,
            plan_type="premium",
            billing_cycle="monthly",
            status="active",
            start_date=initial_start,
            end_date=initial_end,
        )
        db_session.add(sub)
        db_session.commit()

        # 2. Purchase monthly renewal (+30 days from existing expiry)
        renewed_sub = SubscriptionService.activate_premium_subscription(
            db=db_session,
            user_id=user.id,
            billing_cycle="monthly",
        )
        assert renewed_sub.id == sub.id
        # End date must extend from initial_end by exactly 30 days
        expected_monthly_end = initial_end + timedelta(days=30)
        assert abs((_normalize_dt(renewed_sub.end_date) - expected_monthly_end).total_seconds()) < 5

        # 3. Purchase yearly renewal (+365 days from the newly extended expiry)
        renewed_yearly = SubscriptionService.activate_premium_subscription(
            db=db_session,
            user_id=user.id,
            billing_cycle="yearly",
        )
        assert renewed_yearly.id == sub.id
        expected_yearly_end = expected_monthly_end + timedelta(days=365)
        assert abs((_normalize_dt(renewed_yearly.end_date) - expected_yearly_end).total_seconds()) < 5
        assert renewed_yearly.billing_cycle == "yearly"

    def test_expired_subscription_renewal_starts_from_now(
        self, db_session, citizen_auth
    ):
        """Expired subscription purchase creates a new active subscription starting from current time."""
        from app.services.subscription_service import _normalize_dt
        user = citizen_auth["user"]
        now = datetime.now(timezone.utc)

        # Citizen had an expired subscription 5 days ago
        expired_sub = Subscription(
            id=uuid.uuid4(),
            user_id=user.id,
            plan_type="premium",
            billing_cycle="monthly",
            status="expired",
            start_date=now - timedelta(days=35),
            end_date=now - timedelta(days=5),
        )
        db_session.add(expired_sub)
        db_session.commit()

        # Citizen purchases new monthly subscription
        new_sub = SubscriptionService.activate_premium_subscription(
            db=db_session,
            user_id=user.id,
            billing_cycle="monthly",
        )
        assert new_sub.id != expired_sub.id
        assert new_sub.status == "active"
        # Start date is approximately now, end date is now + 30 days
        assert abs((_normalize_dt(new_sub.start_date) - now).total_seconds()) < 5
        assert abs((_normalize_dt(new_sub.end_date) - (now + timedelta(days=30))).total_seconds()) < 5

    def test_duplicate_payment_verification_cannot_extend_expiry_more_than_once(
        self, client: TestClient, db_session, citizen_auth
    ):
        """Duplicate payment verification callbacks return idempotent success and do not extend expiry twice."""
        user = citizen_auth["user"]
        headers = citizen_auth["headers"]

        # Create order
        create_resp = client.post(
            "/api/v1/payments/create-order",
            headers=headers,
            json={"plan_type": "premium", "billing_cycle": "monthly"},
        )
        assert create_resp.status_code == 201
        order_data = create_resp.json()
        order_id = order_data["order_id"]
        payment_id = f"pay_{uuid.uuid4().hex[:12]}"

        # Compute valid signature
        import hmac, hashlib
        from app.core.config import settings
        expected_payload = f"{order_id}|{payment_id}".encode("utf-8")
        secret = settings.RAZORPAY_KEY_SECRET.encode("utf-8")
        signature = hmac.new(secret, expected_payload, hashlib.sha256).hexdigest()

        # 1. First verification succeeds and activates
        v_resp1 = client.post(
            "/api/v1/payments/verify",
            headers=headers,
            json={
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            },
        )
        assert v_resp1.status_code == 200
        sub1 = v_resp1.json()["subscription"]
        end_date1 = sub1["end_date"]

        # 2. Second duplicate verification returns idempotent success
        v_resp2 = client.post(
            "/api/v1/payments/verify",
            headers=headers,
            json={
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            },
        )
        assert v_resp2.status_code == 200
        sub2 = v_resp2.json()["subscription"]
        end_date2 = sub2["end_date"]

        # End date must NOT have moved further
        assert end_date1 == end_date2

    def test_cancelled_subscription_reverts_immediately_and_new_purchase_starts_fresh(
        self, client: TestClient, db_session, citizen_auth
    ):
        """Cancelled subscription follows immediate-cancellation policy and subsequent purchase activates fresh."""
        from app.services.subscription_service import _normalize_dt
        user = citizen_auth["user"]
        headers = citizen_auth["headers"]

        # 1. Activate Premium
        SubscriptionService.activate_premium_subscription(
            db=db_session,
            user_id=user.id,
            billing_cycle="monthly",
        )

        # 2. Cancel subscription -> immediately on Free
        cancel_resp = client.post("/api/v1/subscriptions/cancel", headers=headers)
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["subscription"]["plan_type"] == "free"

        # 3. User repurchases Premium -> starts fresh from now
        now = datetime.now(timezone.utc)
        repurchased = SubscriptionService.activate_premium_subscription(
            db=db_session,
            user_id=user.id,
            billing_cycle="yearly",
        )
        assert repurchased.status == "active"
        assert abs((_normalize_dt(repurchased.start_date) - now).total_seconds()) < 5
        assert abs((_normalize_dt(repurchased.end_date) - (now + timedelta(days=365))).total_seconds()) < 5

