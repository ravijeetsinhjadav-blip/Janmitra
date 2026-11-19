"""Admin Dashboard & Management Endpoints Test Suite (Phase 8.3)

Verifies:
1. Strict RBAC enforcement: Citizen access blocked with 403 Forbidden.
2. Unauthenticated access blocked with 401 Unauthorized.
3. Administrative statistics overview (GET /api/v1/admin/stats).
4. Citizen user management: listing, filtering, detail retrieval, active status toggle.
5. Government scheme management: listing, creation, and updating.
6. Citizen application tracking oversight (monitoring with citizen-reported disclaimer).
"""

import uuid
from datetime import datetime, timezone
import pytest
from app.models.user import User
from app.models.scheme import Scheme
from app.models.application import Application
from app.core.security import create_access_token


@pytest.fixture
def admin_user(db_session):
    """Fixture providing a verified admin user and auth header."""
    admin = User(
        id=uuid.uuid4(),
        mobile_number="+919888888880",
        role="admin",
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()
    token = create_access_token(user_id=str(admin.id), role="admin")
    return {"user": admin, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture
def citizen_user(db_session):
    """Fixture providing a standard citizen user and auth header."""
    citizen = User(
        id=uuid.uuid4(),
        mobile_number="+919888888881",
        email="citizen_fixture@example.com",
        role="citizen",
        is_active=True,
    )
    db_session.add(citizen)
    db_session.commit()
    token = create_access_token(user_id=str(citizen.id), role="citizen")
    return {"user": citizen, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture
def sample_scheme(db_session):
    """Fixture creating a test scheme."""
    scheme = Scheme(
        id=uuid.uuid4(),
        scheme_name="PM Kisan Samman Nidhi",
        category="Agriculture",
        department="Ministry of Agriculture",
        description="Income support to all landholding farmer families.",
        short_description="Annual financial benefit of Rs 6,000.",
        state_applicability="All India",
        eligibility_summary="Landholder farmer families across all states.",
        official_source_url="https://pmkisan.gov.in",
        official_application_url="https://pmkisan.gov.in/RegistrationForm.aspx",
        source_freshness_status="Verified Official Source",
        is_demo_data=False,
        is_active=True,
    )
    db_session.add(scheme)
    db_session.commit()
    return scheme


def test_admin_stats_unauthorized(client):
    """Unauthenticated requests must be rejected with 401 Unauthorized."""
    res = client.get("/api/v1/admin/stats")
    assert res.status_code == 401


def test_admin_stats_forbidden_for_citizen(client, citizen_user):
    """Citizen users must be forbidden from accessing admin endpoints (403)."""
    res = client.get("/api/v1/admin/stats", headers=citizen_user["headers"])
    assert res.status_code == 403
    assert "Administrative privileges required" in res.json()["detail"]


def test_admin_stats_success(client, admin_user, sample_scheme, citizen_user, db_session):
    """Admin callers receive aggregated platform KPI statistics."""
    # Create an application
    now = datetime.now(timezone.utc)
    app = Application(
        id=uuid.uuid4(),
        user_id=citizen_user["user"].id,
        scheme_id=sample_scheme.id,
        status="Under Review",
        application_reference_number="PMK-2026-TEST",
        submission_date=now,
    )
    db_session.add(app)
    db_session.commit()

    res = client.get("/api/v1/admin/stats", headers=admin_user["headers"])
    assert res.status_code == 200
    data = res.json()
    assert "total_citizens" in data
    assert data["total_citizens"] >= 1
    assert "total_schemes" in data
    assert data["total_schemes"] >= 1
    assert "total_applications" in data
    assert data["total_applications"] >= 1
    assert "applications_by_status" in data
    assert data["applications_by_status"]["Under Review"] >= 1


def test_admin_list_users(client, admin_user, citizen_user):
    """Admin can list and search citizens."""
    res = client.get("/api/v1/admin/users", headers=admin_user["headers"])
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert len(data["users"]) >= 1

    # Search by mobile
    mobile_sub = citizen_user["user"].mobile_number[-6:]
    res_search = client.get(f"/api/v1/admin/users?query={mobile_sub}", headers=admin_user["headers"])
    assert res_search.status_code == 200
    assert len(res_search.json()["users"]) >= 1

    # Search by email (Phase 11 Email auth verification)
    email_sub = citizen_user["user"].email.split("@")[0]
    res_email_search = client.get(f"/api/v1/admin/users?query={email_sub}", headers=admin_user["headers"])
    assert res_email_search.status_code == 200
    assert len(res_email_search.json()["users"]) >= 1


def test_admin_get_user_detail(client, admin_user, citizen_user):
    """Admin can retrieve detailed citizen profile and statistics."""
    user_id = str(citizen_user["user"].id)
    res = client.get(f"/api/v1/admin/users/{user_id}", headers=admin_user["headers"])
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == user_id
    assert data["role"] == "citizen"
    assert "applications_count" in data


def test_admin_update_user_status(client, admin_user, citizen_user, db_session):
    """Admin can deactivate and activate citizen accounts."""
    user_id = str(citizen_user["user"].id)

    # Deactivate
    res_deact = client.patch(
        f"/api/v1/admin/users/{user_id}/status",
        headers=admin_user["headers"],
        json={"is_active": False},
    )
    assert res_deact.status_code == 200
    assert res_deact.json()["is_active"] is False

    # Check citizen cannot access
    res_check = client.get("/api/v1/users/me", headers=citizen_user["headers"])
    assert res_check.status_code == 403

    # Reactivate
    res_act = client.patch(
        f"/api/v1/admin/users/{user_id}/status",
        headers=admin_user["headers"],
        json={"is_active": True},
    )
    assert res_act.status_code == 200
    assert res_act.json()["is_active"] is True


def test_admin_schemes_crud(client, admin_user):
    """Admin can create, list, and update government scheme records."""
    # 1. Create Scheme
    new_scheme_payload = {
        "scheme_name": "Ayushman Bharat PM-JAY Test",
        "category": "Healthcare",
        "department": "National Health Authority",
        "description": "Health coverage of Rs. 5 Lakhs per family per year.",
        "short_description": "Annual secondary and tertiary hospitalization cover.",
        "state_applicability": "All India",
        "eligibility_summary": "Families belonging to bottom 40% income bracket.",
        "official_source_url": "https://pmjay.gov.in",
        "official_application_url": "https://setu.pmjay.gov.in",
        "benefits": ["Cashless hospitalization up to 5 lakh"],
        "eligibility_criteria": [{"field": "income", "op": "lte", "value": 250000}],
        "required_documents": ["Aadhaar", "Ration Card"],
        "is_demo_data": False,
    }
    res_create = client.post("/api/v1/admin/schemes", headers=admin_user["headers"], json=new_scheme_payload)
    assert res_create.status_code == 201
    created_id = res_create.json()["id"]

    # 2. List Schemes
    res_list = client.get(f"/api/v1/admin/schemes?query=Ayushman", headers=admin_user["headers"])
    assert res_list.status_code == 200
    assert any(s["id"] == created_id for s in res_list.json()["schemes"])

    # 3. Update Scheme
    res_update = client.patch(
        f"/api/v1/admin/schemes/{created_id}",
        headers=admin_user["headers"],
        json={"is_active": False, "source_freshness_status": "Official Portal Verified"},
    )
    assert res_update.status_code == 200
    assert res_update.json()["is_active"] is False
    assert res_update.json()["source_freshness_status"] == "Official Portal Verified"


def test_admin_monitor_applications(client, admin_user, sample_scheme, citizen_user, db_session):
    """Admin can monitor citizen tracked applications with explicit citizen-reported qualification."""
    now = datetime.now(timezone.utc)
    app = Application(
        id=uuid.uuid4(),
        user_id=citizen_user["user"].id,
        scheme_id=sample_scheme.id,
        status="Submitted",
        application_reference_number="GOV-REF-9988",
        submission_date=now,
    )
    db_session.add(app)
    db_session.commit()

    res = client.get("/api/v1/admin/applications", headers=admin_user["headers"])
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert "status_summary" in data
    assert any(a["id"] == str(app.id) for a in data["applications"])
    app_item = next(a for a in data["applications"] if a["id"] == str(app.id))
    assert app_item["source_qualification"] == "Citizen Reported"
    assert app_item["status"] == "Submitted"



def test_admin_token_expired_rejected(client, admin_user):
    """Expired admin token must be rejected with 401 Unauthorized."""
    from datetime import timedelta
    from app.core.security import create_access_token

    expired_token = create_access_token(
        user_id=str(admin_user["user"].id),
        role="admin",
        expires_delta=timedelta(seconds=-30),
    )
    headers = {"Authorization": f"Bearer {expired_token}"}
    res = client.get("/api/v1/admin/stats", headers=headers)
    assert res.status_code == 401
    assert "Signature has expired" in res.json()["detail"] or "expired" in res.json()["detail"].lower()


def test_admin_token_invalid_signature_rejected(client, admin_user):
    """Tampered or invalid signature token must be rejected with 401 Unauthorized."""
    valid_token = admin_user["headers"]["Authorization"].replace("Bearer ", "")
    tampered_token = valid_token[:-10] + "TAMPERED99"
    headers = {"Authorization": f"Bearer {tampered_token}"}
    res = client.get("/api/v1/admin/stats", headers=headers)
    assert res.status_code == 401


def test_admin_token_deactivated_admin_rejected(client, admin_user, db_session):
    """Deactivated admin accounts must be forbidden (403)."""
    admin_user["user"].is_active = False
    db_session.commit()

    res = client.get("/api/v1/admin/stats", headers=admin_user["headers"])
    assert res.status_code == 403
    assert "deactivated" in res.json()["detail"].lower()

    # Re-enable
    admin_user["user"].is_active = True
    db_session.commit()


def test_citizen_token_cannot_access_any_admin_endpoint(client, citizen_user):
    """Citizen role token must receive 403 Forbidden across all administrative routes."""
    headers = citizen_user["headers"]

    # 1. Stats
    assert client.get("/api/v1/admin/stats", headers=headers).status_code == 403

    # 2. Users directory
    assert client.get("/api/v1/admin/users", headers=headers).status_code == 403

    # 3. Specific user detail
    assert client.get(f"/api/v1/admin/users/{citizen_user['user'].id}", headers=headers).status_code == 403

    # 4. Schemes list
    assert client.get("/api/v1/admin/schemes", headers=headers).status_code == 403

    # 5. Create scheme
    assert client.post("/api/v1/admin/schemes", headers=headers, json={"scheme_name": "Test"}).status_code == 403

    # 6. Applications monitoring
    assert client.get("/api/v1/admin/applications", headers=headers).status_code == 403


def test_admin_trigger_process_due_reminders(client, admin_user, citizen_user, db_session):
    """Admin can trigger due reminders sweep and dispatch alerts."""
    from app.models.application import Application, ApplicationReminder
    from app.models.scheme import Scheme
    from datetime import datetime, timezone, timedelta

    scheme = Scheme(
        id=uuid.uuid4(),
        scheme_name="Scholarship Scheme",
        category="Education",
        state_applicability="All India",
        department="Education",
        description="Scholarship",
        eligibility_summary="Students",
        official_source_url="https://scholarships.gov.in",
        official_application_url="https://scholarships.gov.in",
        status="active",
        is_active=True,
    )
    db_session.add(scheme)
    db_session.commit()

    app = Application(
        id=uuid.uuid4(),
        user_id=citizen_user["user"].id,
        scheme_id=scheme.id,
        status="Submitted",
    )
    db_session.add(app)
    db_session.commit()

    past_due = datetime.now(timezone.utc) - timedelta(hours=2)
    reminder = ApplicationReminder(
        id=uuid.uuid4(),
        application_id=app.id,
        user_id=citizen_user["user"].id,
        title="Submit Marks Memo",
        description="Submit physical memo at office",
        reminder_date=past_due,
        is_completed=False,
    )
    db_session.add(reminder)
    db_session.commit()

    # Citizen cannot trigger
    res_citizen = client.post("/api/v1/admin/reminders/process-due", headers=citizen_user["headers"])
    assert res_citizen.status_code == 403

    # Admin can trigger
    res_admin = client.post("/api/v1/admin/reminders/process-due", headers=admin_user["headers"])
    assert res_admin.status_code == 200
    data = res_admin.json()
    assert data["evaluated_count"] >= 1
    assert data["dispatched_count"] >= 1


def test_admin_schemes_pagination_beyond_50_items(client, admin_user, db_session):
    """Regression test: verify pagination, filtering, page navigation, and boundaries when >50 schemes exist."""
    created_ids = []
    try:
        # Create 55 test schemes
        for i in range(55):
            s_id = uuid.uuid4()
            created_ids.append(s_id)
            scheme = Scheme(
                id=s_id,
                scheme_name=f"test_page_scheme_{i:03d}",
                category="Agriculture" if i % 2 == 0 else "Education",
                department="Ministry of Testing",
                description=f"Pagination test scheme {i}",
                short_description=f"Short test {i}",
                state_applicability="All India",
                eligibility_summary="Citizens eligible for testing",
                official_source_url="https://test.gov.in",
                official_application_url="https://test.gov.in/apply",
                source_freshness_status="Verified Official Source",
                is_demo_data=False,
                is_active=True,
            )
            db_session.add(scheme)
        db_session.commit()

        # 1. Page 1 with page_size=25
        res_p1 = client.get(
            "/api/v1/admin/schemes?page=1&page_size=25",
            headers=admin_user["headers"],
        )
        assert res_p1.status_code == 200
        data_p1 = res_p1.json()
        assert data_p1["page"] == 1
        assert data_p1["page_size"] == 25
        assert data_p1["total"] >= 55
        assert len(data_p1["schemes"]) == 25
        assert data_p1["total_pages"] >= 3

        # 2. Page 2 with page_size=25
        res_p2 = client.get(
            "/api/v1/admin/schemes?page=2&page_size=25",
            headers=admin_user["headers"],
        )
        assert res_p2.status_code == 200
        data_p2 = res_p2.json()
        assert data_p2["page"] == 2
        assert len(data_p2["schemes"]) == 25

        # Verify no overlapping items between Page 1 and Page 2
        p1_ids = {s["id"] for s in data_p1["schemes"]}
        p2_ids = {s["id"] for s in data_p2["schemes"]}
        assert len(p1_ids.intersection(p2_ids)) == 0

        # 3. Page 3 with page_size=25
        res_p3 = client.get(
            "/api/v1/admin/schemes?page=3&page_size=25",
            headers=admin_user["headers"],
        )
        assert res_p3.status_code == 200
        data_p3 = res_p3.json()
        assert data_p3["page"] == 3
        assert len(data_p3["schemes"]) >= 5

        # 4. Search query filtering across pages
        res_search = client.get(
            "/api/v1/admin/schemes?query=test_page_scheme&page=1&page_size=20",
            headers=admin_user["headers"],
        )
        assert res_search.status_code == 200
        data_search = res_search.json()
        assert data_search["total"] == 55
        assert len(data_search["schemes"]) == 20
        assert data_search["total_pages"] == 3  # ceil(55 / 20) = 3

        # 5. Page size boundary check (page_size=100)
        res_max = client.get(
            "/api/v1/admin/schemes?page=1&page_size=100",
            headers=admin_user["headers"],
        )
        assert res_max.status_code == 200
        data_max = res_max.json()
        assert data_max["page"] == 1
        assert data_max["page_size"] == 100
        assert len(data_max["schemes"]) >= 55
    finally:
        # Reliable cleanup: delete test schemes by exact UUID
        for s_id in created_ids:
            db_session.query(Scheme).filter(Scheme.id == s_id).delete(synchronize_session=False)
        db_session.commit()

