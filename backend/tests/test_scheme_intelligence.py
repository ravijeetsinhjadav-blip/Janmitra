import uuid
import pytest
from app.services.scheme_service import SchemeService
from app.db.seed_scheme_intelligence import (
    seed_scheme_intelligence_data,
    PM_KISAN_ID,
    POST_MATRIC_ID,
)


@pytest.fixture(autouse=True)
def seed_schemes(db_session):
    """Ensure demo schemes and scheme intelligence data are present in test db."""
    SchemeService.ensure_demo_schemes_seeded(db_session)
    seed_scheme_intelligence_data(db_session)


def get_admin_headers(client) -> dict:
    """Helper to authenticate as admin and return Bearer token."""
    email = "admin_intel_test@janmitra.gov.in"
    password = "AdminSecurePassword@2026!"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "confirm_password": password,
            "full_name": "Test Administrator",
            "mobile_number": "+919999900001",
        },
    )
    res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    if res.status_code == 200:
        token = res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {}


class TestSchemeIntelligenceCitizenEndpoints:
    """Test suite for citizen category rules, category documents, document guides, and beneficiary analytics."""

    def test_get_scheme_categories(self, client):
        res = client.get(f"/api/v1/schemes/{PM_KISAN_ID}/categories")
        assert res.status_code == 200
        cats = res.json()
        assert isinstance(cats, list)
        assert "All" in cats or "General" in cats

    def test_get_scheme_category_rules(self, client):
        res = client.get(f"/api/v1/schemes/{PM_KISAN_ID}/category-rules")
        assert res.status_code == 200
        rules = res.json()
        assert len(rules) >= 1
        assert any(r["field"] == "landholding" for r in rules)

    def test_get_scheme_category_rules_filtered(self, client):
        res = client.get(f"/api/v1/schemes/{PM_KISAN_ID}/category-rules?category=SC")
        assert res.status_code == 200
        rules = res.json()
        assert any(r["category"] in ["SC", "All"] for r in rules)

    def test_get_scheme_category_documents(self, client):
        res = client.get(f"/api/v1/schemes/{POST_MATRIC_ID}/documents?category=OBC")
        assert res.status_code == 200
        docs = res.json()
        assert len(docs) >= 1
        assert any(d["document_type"] == "non_creamy_layer" for d in docs)
        for d in docs:
            assert "has_guide" in d

    def test_list_document_guides(self, client):
        res = client.get("/api/v1/document-guides")
        assert res.status_code == 200
        guides = res.json()
        assert len(guides) >= 5
        types = [g["document_type"] for g in guides]
        assert "income_certificate" in types
        assert "caste_certificate" in types
        assert "ews_certificate" in types

    def test_get_document_guide_detail(self, client):
        res = client.get("/api/v1/document-guides/income_certificate")
        assert res.status_code == 200
        guide = res.json()
        assert guide["document_type"] == "income_certificate"
        assert "state_specific_authority" in guide
        assert "Maharashtra" in guide["state_specific_authority"]
        assert "Gujarat" in guide["state_specific_authority"]
        assert "online_steps" in guide
        assert "en" in guide["online_steps"]
        assert "hi" in guide["online_steps"]
        assert "gu" in guide["online_steps"]
        assert len(guide["required_supporting_documents"]) >= 3

    def test_document_guide_not_found(self, client):
        res = client.get("/api/v1/document-guides/non_existent_certificate")
        assert res.status_code == 404

    def test_evaluate_category_rules_on_demand_privacy(self, client):
        payload = {
            "category": "SC",
            "profile_data": {
                "annual_family_income": 200000,
                "age": 22,
                "landholding": 1.5,
            }
        }
        res = client.post(f"/api/v1/schemes/{POST_MATRIC_ID}/evaluate-category", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["category"] == "SC"
        assert data["is_category_eligible"] is True
        assert len(data["evaluations"]) >= 1
        assert "advisory_disclaimer" in data

    def test_get_scheme_analytics_dataset(self, client):
        res = client.get(f"/api/v1/schemes/{PM_KISAN_ID}/analytics")
        assert res.status_code == 200
        dataset = res.json()
        assert dataset["total_beneficiaries"] == 110000000
        assert dataset["is_published"] is True
        assert dataset["verification_status"] == "Verified"
        assert len(dataset["breakdowns"]) >= 3
        dimensions = set(b["dimension"] for b in dataset["breakdowns"])
        # Pillar 1 audit remediation: Fabricated caste breakdowns removed
        assert "caste_category" not in dimensions
        assert "gender" in dimensions
        assert "state" in dimensions
        assert dataset["report_title"] is not None
        assert dataset["geographic_scope"] == "National"
        assert dataset["metric_definition"] is not None
        assert "civic_disclaimer" in dataset


class TestSchemeIntelligenceAdminEndpoints:
    """Test suite for administrative analytics lifecycle and workflow."""

    def test_admin_analytics_lifecycle(self, client, db_session):
        # Promote test user to admin
        from app.models.user import User
        headers = get_admin_headers(client)
        admin_user = db_session.query(User).filter(User.email == "admin_intel_test@janmitra.gov.in").first()
        if admin_user:
            admin_user.role = "admin"
            db_session.commit()

        # 1. Admin gets all analytics for PM-KISAN
        res = client.get(f"/api/v1/admin/schemes/{PM_KISAN_ID}/analytics", headers=headers)
        assert res.status_code == 200
        datasets = res.json()
        assert len(datasets) >= 1
        dataset_id = datasets[0]["id"]

        # 2. Admin unpublishes dataset
        res_unpub = client.post(
            f"/api/v1/admin/schemes/{PM_KISAN_ID}/analytics/{dataset_id}/unpublish",
            headers=headers
        )
        assert res_unpub.status_code == 200
        assert res_unpub.json()["is_published"] is False

        # 3. Citizen request returns 404 since it's unpublished
        res_cit = client.get(f"/api/v1/schemes/{PM_KISAN_ID}/analytics")
        assert res_cit.status_code == 404

        # 4. Admin re-publishes dataset
        res_pub = client.post(
            f"/api/v1/admin/schemes/{PM_KISAN_ID}/analytics/{dataset_id}/publish",
            headers=headers
        )
        assert res_pub.status_code == 200
        assert res_pub.json()["is_published"] is True

        # 5. Citizen request succeeds again
        res_cit_again = client.get(f"/api/v1/schemes/{PM_KISAN_ID}/analytics")
        assert res_cit_again.status_code == 200

        # 6. Check audit log history
        res_hist = client.get(f"/api/v1/admin/schemes/{PM_KISAN_ID}/analytics/history", headers=headers)
        assert res_hist.status_code == 200
        logs = res_hist.json()
        assert len(logs) >= 1
