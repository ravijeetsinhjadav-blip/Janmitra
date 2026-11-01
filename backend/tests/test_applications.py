import uuid
from datetime import datetime, timezone, timedelta
import pytest
from app.models.application import Application, APPLICATION_STATUSES
from app.models.scheme import Scheme
from app.schemas.application import ApplicationResponse


def get_auth_headers(client, mobile_number: str) -> dict:
    """Authenticate citizen via mock OTP and return Bearer headers."""
    res_otp = client.post("/api/v1/auth/send-otp", json={"mobile_number": mobile_number})
    otp = res_otp.json()["dev_otp"]
    res_verify = client.post(
        "/api/v1/auth/verify-otp",
        json={"mobile_number": mobile_number, "otp": otp},
    )
    token = res_verify.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def get_active_scheme_id(client) -> str:
    """Fetch an active seed scheme ID."""
    res = client.get("/api/v1/schemes")
    assert res.status_code == 200
    items = res.json()["items"]
    scheme = next(s for s in items if s["is_active"])
    return scheme["id"]


class TestApplicationTrackingModule:
    """Test suite for Subphase 8.1 Citizen Application Tracking Module."""

    def test_application_response_direct_orm_serialization(self, db_session):
        """Verifies that ApplicationResponse serializes an ORM Application and eager-loaded Scheme via AliasPath."""
        scheme = Scheme(
            id=uuid.uuid4(),
            scheme_name="Test Direct ORM Scheme",
            description="Testing AliasPath ORM serialization",
            category="Welfare",
            department="Ministry of Social Justice",
            official_source_url="https://welfare.gov.in",
            official_application_url="https://welfare.gov.in/apply",
            eligibility_summary="Eligible citizens",
            is_active=True,
        )
        db_session.add(scheme)
        db_session.commit()

        now = datetime.now(timezone.utc)
        app = Application(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            scheme_id=scheme.id,
            application_reference_number="DIR-ORM-001",
            submission_date=now,
            status="Submitted",
        )
        app.scheme = scheme  # Eager-loaded ORM relationship
        db_session.add(app)
        db_session.commit()
        db_session.refresh(app)

        resp = ApplicationResponse.model_validate(app)
        assert resp.id == app.id
        assert resp.scheme_id == scheme.id
        assert resp.scheme_name == "Test Direct ORM Scheme"
        assert resp.category == "Welfare"
        assert resp.department == "Ministry of Social Justice"
        assert resp.official_application_url == "https://welfare.gov.in/apply"
        assert resp.application_reference_number == "DIR-ORM-001"
        assert resp.status == "Submitted"

    def test_create_application_success(self, client):
        """Citizens can register an application submitted on a government portal."""
        headers = get_auth_headers(client, "+919933000001")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()

        res = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "PMK-2026-998811",
                "reference_number_not_issued": False,
            },
        )
        assert res.status_code == 201, res.text
        data = res.json()
        assert data["scheme_id"] == scheme_id
        assert data["status"] == "Submitted"
        assert data["application_reference_number"] == "PMK-2026-998811"
        assert data["scheme_name"] is not None
        assert data["official_application_url"] is not None

    def test_create_application_without_ref_num_success(self, client):
        """Citizens can submit when portal did not issue a reference number by asserting reference_number_not_issued."""
        headers = get_auth_headers(client, "+919933000002")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()

        res = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": None,
                "reference_number_not_issued": True,
            },
        )
        assert res.status_code == 201, res.text
        data = res.json()
        assert data["application_reference_number"] is None
        assert data["status"] == "Submitted"

    def test_create_application_missing_ref_num_fails(self, client):
        """Missing reference number without explicit reference_number_not_issued declaration fails with HTTP 422."""
        headers = get_auth_headers(client, "+919933000003")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        res = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": None,
                "reference_number_not_issued": False,
            },
        )
        assert res.status_code == 422
        assert "reference number is required" in res.text

    def test_create_application_contradictory_ref_payload_fails(self, client):
        """Providing a reference number while setting reference_number_not_issued=True fails with HTTP 422."""
        headers = get_auth_headers(client, "+919933000004")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        res = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "REF-CONTRADICT-999",
                "reference_number_not_issued": True,
            },
        )
        assert res.status_code == 422
        assert "Contradictory reference-number payload" in res.text

    def test_create_application_initial_status_rejected_422(self, client):
        """Extra fields like status are forbidden on creation (initial status is always 'Submitted')."""
        headers = get_auth_headers(client, "+919933000005")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        res = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "REF-005",
                "status": "Approved",  # Cannot self-assign status
            },
        )
        assert res.status_code == 422
        assert "extra_forbidden" in res.text or "extra fields not permitted" in res.text.lower()

    def test_create_application_extra_user_id_rejected_422(self, client):
        """User ID cannot be passed in request body (strictly derived from JWT token)."""
        headers = get_auth_headers(client, "+919933000006")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        res = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "REF-006",
                "user_id": str(uuid.uuid4()),  # Spoofed user ID
            },
        )
        assert res.status_code == 422
        assert "extra_forbidden" in res.text or "extra fields not permitted" in res.text.lower()

    def test_create_application_naive_datetime_fails_422(self, client):
        """Naive datetime inputs lacking explicit timezone offset are rejected with HTTP 422."""
        headers = get_auth_headers(client, "+919933000007")
        scheme_id = get_active_scheme_id(client)

        res = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": "2026-10-31T12:00:00",  # No Z or offset
                "application_reference_number": "REF-007",
            },
        )
        assert res.status_code == 422
        assert "timezone offset" in res.text

    def test_create_application_future_datetime_fails_422(self, client):
        """Submission dates in the future beyond clock-skew tolerance are rejected with HTTP 422."""
        headers = get_auth_headers(client, "+919933000008")
        scheme_id = get_active_scheme_id(client)
        future_date = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()

        res = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": future_date,
                "application_reference_number": "REF-008",
            },
        )
        assert res.status_code == 422
        assert "cannot be in the future" in res.text

    def test_create_application_invalid_scheme_uuid_404(self, client):
        """Attempting to track an application for a non-existent scheme returns HTTP 404."""
        headers = get_auth_headers(client, "+919933000009")
        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        res = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": str(uuid.uuid4()),
                "submission_date": sub_date,
                "application_reference_number": "REF-009",
            },
        )
        assert res.status_code == 404
        assert "Government scheme not found" in res.text

    def test_create_application_inactive_scheme_fails_400(self, client, db_session):
        """Attempting to track a new application for an inactive scheme returns HTTP 400."""
        headers = get_auth_headers(client, "+919933000010")
        inactive_scheme = Scheme(
            id=uuid.uuid4(),
            scheme_name="Discontinued Farmer Support 2024",
            description="Historical scheme no longer accepting new applications.",
            category="Agriculture",
            department="Department of Agriculture",
            official_source_url="https://agriculture.gov.in/closed",
            official_application_url="https://agriculture.gov.in/closed-portal",
            eligibility_summary="No longer active",
            is_active=False,
        )
        db_session.add(inactive_scheme)
        db_session.commit()

        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        res = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": str(inactive_scheme.id),
                "submission_date": sub_date,
                "application_reference_number": "REF-010",
            },
        )
        assert res.status_code == 400
        assert "currently inactive" in res.text

    def test_list_applications_pagination_and_tenant_isolation(self, client):
        """Applications are strictly tenant-isolated and support pagination."""
        headers_user1 = get_auth_headers(client, "+919933000011")
        headers_user2 = get_auth_headers(client, "+919933000012")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        # User 1 creates 3 applications
        for i in range(3):
            res = client.post(
                "/api/v1/applications",
                headers=headers_user1,
                json={
                    "scheme_id": scheme_id,
                    "submission_date": sub_date,
                    "application_reference_number": f"U1-REF-{i}",
                },
            )
            assert res.status_code == 201

        # User 2 creates 1 application
        res2 = client.post(
            "/api/v1/applications",
            headers=headers_user2,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "U2-REF-99",
            },
        )
        assert res2.status_code == 201

        # User 1 lists page 1 with page_size=2
        res_list = client.get("/api/v1/applications?page=1&page_size=2", headers=headers_user1)
        assert res_list.status_code == 200
        data1 = res_list.json()
        assert data1["total"] == 3
        assert len(data1["applications"]) == 2
        assert data1["total_pages"] == 2
        assert all("U1-REF" in a["application_reference_number"] for a in data1["applications"])

        # User 2 lists applications -> only sees 1 application
        res_list2 = client.get("/api/v1/applications", headers=headers_user2)
        assert res_list2.status_code == 200
        data2 = res_list2.json()
        assert data2["total"] == 1
        assert data2["applications"][0]["application_reference_number"] == "U2-REF-99"

    def test_list_applications_status_filter(self, client):
        """Filtering by status returns only matching applications."""
        headers = get_auth_headers(client, "+919933000013")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        res1 = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "FILTER-APP-1",
            },
        )
        app1_id = res1.json()["id"]

        # Update app1 to 'Under Review'
        res_patch = client.patch(
            f"/api/v1/applications/{app1_id}",
            headers=headers,
            json={"status": "Under Review"},
        )
        assert res_patch.status_code == 200

        # Create app2 which defaults to 'Submitted'
        client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "FILTER-APP-2",
            },
        )

        # Filter by 'Under Review'
        res_filter = client.get("/api/v1/applications?status=Under%20Review", headers=headers)
        assert res_filter.status_code == 200
        items = res_filter.json()["applications"]
        assert len(items) == 1
        assert items[0]["id"] == app1_id
        assert items[0]["status"] == "Under Review"

    def test_list_applications_invalid_page_fails_422(self, client):
        """Querying with page < 1 returns HTTP 422."""
        headers = get_auth_headers(client, "+919933000014")
        res = client.get("/api/v1/applications?page=0", headers=headers)
        assert res.status_code == 422

    def test_list_applications_invalid_page_size_fails_422(self, client):
        """Querying with page_size < 1 or > 100 returns HTTP 422."""
        headers = get_auth_headers(client, "+919933000015")
        res_zero = client.get("/api/v1/applications?page_size=0", headers=headers)
        assert res_zero.status_code == 422

        res_huge = client.get("/api/v1/applications?page_size=101", headers=headers)
        assert res_huge.status_code == 422

    def test_list_applications_total_pages_calculation_zero_and_multiple(self, client):
        """Empty lists yield total=0 and total_pages=0 cleanly."""
        headers = get_auth_headers(client, "+919933000016")
        res = client.get("/api/v1/applications", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 0
        assert data["total_pages"] == 0
        assert data["applications"] == []

    def test_get_application_detail_owner_success(self, client):
        """Citizen can fetch detail for an owned application."""
        headers = get_auth_headers(client, "+919933000017")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        res_create = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "DETAIL-APP-1",
            },
        )
        app_id = res_create.json()["id"]

        res = client.get(f"/api/v1/applications/{app_id}", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == app_id
        assert data["application_reference_number"] == "DETAIL-APP-1"
        assert data["scheme_name"] is not None
        assert data["official_application_url"] is not None

    def test_get_application_detail_cross_user_idor_404(self, client):
        """Cross-user GET returns identical HTTP 404 as non-existent UUID (zero enumeration)."""
        headers1 = get_auth_headers(client, "+919933000018")
        headers2 = get_auth_headers(client, "+919933000019")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        res_create = client.post(
            "/api/v1/applications",
            headers=headers1,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "USER1-SECRET-APP",
            },
        )
        app_id = res_create.json()["id"]

        # User 2 attempts to query User 1's application ID
        res_cross = client.get(f"/api/v1/applications/{app_id}", headers=headers2)
        assert res_cross.status_code == 404
        assert "Application tracking record not found" in res_cross.text

    def test_existing_tracking_on_inactive_scheme_accessible(self, client, db_session):
        """Existing tracking entries remain readable and updatable even if the scheme becomes inactive later."""
        headers = get_auth_headers(client, "+919933000020")
        scheme = Scheme(
            id=uuid.uuid4(),
            scheme_name="Temporary Flood Relief 2025",
            description="Active during application submission",
            category="Disaster Management",
            department="Revenue Department",
            official_source_url="https://relief.gov.in",
            official_application_url="https://relief.gov.in/apply",
            eligibility_summary="Flood affected citizens",
            is_active=True,
        )
        db_session.add(scheme)
        db_session.commit()

        # Citizen registers application while active
        sub_date = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        res_create = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": str(scheme.id),
                "submission_date": sub_date,
                "application_reference_number": "RELIEF-APP-2025",
            },
        )
        assert res_create.status_code == 201
        app_id = res_create.json()["id"]

        # Government closes the scheme
        scheme.is_active = False
        db_session.commit()

        # Citizen can still fetch application details
        res_get = client.get(f"/api/v1/applications/{app_id}", headers=headers)
        assert res_get.status_code == 200
        assert res_get.json()["scheme_name"] == "Temporary Flood Relief 2025"

        # Citizen can still update status
        res_patch = client.patch(
            f"/api/v1/applications/{app_id}",
            headers=headers,
            json={"status": "Approved"},
        )
        assert res_patch.status_code == 200
        assert res_patch.json()["status"] == "Approved"

    def test_patch_application_status_success(self, client):
        """Citizen can update status to a valid stage."""
        headers = get_auth_headers(client, "+919933000021")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()

        res_create = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "PATCH-STATUS-APP",
            },
        )
        app_id = res_create.json()["id"]

        res_patch = client.patch(
            f"/api/v1/applications/{app_id}",
            headers=headers,
            json={"status": "Document Verification"},
        )
        assert res_patch.status_code == 200
        data = res_patch.json()
        assert data["status"] == "Document Verification"
        assert data["application_reference_number"] == "PATCH-STATUS-APP"

    def test_patch_status_null_fails_422(self, client):
        """Explicitly passing status=null in PATCH payload is rejected with HTTP 422."""
        headers = get_auth_headers(client, "+919933000022")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        res_create = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "PATCH-NULL-STAT",
            },
        )
        app_id = res_create.json()["id"]

        res_patch = client.patch(
            f"/api/v1/applications/{app_id}",
            headers=headers,
            json={"status": None},
        )
        assert res_patch.status_code == 422
        assert "Status cannot be null" in res_patch.text or "status" in res_patch.text

    def test_patch_submission_date_null_fails_422(self, client):
        """Explicitly passing submission_date=null in PATCH payload is rejected with HTTP 422."""
        headers = get_auth_headers(client, "+919933000023")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        res_create = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "PATCH-NULL-DATE",
            },
        )
        app_id = res_create.json()["id"]

        res_patch = client.patch(
            f"/api/v1/applications/{app_id}",
            headers=headers,
            json={"submission_date": None},
        )
        assert res_patch.status_code == 422
        assert "Submission date cannot be null" in res_patch.text

    def test_patch_empty_body_fails_422(self, client):
        """Sending an empty PATCH body {} returns HTTP 422."""
        headers = get_auth_headers(client, "+919933000024")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        res_create = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "PATCH-EMPTY-APP",
            },
        )
        app_id = res_create.json()["id"]

        res_patch = client.patch(
            f"/api/v1/applications/{app_id}",
            headers=headers,
            json={},
        )
        assert res_patch.status_code == 422
        assert "PATCH payload cannot be empty" in res_patch.text

    def test_patch_extra_field_forbidden_422(self, client):
        """Extra fields like user_id or notes are rejected with HTTP 422."""
        headers = get_auth_headers(client, "+919933000025")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        res_create = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "PATCH-EXTRA-APP",
            },
        )
        app_id = res_create.json()["id"]

        res_patch = client.patch(
            f"/api/v1/applications/{app_id}",
            headers=headers,
            json={"notes": "Illegal extra note field"},
        )
        assert res_patch.status_code == 422
        assert "extra_forbidden" in res_patch.text or "extra fields not permitted" in res_patch.text.lower()

    def test_patch_clear_flag_alone_fails_422(self, client):
        """Sending clear_reference_number=true alone without substantive fields returns HTTP 422."""
        headers = get_auth_headers(client, "+919933000026")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        res_create = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "PATCH-CLEAR-FLAG-ONLY",
            },
        )
        app_id = res_create.json()["id"]

        res_patch = client.patch(
            f"/api/v1/applications/{app_id}",
            headers=headers,
            json={"clear_reference_number": True},
        )
        assert res_patch.status_code == 422

    def test_patch_clear_ref_without_flag_fails_422(self, client):
        """Setting application_reference_number=null without clear_reference_number=true returns HTTP 422."""
        headers = get_auth_headers(client, "+919933000027")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        res_create = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "PATCH-CLEAR-NO-FLAG",
            },
        )
        app_id = res_create.json()["id"]

        res_patch = client.patch(
            f"/api/v1/applications/{app_id}",
            headers=headers,
            json={"application_reference_number": None},
        )
        assert res_patch.status_code == 422
        assert "Cannot clear application_reference_number" in res_patch.text

    def test_patch_non_empty_ref_with_clear_flag_fails_422(self, client):
        """Supplying both a non-empty reference number and clear_reference_number=true returns HTTP 422."""
        headers = get_auth_headers(client, "+919933000028")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        res_create = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "PATCH-CONTRADICT-APP",
            },
        )
        app_id = res_create.json()["id"]

        res_patch = client.patch(
            f"/api/v1/applications/{app_id}",
            headers=headers,
            json={
                "application_reference_number": "NEW-REF-999",
                "clear_reference_number": True,
            },
        )
        assert res_patch.status_code == 422
        assert "Cannot provide both a non-empty application_reference_number and clear_reference_number=true" in res_patch.text

    def test_patch_clear_ref_with_flag_success(self, client):
        """Supplying application_reference_number=null with clear_reference_number=true clears the reference number."""
        headers = get_auth_headers(client, "+919933000029")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        res_create = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "WILL-BE-CLEARED",
            },
        )
        app_id = res_create.json()["id"]

        res_patch = client.patch(
            f"/api/v1/applications/{app_id}",
            headers=headers,
            json={
                "application_reference_number": None,
                "clear_reference_number": True,
            },
        )
        assert res_patch.status_code == 200
        assert res_patch.json()["application_reference_number"] is None

    def test_patch_omitted_fields_remain_unchanged(self, client):
        """Updating only the status preserves existing reference number and submission date."""
        headers = get_auth_headers(client, "+919933000030")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()

        res_create = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "PRESERVE-REF-99",
            },
        )
        app_id = res_create.json()["id"]
        original_sub_date = res_create.json()["submission_date"]

        res_patch = client.patch(
            f"/api/v1/applications/{app_id}",
            headers=headers,
            json={"status": "Under Review"},
        )
        assert res_patch.status_code == 200
        data = res_patch.json()
        assert data["status"] == "Under Review"
        assert data["application_reference_number"] == "PRESERVE-REF-99"
        assert data["submission_date"] == original_sub_date

    def test_patch_cross_user_idor_404(self, client):
        """Attempting to update another citizen's application returns HTTP 404."""
        headers1 = get_auth_headers(client, "+919933000031")
        headers2 = get_auth_headers(client, "+919933000032")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        res_create = client.post(
            "/api/v1/applications",
            headers=headers1,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "USER1-APP",
            },
        )
        app_id = res_create.json()["id"]

        res_patch = client.patch(
            f"/api/v1/applications/{app_id}",
            headers=headers2,
            json={"status": "Approved"},
        )
        assert res_patch.status_code == 404
        assert "Application tracking record not found" in res_patch.text

    def test_delete_application_owner_success(self, client):
        """Owner can delete a tracking record and receive the statutory disclaimer."""
        headers = get_auth_headers(client, "+919933000033")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        res_create = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "DELETE-ME-APP",
            },
        )
        app_id = res_create.json()["id"]

        res_del = client.delete(f"/api/v1/applications/{app_id}", headers=headers)
        assert res_del.status_code == 200
        data = res_del.json()
        assert data["id"] == app_id
        assert "does NOT withdraw, cancel, or modify your formal application" in data["message"]

        # Subsequent GET yields 404
        res_get = client.get(f"/api/v1/applications/{app_id}", headers=headers)
        assert res_get.status_code == 404

    def test_delete_application_cross_user_idor_404(self, client):
        """Attempting to delete another citizen's application returns HTTP 404."""
        headers1 = get_auth_headers(client, "+919933000034")
        headers2 = get_auth_headers(client, "+919933000035")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        res_create = client.post(
            "/api/v1/applications",
            headers=headers1,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "USER1-DO-NOT-DELETE",
            },
        )
        app_id = res_create.json()["id"]

        res_del = client.delete(f"/api/v1/applications/{app_id}", headers=headers2)
        assert res_del.status_code == 404
        assert "Application tracking record not found" in res_del.text

        # Record still intact for User 1
        res_get = client.get(f"/api/v1/applications/{app_id}", headers=headers1)
        assert res_get.status_code == 200

    def test_unauthenticated_requests_fail_401(self, client):
        """All application tracking routes require Bearer authentication."""
        res_post = client.post("/api/v1/applications", json={})
        assert res_post.status_code == 401

        res_get = client.get("/api/v1/applications")
        assert res_get.status_code == 401

        fake_id = str(uuid.uuid4())
        res_detail = client.get(f"/api/v1/applications/{fake_id}")
        assert res_detail.status_code == 401

        res_patch = client.patch(f"/api/v1/applications/{fake_id}", json={})
        assert res_patch.status_code == 401

        res_delete = client.delete(f"/api/v1/applications/{fake_id}")
        assert res_delete.status_code == 401

    def test_patch_submission_date_success(self, client):
        """PATCH successfully updates submission_date with a valid timezone-aware datetime."""
        headers = get_auth_headers(client, "+919933000041")
        scheme_id = get_active_scheme_id(client)
        initial_sub_date = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()

        res_create = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": initial_sub_date,
                "application_reference_number": "PATCH-DATE-TEST",
            },
        )
        assert res_create.status_code == 201
        app_id = res_create.json()["id"]

        new_sub_date = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        res_patch = client.patch(
            f"/api/v1/applications/{app_id}",
            headers=headers,
            json={"submission_date": new_sub_date},
        )
        assert res_patch.status_code == 200
        data = res_patch.json()
        assert data["submission_date"] is not None

        # Verify persisted date by fetching again
        res_get = client.get(f"/api/v1/applications/{app_id}", headers=headers)
        assert res_get.status_code == 200
        assert res_get.json()["submission_date"] == data["submission_date"]

    def test_patch_naive_submission_date_fails_422(self, client):
        """PATCH rejects a naive datetime string without timezone offset with HTTP 422."""
        headers = get_auth_headers(client, "+919933000042")
        scheme_id = get_active_scheme_id(client)
        initial_sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        res_create = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": initial_sub_date,
                "application_reference_number": "PATCH-NAIVE-DATE",
            },
        )
        app_id = res_create.json()["id"]

        res_patch = client.patch(
            f"/api/v1/applications/{app_id}",
            headers=headers,
            json={"submission_date": "2026-10-31T10:30:00"},  # Naive without Z or offset
        )
        assert res_patch.status_code == 422
        assert "timezone offset" in res_patch.text

    def test_patch_future_submission_date_fails_422(self, client):
        """PATCH rejects a submission date beyond the allowed future clock-skew tolerance with HTTP 422."""
        headers = get_auth_headers(client, "+919933000043")
        scheme_id = get_active_scheme_id(client)
        initial_sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        res_create = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": initial_sub_date,
                "application_reference_number": "PATCH-FUTURE-DATE",
            },
        )
        app_id = res_create.json()["id"]

        future_sub_date = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        res_patch = client.patch(
            f"/api/v1/applications/{app_id}",
            headers=headers,
            json={"submission_date": future_sub_date},
        )
        assert res_patch.status_code == 422
        assert "cannot be in the future" in res_patch.text

    def test_patch_application_reference_number_success(self, client):
        """PATCH successfully updates application_reference_number to a new non-empty value."""
        headers = get_auth_headers(client, "+919933000044")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        res_create = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "OLD-REF-111",
            },
        )
        app_id = res_create.json()["id"]

        res_patch = client.patch(
            f"/api/v1/applications/{app_id}",
            headers=headers,
            json={"application_reference_number": "  NEW-ACK-222  "},
        )
        assert res_patch.status_code == 200
        data = res_patch.json()
        assert data["application_reference_number"] == "NEW-ACK-222"

        # Verify persisted in database
        res_get = client.get(f"/api/v1/applications/{app_id}", headers=headers)
        assert res_get.status_code == 200
        assert res_get.json()["application_reference_number"] == "NEW-ACK-222"

    def test_patch_invalid_status_string_fails_422(self, client):
        """PATCH rejects an invalid status string not in APPLICATION_STATUSES with HTTP 422."""
        headers = get_auth_headers(client, "+919933000045")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        res_create = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "PATCH-INV-STAT",
            },
        )
        app_id = res_create.json()["id"]

        res_patch = client.patch(
            f"/api/v1/applications/{app_id}",
            headers=headers,
            json={"status": "ArbitraryNonExistentStatus"},
        )
        assert res_patch.status_code == 422
        assert "Invalid status" in res_patch.text

    def test_list_applications_invalid_status_filter_fails_422(self, client):
        """GET /applications rejects an invalid status query parameter with HTTP 422."""
        headers = get_auth_headers(client, "+919933000046")
        res = client.get("/api/v1/applications?status=UnknownFakeStatus", headers=headers)
        assert res.status_code == 422
        assert "Invalid status" in res.text

    def test_list_applications_scheme_id_filter_success(self, client, db_session):
        """GET /applications correctly filters applications by scheme_id."""
        headers = get_auth_headers(client, "+919933000047")
        active_scheme_1 = get_active_scheme_id(client)

        scheme_2 = Scheme(
            id=uuid.uuid4(),
            scheme_name="Second Active Scheme For Filtering",
            description="Testing scheme_id filter parameter",
            category="Education",
            department="Department of Higher Education",
            official_source_url="https://education.gov.in",
            official_application_url="https://education.gov.in/apply",
            eligibility_summary="Eligible students",
            is_active=True,
        )
        db_session.add(scheme_2)
        db_session.commit()

        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        # Create application for Scheme 1
        client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": active_scheme_1,
                "submission_date": sub_date,
                "application_reference_number": "SCHEME1-APP",
            },
        )

        # Create application for Scheme 2
        client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": str(scheme_2.id),
                "submission_date": sub_date,
                "application_reference_number": "SCHEME2-APP",
            },
        )

        # Query filtering by Scheme 2 ID
        res_filter = client.get(f"/api/v1/applications?scheme_id={scheme_2.id}", headers=headers)
        assert res_filter.status_code == 200
        data = res_filter.json()
        assert data["total"] == 1
        assert len(data["applications"]) == 1
        assert data["applications"][0]["scheme_id"] == str(scheme_2.id)
        assert data["applications"][0]["application_reference_number"] == "SCHEME2-APP"

    def test_create_application_ref_num_exceeding_100_chars_fails_422(self, client):
        """POST rejects a reference number longer than 100 characters with HTTP 422."""
        headers = get_auth_headers(client, "+919933000048")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        oversized_ref = "A" * 101
        res = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": oversized_ref,
            },
        )
        assert res.status_code == 422
        assert "at most 100 characters" in res.text or "string_too_long" in res.text

    def test_patch_ref_num_exceeding_100_chars_fails_422(self, client):
        """PATCH rejects a reference number longer than 100 characters with HTTP 422."""
        headers = get_auth_headers(client, "+919933000049")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        res_create = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "VALID-SHORT-REF",
            },
        )
        app_id = res_create.json()["id"]

        oversized_ref = "B" * 101
        res_patch = client.patch(
            f"/api/v1/applications/{app_id}",
            headers=headers,
            json={"application_reference_number": oversized_ref},
        )
        assert res_patch.status_code == 422
        assert "at most 100 characters" in res_patch.text or "string_too_long" in res_patch.text

    def test_patch_clear_ref_with_whitespace_stores_null_success(self, client):
        """PATCH accepts whitespace-only reference when clear_reference_number=true and actually stores NULL."""
        headers = get_auth_headers(client, "+919933000050")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        res_create = client.post(
            "/api/v1/applications",
            headers=headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "REF-TO-CLEAR-WS",
            },
        )
        app_id = res_create.json()["id"]

        # Pass whitespace with clear_reference_number=true
        res_patch = client.patch(
            f"/api/v1/applications/{app_id}",
            headers=headers,
            json={
                "application_reference_number": "   ",
                "clear_reference_number": True,
            },
        )
        assert res_patch.status_code == 200
        data = res_patch.json()
        assert data["application_reference_number"] is None

        # Verify persisted state via GET
        res_get = client.get(f"/api/v1/applications/{app_id}", headers=headers)
        assert res_get.status_code == 200
        assert res_get.json()["application_reference_number"] is None

    def test_admin_list_applications_is_scoped_to_admin_user(self, client, db_session):
        """Admin callers are authenticated under shared citizen dependency but strictly scoped to their own records."""
        from app.models.user import User
        from app.core.security import create_access_token

        # Citizen creates a tracking application
        citizen_headers = get_auth_headers(client, "+919933000051")
        scheme_id = get_active_scheme_id(client)
        sub_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        res_create = client.post(
            "/api/v1/applications",
            headers=citizen_headers,
            json={
                "scheme_id": scheme_id,
                "submission_date": sub_date,
                "application_reference_number": "CITIZEN-APP-001",
            },
        )
        assert res_create.status_code == 201
        citizen_app_id = res_create.json()["id"]

        # Authenticate an actual Admin account
        admin = User(
            id=uuid.uuid4(),
            mobile_number="+919999900001",
            role="admin",
            is_active=True,
        )
        db_session.add(admin)
        db_session.commit()

        token = create_access_token(user_id=str(admin.id), role="admin")
        admin_headers = {"Authorization": f"Bearer {token}"}

        # Admin calls GET /api/v1/applications -> HTTP 200 with isolated zero records
        res_list = client.get("/api/v1/applications", headers=admin_headers)
        assert res_list.status_code == 200
        data = res_list.json()
        assert data["total"] == 0
        assert data["applications"] == []

        # Admin attempts to read citizen's application -> HTTP 404 (strict ownership enforced)
        res_detail = client.get(f"/api/v1/applications/{citizen_app_id}", headers=admin_headers)
        assert res_detail.status_code == 404
        assert res_detail.json()["detail"] == "Application tracking record not found."
