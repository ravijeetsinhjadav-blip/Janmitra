import io
import uuid
import pytest
from app.models.document import DocumentProcessingStatus, DocumentMetadata
from app.models.scheme import Scheme
from app.models.profile import UserProfile
from app.core.config import settings

VALID_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n>>\n%%EOF"


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


class TestApplicationAssistanceModule:
    """Test suite for Phase 7.1 Application Assistance Module."""

    def test_prepare_application_successful_generation(self, client):
        """Generates comprehensive preparation guide, document statuses, and checklist for a scheme."""
        headers = get_auth_headers(client, "+919922000001")

        # 1. Fetch seeded schemes
        res_schemes = client.get("/api/v1/schemes")
        assert res_schemes.status_code == 200
        items = res_schemes.json()["items"]
        pm_kisan = next(s for s in items if "PM-KISAN" in s["scheme_name"])
        scheme_id = pm_kisan["id"]

        # 2. Call prepare endpoint
        res = client.post(
            f"/api/v1/assistance/schemes/{scheme_id}/prepare",
            json={"language": "en"},
            headers=headers,
        )
        assert res.status_code == 200, res.text
        data = res.json()

        assert data["scheme_id"] == scheme_id
        assert "PM-KISAN" in data["scheme_name"]
        assert "document_preparation_statuses" in data
        assert len(data["document_preparation_statuses"]) > 0
        assert "checklist" in data
        assert len(data["checklist"]) > 0
        assert "guide" in data
        assert len(data["guide"]["common_mistakes_to_avoid"]) > 0
        assert len(data["guide"]["submission_precautions"]) > 0
        assert len(data["guide"]["important_declarations"]) > 0
        assert len(data["guide"]["portal_steps"]) > 0
        assert data["official_application_url"].startswith("http")
        assert "not replace official government portals" in data["disclaimer"].lower()

    def test_missing_and_available_document_detection(self, client):
        """Distinguishes between uploaded vault documents and missing required documents."""
        headers = get_auth_headers(client, "+919922000002")

        # Upload a Domicile Certificate
        client.post(
            "/api/v1/documents/upload",
            files={"file": ("domicile.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")},
            data={"document_type": "domicile_certificate"},
            headers=headers,
        )

        res_schemes = client.get("/api/v1/schemes")
        pm_kisan = next(s for s in res_schemes.json()["items"] if "PM-KISAN" in s["scheme_name"])
        scheme_id = pm_kisan["id"]

        res = client.post(
            f"/api/v1/assistance/schemes/{scheme_id}/prepare",
            json={"language": "en"},
            headers=headers,
        )
        assert res.status_code == 200
        statuses = res.json()["document_preparation_statuses"]

        # Domicile should be ready/available, land/bank docs should be missing
        domicile_status = next((ds for ds in statuses if "domicile" in ds["document_name"].lower()), None)
        assert domicile_status is not None
        assert domicile_status["status"] in ["Ready for Application Preparation", "Available", "Manual Review Required"]

        missing_docs = [ds for ds in statuses if ds["status"] == "Missing"]
        assert len(missing_docs) > 0

    def test_ocr_failed_document_status_handling(self, db_session, client):
        """Documents with OCR_FAILED status are classified as 'Processing Failed'."""
        headers = get_auth_headers(client, "+919922000003")

        # Create user profile and scheme
        res_me = client.get("/api/v1/users/me", headers=headers)
        user_id = uuid.UUID(res_me.json()["id"])

        scheme = Scheme(
            scheme_name="Test Failed Scheme",
            category="Welfare",
            department="Department of Welfare",
            description="Testing failed document status",
            eligibility_summary="Testing",
            required_documents=["Caste Certificate"],
            eligibility_criteria=[],
            official_source_url="https://myscheme.gov.in/",
            official_application_url="https://myscheme.gov.in/apply",
            is_active=True,
        )
        db_session.add(scheme)
        db_session.commit()

        # Add OCR_FAILED document
        failed_doc = DocumentMetadata(
            user_id=user_id,
            document_type="Caste Certificate",
            original_filename="caste_corrupted.pdf",
            storage_reference="vault/corrupt.pdf",
            file_size=1024,
            mime_type="application/pdf",
            ocr_status=DocumentProcessingStatus.OCR_FAILED,
        )
        db_session.add(failed_doc)
        db_session.commit()

        res = client.post(
            f"/api/v1/assistance/schemes/{scheme.id}/prepare",
            json={"language": "en"},
            headers=headers,
        )
        assert res.status_code == 200
        statuses = res.json()["document_preparation_statuses"]
        caste_status = next(s for s in statuses if "caste" in s["document_name"].lower())
        assert caste_status["status"] == "Processing Failed"
        assert "failed" in caste_status["notes"].lower()

    def test_manual_review_document_status_handling(self, db_session, client):
        """Documents flagged for manual review receive 'Manual Review Required' status."""
        headers = get_auth_headers(client, "+919922000004")
        res_me = client.get("/api/v1/users/me", headers=headers)
        user_id = uuid.UUID(res_me.json()["id"])

        scheme = Scheme(
            scheme_name="Test Review Scheme",
            category="Welfare",
            department="Social Welfare",
            description="Testing review status",
            eligibility_summary="Testing",
            required_documents=["Income Certificate"],
            eligibility_criteria=[],
            official_source_url="https://myscheme.gov.in/",
            official_application_url="https://myscheme.gov.in/apply",
            is_active=True,
        )
        db_session.add(scheme)
        db_session.commit()

        review_doc = DocumentMetadata(
            user_id=user_id,
            document_type="Income Certificate",
            original_filename="income_blurry.pdf",
            storage_reference="vault/blurry.pdf",
            file_size=1024,
            mime_type="application/pdf",
            ocr_status=DocumentProcessingStatus.OCR_COMPLETED,
            manual_review_required=True,
            ocr_confidence=0.58,
        )
        db_session.add(review_doc)
        db_session.commit()

        res = client.post(
            f"/api/v1/assistance/schemes/{scheme.id}/prepare",
            json={"language": "en"},
            headers=headers,
        )
        assert res.status_code == 200
        statuses = res.json()["document_preparation_statuses"]
        inc_status = next(s for s in statuses if "income" in s["document_name"].lower())
        assert inc_status["status"] == "Manual Review Required"

    def test_checklist_item_toggle_and_state_persistence(self, client):
        """Citizens can toggle checklist items as completed and progress persists across requests."""
        headers = get_auth_headers(client, "+919922000005")

        res_schemes = client.get("/api/v1/schemes")
        scheme_id = res_schemes.json()["items"][0]["id"]

        # Initial preparation
        res_prep = client.post(
            f"/api/v1/assistance/schemes/{scheme_id}/prepare",
            json={"language": "en"},
            headers=headers,
        )
        assert res_prep.status_code == 200
        initial_checklist = res_prep.json()["checklist"]
        target_item = initial_checklist[-1]  # Pick last item (e.g. portal action)
        target_item_id = target_item["item_id"]

        # Toggle item to completed
        res_toggle = client.patch(
            f"/api/v1/assistance/schemes/{scheme_id}/checklist/{target_item_id}",
            json={"is_completed": True},
            headers=headers,
        )
        assert res_toggle.status_code == 200
        toggle_data = res_toggle.json()
        assert toggle_data["item_id"] == target_item_id
        assert toggle_data["is_completed"] is True
        assert toggle_data["completed_count"] >= 1
        assert "does not submit your application to the government" in toggle_data["message"].lower()

        # Fetch preparation again and verify item is now completed
        res_prep2 = client.post(
            f"/api/v1/assistance/schemes/{scheme_id}/prepare",
            json={"language": "en"},
            headers=headers,
        )
        assert res_prep2.status_code == 200
        checklist2 = res_prep2.json()["checklist"]
        updated_item = next(it for it in checklist2 if it["item_id"] == target_item_id)
        assert updated_item["is_completed"] is True

    def test_unauthorized_idor_access_blocked(self, client):
        """Non-owner citizens cannot toggle checklist items on another citizen's assessment."""
        headers_a = get_auth_headers(client, "+919922000006")
        headers_b = get_auth_headers(client, "+919922000007")

        res_schemes = client.get("/api/v1/schemes")
        scheme_id = res_schemes.json()["items"][0]["id"]

        # Citizen A prepares application
        client.post(
            f"/api/v1/assistance/schemes/{scheme_id}/prepare",
            headers=headers_a,
        )

        # Citizen B attempts to toggle Citizen A's item without prior assessment
        res_b = client.patch(
            f"/api/v1/assistance/schemes/{scheme_id}/checklist/action_visit_portal",
            json={"is_completed": True},
            headers=headers_b,
        )
        # Should return 404 because Citizen B has no assessment record for this scheme
        assert res_b.status_code in [403, 404]

    def test_invalid_scheme_id_returns_404(self, client):
        """Request with non-existent scheme UUID returns 404."""
        headers = get_auth_headers(client, "+919922000008")
        fake_id = uuid.uuid4()
        res = client.post(
            f"/api/v1/assistance/schemes/{fake_id}/prepare",
            headers=headers,
        )
        assert res.status_code == 404

    def test_multilingual_guidance_hindi_and_gujarati(self, client):
        """Application guide generates genuine multilingual instructions in Hindi and Gujarati."""
        headers = get_auth_headers(client, "+919922000009")
        res_schemes = client.get("/api/v1/schemes")
        pm_kisan = next(s for s in res_schemes.json()["items"] if "PM-KISAN" in s["scheme_name"])
        scheme_id = pm_kisan["id"]

        # 1. Hindi Assistance
        res_hi = client.post(
            f"/api/v1/assistance/schemes/{scheme_id}/prepare",
            json={"language": "hi"},
            headers=headers,
        )
        assert res_hi.status_code == 200
        guide_hi = res_hi.json()["guide"]
        assert guide_hi["language"] == "hi"
        # Verify Devanagari script presence
        assert any("\u0900" <= c <= "\u097F" for c in guide_hi["common_mistakes_to_avoid"][0])
        assert any("\u0900" <= c <= "\u097F" for c in guide_hi["submission_precautions"][0])

        # 2. Gujarati Assistance
        res_gu = client.post(
            f"/api/v1/assistance/schemes/{scheme_id}/prepare",
            json={"language": "gu"},
            headers=headers,
        )
        assert res_gu.status_code == 200
        guide_gu = res_gu.json()["guide"]
        assert guide_gu["language"] == "gu"
        # Verify Gujarati script presence
        assert any("\u0A80" <= c <= "\u0AFF" for c in guide_gu["common_mistakes_to_avoid"][0])
        assert any("\u0A80" <= c <= "\u0AFF" for c in guide_gu["submission_precautions"][0])

    def test_public_scheme_guide_endpoint(self, client):
        """Public scheme guide is retrievable without authentication."""
        res_schemes = client.get("/api/v1/schemes")
        scheme_id = res_schemes.json()["items"][0]["id"]

        res = client.get(f"/api/v1/assistance/schemes/{scheme_id}/guide?language=en")
        assert res.status_code == 200
        data = res.json()
        assert "common_mistakes_to_avoid" in data
        assert "supporting_documents_specs" in data
        assert len(data["common_mistakes_to_avoid"]) > 0
        assert len(data["portal_steps"]) > 0
