import io
import uuid
import pytest
from fastapi.testclient import TestClient

from app.models.user import User
from app.services.scheme_service import SchemeService
from app.db.seed_scheme_intelligence import (
    seed_scheme_intelligence_data,
    PM_KISAN_ID,
)

VALID_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n>>\n%%EOF"


@pytest.fixture(autouse=True)
def seed_test_schemes(db_session):
    """Ensure demo schemes and scheme intelligence data are seeded in test db."""
    SchemeService.ensure_demo_schemes_seeded(db_session)
    seed_scheme_intelligence_data(db_session)


class TestAuditWorkflowsEndToEnd:
    """Complete verification of real Citizen and Admin workflows as required by Section 8."""

    def test_complete_citizen_workflow(self, client: TestClient, db_session):
        # 1. Citizen Registration
        unique_suffix = uuid.uuid4().hex[:8]
        citizen_email = f"citizen_{unique_suffix}@example.com"
        citizen_phone = f"+9198{unique_suffix}"
        citizen_pw = f"CitP!{uuid.uuid4().hex[:12]}"
        reg_payload = {
            "email": citizen_email,
            "password": citizen_pw,
            "confirm_password": citizen_pw,
            "full_name": "Citizen Ramesh Kumar",
            "mobile_number": citizen_phone,
        }
        res_reg = client.post("/api/v1/auth/register", json=reg_payload)
        assert res_reg.status_code == 201, res_reg.text
        reg_data = res_reg.json()
        assert "access_token" in reg_data
        assert "csrf_token" in reg_data
        assert "access_token_cookie" in client.cookies
        assert "csrf_token_cookie" in client.cookies

        # 2. Citizen Login
        login_payload = {
            "email": citizen_email,
            "password": citizen_pw,
        }
        res_login = client.post("/api/v1/auth/login", json=login_payload)
        assert res_login.status_code == 200, res_login.text
        login_data = res_login.json()
        token = login_data["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        # 3. Scheme Discovery
        res_schemes = client.get("/api/v1/schemes", headers=auth_headers)
        assert res_schemes.status_code == 200, res_schemes.text
        items = res_schemes.json()["items"]
        assert len(items) >= 5
        pm_kisan = next(s for s in items if "PM-KISAN" in s["scheme_name"])
        scheme_id = pm_kisan["id"]

        # 4. Scheme Details
        res_detail = client.get(f"/api/v1/schemes/{scheme_id}", headers=auth_headers)
        assert res_detail.status_code == 200, res_detail.text
        detail_data = res_detail.json()
        assert detail_data["scheme_name"] == pm_kisan["scheme_name"]

        # 5. Category Selection & Rules
        res_cats = client.get(f"/api/v1/schemes/{scheme_id}/categories")
        assert res_cats.status_code == 200, res_cats.text
        res_rules = client.get(f"/api/v1/schemes/{scheme_id}/category-rules")
        assert res_rules.status_code == 200, res_rules.text
        rules = res_rules.json()
        assert len(rules) >= 1
        for rule in rules:
            assert "geographic_scope" in rule
            assert "verification_status" in rule

        # 6. Privacy-Preserving Category Eligibility Evaluation
        eval_payload = {
            "category": "All",
            "state": "Maharashtra",
            "citizen_data": {
                "landholding": 1.5,
                "is_institutional_landholder": False,
            },
        }
        res_eval = client.post(f"/api/v1/schemes/{scheme_id}/evaluate-category", json=eval_payload)
        assert res_eval.status_code == 200, res_eval.text
        eval_result = res_eval.json()
        assert eval_result["is_category_eligible"] is True
        assert "advisory_disclaimer" in eval_result

        # 7. Document Checklist (Aadhaar-free)
        res_docs = client.get(f"/api/v1/schemes/{scheme_id}/documents")
        assert res_docs.status_code == 200, res_docs.text
        docs = res_docs.json()
        doc_names = [d["document_name"].lower() for d in docs]
        for name in doc_names:
            assert "aadhaar" not in name, f"Aadhaar found in document requirement: {name}"

        # 8. Document Guide (Accurate, fee disclaimer, no commercial banks)
        res_guide = client.get("/api/v1/document-guides/bank_passbook")
        assert res_guide.status_code == 200, res_guide.text
        guide = res_guide.json()
        assert "Fee and processing time may vary" in guide["fees_and_timelines"]["fee_disclaimer"]
        assert "rbi.org.in" in guide["official_links"]["rbi_customer_services"]
        for link in guide["official_links"].values():
            assert "sbi.co.in" not in link

        # 9. Document Vault (Create document record without Aadhaar)
        file_payload = {
            "file": ("income_cert.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")
        }
        res_vault = client.post(
            "/api/v1/documents/upload",
            data={"document_type": "income_certificate"},
            files=file_payload,
            headers=auth_headers,
        )
        assert res_vault.status_code == 201, res_vault.text
        vault_data = res_vault.json()
        assert vault_data["document"]["document_type"] == "income_certificate"
        assert vault_data["document"]["id"] is not None

        # 10. Application Assistance / Readiness Assessment
        res_adv = client.post(
            f"/api/v1/advisory/schemes/{scheme_id}/assess-and-advise",
            json={"language": "hi"},
            headers=auth_headers,
        )
        assert res_adv.status_code == 200, res_adv.text
        advisory_data = res_adv.json()
        assert "readiness" in advisory_data
        assert "overall_readiness_score" in advisory_data["readiness"]
        assert "advisory" in advisory_data
        assert "citations" in advisory_data["advisory"]

    def test_complete_admin_workflow(self, client: TestClient, db_session):
        # Setup Admin User
        admin_suffix = uuid.uuid4().hex[:8]
        admin_email = f"admin_{admin_suffix}@janmitra.gov.in"
        admin_phone = f"+9197{admin_suffix}"
        admin_pw = f"AdmP!{uuid.uuid4().hex[:12]}"
        reg_payload = {
            "email": admin_email,
            "password": admin_pw,
            "confirm_password": admin_pw,
            "full_name": "Admin Official",
            "mobile_number": admin_phone,
        }
        res_reg = client.post("/api/v1/auth/register", json=reg_payload)
        assert res_reg.status_code == 201, res_reg.text
        admin_user = db_session.query(User).filter(User.email == admin_email).first()
        admin_user.role = "admin"
        db_session.commit()

        # 1. Admin Login
        login_payload = {
            "email": admin_email,
            "password": admin_pw,
        }
        res_login = client.post("/api/v1/auth/login", json=login_payload)
        assert res_login.status_code == 200
        admin_token = res_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 2. Scheme Management Check
        res_schemes = client.get("/api/v1/admin/schemes", headers=admin_headers)
        assert res_schemes.status_code == 200
        schemes = res_schemes.json()["schemes"]
        assert len(schemes) >= 1
        pm_kisan = next(s for s in schemes if "PM-KISAN" in s["scheme_name"])
        scheme_id = pm_kisan["id"]

        # 3. Category Rules Audit Check
        res_rules = client.get(f"/api/v1/schemes/{scheme_id}/category-rules")
        assert res_rules.status_code == 200
        rules = res_rules.json()
        for r in rules:
            assert r["verification_status"] in ("Verified", "Review Required", "Pending Verification")

        # 4. Document Guides Audit Check
        res_guides = client.get("/api/v1/document-guides")
        assert res_guides.status_code == 200
        guides = res_guides.json()
        assert len(guides) == 8

        # 5. Analytics Import with Full Provenance (Pillar 1)
        import_payload = {
            "source_name": "Department of Agriculture and Farmers Welfare",
            "source_url": "https://pmkisan.gov.in/Dashboard.aspx",
            "report_title": "PM-KISAN Operational Beneficiary Report Q4 2025-26",
            "reporting_period": "FY 2025-26 Q4",
            "geographic_scope": "National",
            "metric_type": "unique_farmer_households",
            "metric_definition": "Unique verified small & marginal farmer households credited via Aadhaar DBT",
            "total_beneficiaries": 110500000,
            "notes": "Verified against official MoA&FW open dashboard API.",
            "breakdowns": [
                {
                    "dimension": "gender",
                    "category_name": "Female Farmers",
                    "metric_value": 30000000,
                    "percentage": 27.15,
                },
                {
                    "dimension": "state",
                    "category_name": "Uttar Pradesh",
                    "metric_value": 26000000,
                    "percentage": 23.53,
                },
            ],
        }
        res_import = client.post(
            f"/api/v1/admin/schemes/{scheme_id}/analytics/import",
            json=import_payload,
            headers=admin_headers,
        )
        assert res_import.status_code in (200, 201), res_import.text
        imported = res_import.json()
        dataset_id = imported["id"]
        assert imported["report_title"] == "PM-KISAN Operational Beneficiary Report Q4 2025-26"
        assert imported["geographic_scope"] == "National"
        assert imported["metric_definition"] == "Unique verified small & marginal farmer households credited via Aadhaar DBT"
        # Newly imported dataset defaults to unpublished until explicitly approved/published
        assert imported["is_published"] is False

        # 6. Citizen Visibility before publish -> must not see unpublished dataset
        res_cit_before = client.get(f"/api/v1/schemes/{scheme_id}/analytics")
        # Should return currently active published dataset (not the unpublished import)
        if res_cit_before.status_code == 200:
            assert res_cit_before.json()["id"] != dataset_id

        # 7. Admin Publish
        res_pub = client.post(
            f"/api/v1/admin/schemes/{scheme_id}/analytics/{dataset_id}/publish",
            headers=admin_headers,
        )
        assert res_pub.status_code == 200
        assert res_pub.json()["is_published"] is True

        # 8. Citizen Visibility after publish -> must see verified published dataset
        res_cit_after = client.get(f"/api/v1/schemes/{scheme_id}/analytics")
        assert res_cit_after.status_code == 200
        cit_dataset = res_cit_after.json()
        assert cit_dataset["id"] == dataset_id
        assert cit_dataset["verification_status"] == "Verified"
        assert cit_dataset["total_beneficiaries"] == 110500000
        # Verify no fabricated caste breakdowns
        dims = set(b["dimension"] for b in cit_dataset["breakdowns"])
        assert "caste_category" not in dims
