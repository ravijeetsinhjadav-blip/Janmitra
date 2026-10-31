import io
import uuid
from pathlib import Path
import pytest
from app.models.document import DocumentProcessingStatus, DocumentMetadata
from app.models.scheme import Scheme
from app.services.storage_service import storage_service
from app.core.config import settings


def get_auth_headers(client, mobile_number: str) -> dict:
    """Helper to authenticate a citizen via mock OTP."""
    res_otp = client.post("/api/v1/auth/send-otp", json={"mobile_number": mobile_number})
    otp = res_otp.json()["dev_otp"]
    res_verify = client.post(
        "/api/v1/auth/verify-otp",
        json={"mobile_number": mobile_number, "otp": otp},
    )
    token = res_verify.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# Sample binary files with valid magic bytes
VALID_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\ntrailer\n<<\n>>\n%%EOF"
VALID_JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb" + (b"\x00" * 50) + b"\xff\xd9"
VALID_PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"


class TestDocumentVaultAndOCR:
    """Comprehensive test suite for Phase 5 Document Vault & OCR Pipeline."""

    def test_upload_valid_pdf_document(self, client):
        """Citizens can upload valid PDF certificates and get automated OCR extraction."""
        headers = get_auth_headers(client, "+919900000001")
        file_payload = {
            "file": ("income_cert.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")
        }
        data_payload = {
            "document_type": "income_certificate"
        }

        response = client.post(
            "/api/v1/documents/upload",
            files=file_payload,
            data=data_payload,
            headers=headers,
        )

        assert response.status_code == 201, response.text
        data = response.json()
        doc = data["document"]
        assert doc["document_type"] == "income_certificate"
        assert doc["original_filename"] == "income_cert.pdf"
        assert doc["mime_type"] == "application/pdf"
        assert doc["file_size"] == len(VALID_PDF_BYTES)
        assert doc["ocr_status"] == DocumentProcessingStatus.OCR_COMPLETED
        assert doc["manual_review_required"] is False
        assert doc["ocr_confidence"] >= 0.70
        assert "INCOME CERTIFICATE" in doc["ocr_extracted_text"]
        assert "storage_reference" in doc

        # Verify file exists on local storage disk
        resolved_path = storage_service.resolve_path(doc["storage_reference"])
        assert resolved_path.exists()
        assert resolved_path.read_bytes() == VALID_PDF_BYTES

    def test_upload_valid_jpeg_and_png(self, client):
        """Citizens can upload valid JPG and PNG document images."""
        headers = get_auth_headers(client, "+919900000002")

        # 1. JPEG
        res_jpg = client.post(
            "/api/v1/documents/upload",
            files={"file": ("caste_cert.jpg", io.BytesIO(VALID_JPEG_BYTES), "image/jpeg")},
            data={"document_type": "caste_certificate"},
            headers=headers,
        )
        assert res_jpg.status_code == 201
        assert res_jpg.json()["document"]["mime_type"] == "image/jpeg"
        assert res_jpg.json()["document"]["ocr_status"] == DocumentProcessingStatus.OCR_COMPLETED

        # 2. PNG
        res_png = client.post(
            "/api/v1/documents/upload",
            files={"file": ("ration_card.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            data={"document_type": "ration_card"},
            headers=headers,
        )
        assert res_png.status_code == 201
        assert res_png.json()["document"]["mime_type"] == "image/png"
        assert res_png.json()["document"]["ocr_status"] == DocumentProcessingStatus.OCR_COMPLETED

    def test_upload_invalid_magic_bytes_rejected(self, client):
        """Uploading a spoofed file with wrong magic bytes returns 400 Bad Request."""
        headers = get_auth_headers(client, "+919900000003")
        fake_pdf = b"This is plain text pretending to be a PDF file."

        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("spoofed.pdf", io.BytesIO(fake_pdf), "application/pdf")},
            data={"document_type": "income_certificate"},
            headers=headers,
        )
        assert response.status_code == 400
        assert "content signature validation failed" in response.json()["detail"].lower()

    def test_upload_disallowed_extension_rejected(self, client):
        """Uploading unsupported extensions (e.g. .exe, .sh, .txt) returns 400 Bad Request."""
        headers = get_auth_headers(client, "+919900000004")
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("script.exe", io.BytesIO(b"MZtest"), "application/octet-stream")},
            data={"document_type": "income_certificate"},
            headers=headers,
        )
        assert response.status_code == 400
        assert "unsupported file extension" in response.json()["detail"].lower()

    def test_upload_oversized_file_rejected(self, client, monkeypatch):
        """Uploading files exceeding max size limit returns 400 Bad Request."""
        headers = get_auth_headers(client, "+919900000005")
        # Temporarily set max limit to 50 bytes for fast testing
        monkeypatch.setattr("app.services.storage_service.settings.MAX_DOCUMENT_FILE_SIZE_BYTES", 50)

        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("large.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")},
            data={"document_type": "income_certificate"},
            headers=headers,
        )
        assert response.status_code == 400
        assert "exceeds the maximum allowed limit" in response.json()["detail"].lower()


    def test_list_and_filter_documents(self, client):
        """Citizens can list vault documents and filter by document_type or ocr_status."""
        headers = get_auth_headers(client, "+919900000006")

        # Upload 2 documents
        client.post(
            "/api/v1/documents/upload",
            files={"file": ("income.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")},
            data={"document_type": "income_certificate"},
            headers=headers,
        )
        client.post(
            "/api/v1/documents/upload",
            files={"file": ("domicile.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")},
            data={"document_type": "domicile_certificate"},
            headers=headers,
        )

        # List all
        res_all = client.get("/api/v1/documents", headers=headers)
        assert res_all.status_code == 200
        data_all = res_all.json()
        assert data_all["total"] >= 2

        # Filter by type
        res_income = client.get("/api/v1/documents?document_type=income_certificate", headers=headers)
        assert res_income.status_code == 200
        assert all(d["document_type"] == "income_certificate" for d in res_income.json()["documents"])

        # Filter by status
        res_status = client.get("/api/v1/documents?ocr_status=OCR_COMPLETED", headers=headers)
        assert res_status.status_code == 200
        assert all(d["ocr_status"] == "OCR_COMPLETED" for d in res_status.json()["documents"])

    def test_get_document_details(self, client):
        """Citizens can fetch full details and extracted text of an uploaded document."""
        headers = get_auth_headers(client, "+919900000007")
        res_up = client.post(
            "/api/v1/documents/upload",
            files={"file": ("aadhaar.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            data={"document_type": "aadhaar_card"},
            headers=headers,
        )
        doc_id = res_up.json()["document"]["id"]

        response = client.get(f"/api/v1/documents/{doc_id}", headers=headers)
        assert response.status_code == 200
        doc = response.json()
        assert doc["id"] == doc_id
        assert "UIDAI" in doc["ocr_extracted_text"]
        assert doc["ocr_metadata"]["provider"] == "mock_ocr"

    def test_download_document_file(self, client):
        """Citizens can stream and view the binary document file with correct MIME type headers."""
        headers = get_auth_headers(client, "+919900000008")
        res_up = client.post(
            "/api/v1/documents/upload",
            files={"file": ("my_income.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")},
            data={"document_type": "income_certificate"},
            headers=headers,
        )
        doc_id = res_up.json()["document"]["id"]

        response = client.get(f"/api/v1/documents/{doc_id}/download", headers=headers)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "my_income.pdf" in response.headers["content-disposition"]
        assert response.content == VALID_PDF_BYTES

    def test_idor_prevention_cross_user_access_blocked(self, client):
        """Prevent Insecure Direct Object References: Citizen B cannot view or delete Citizen A's documents."""
        headers_a = get_auth_headers(client, "+919900000010")
        headers_b = get_auth_headers(client, "+919900000011")

        # Citizen A uploads
        res_up = client.post(
            "/api/v1/documents/upload",
            files={"file": ("confidential.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")},
            data={"document_type": "income_certificate"},
            headers=headers_a,
        )
        doc_id = res_up.json()["document"]["id"]

        # Citizen B attempts GET details
        res_get = client.get(f"/api/v1/documents/{doc_id}", headers=headers_b)
        assert res_get.status_code in (403, 404)

        # Citizen B attempts download
        res_dl = client.get(f"/api/v1/documents/{doc_id}/download", headers=headers_b)
        assert res_dl.status_code in (403, 404)

        # Citizen B attempts delete
        res_del = client.delete(f"/api/v1/documents/{doc_id}", headers=headers_b)
        assert res_del.status_code in (403, 404)

    def test_delete_document_removes_from_disk_and_db(self, client):
        """Deleting a document purges the DB record and unlinks the file on disk."""
        headers = get_auth_headers(client, "+919900000012")
        res_up = client.post(
            "/api/v1/documents/upload",
            files={"file": ("delete_me.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")},
            data={"document_type": "ration_card"},
            headers=headers,
        )
        doc = res_up.json()["document"]
        doc_id = doc["id"]
        storage_ref = doc["storage_reference"]

        # Verify exists on disk
        file_path = storage_service.resolve_path(storage_ref)
        assert file_path.exists()

        # Delete
        res_del = client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
        assert res_del.status_code == 200

        # Verify removed from disk
        assert not file_path.exists()

        # Verify not found in DB
        res_get = client.get(f"/api/v1/documents/{doc_id}", headers=headers)
        assert res_get.status_code == 404

    def test_low_confidence_triggers_manual_review(self, client):
        """Low confidence OCR extraction triggers MANUAL_REVIEW_REQUIRED status."""
        headers = get_auth_headers(client, "+919900000013")
        res_up = client.post(
            "/api/v1/documents/upload",
            files={"file": ("blurry_scan.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")},
            data={"document_type": "income_certificate"},
            headers=headers,
        )
        doc = res_up.json()["document"]
        assert doc["ocr_status"] == DocumentProcessingStatus.MANUAL_REVIEW_REQUIRED
        assert doc["manual_review_required"] is True
        assert doc["ocr_confidence"] < 0.70
        assert "manual citizen verification required" in doc["ocr_error_message"].lower()

    def test_retry_ocr(self, client):
        """Citizen can re-trigger OCR processing on an existing document."""
        headers = get_auth_headers(client, "+919900000014")
        res_up = client.post(
            "/api/v1/documents/upload",
            files={"file": ("income_test.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")},
            data={"document_type": "income_certificate"},
            headers=headers,
        )
        doc_id = res_up.json()["document"]["id"]

        res_retry = client.post(f"/api/v1/documents/{doc_id}/retry-ocr", headers=headers)
        assert res_retry.status_code == 200
        doc = res_retry.json()
        assert doc["id"] == doc_id
        assert doc["ocr_status"] == DocumentProcessingStatus.OCR_COMPLETED

    def test_scheme_document_checklist(self, client, db_session):
        """Check scheme requirements against citizen's uploaded documents."""
        headers = get_auth_headers(client, "+919900000015")

        # Create scheme requiring Aadhaar and Income Certificate
        scheme = Scheme(
            scheme_name="Kisan Krishi Sahayata",
            description="Agricultural welfare subsidy for small farmers.",
            department="Department of Agriculture",
            state_applicability="All India",
            eligibility_summary="Farmer landholder with income under 2 Lakhs",
            official_source_url="https://agricoop.gov.in",
            official_application_url="https://agricoop.gov.in/apply",
            required_documents=[
                {"name": "Aadhaar Card", "description": "Proof of identity", "is_mandatory": True},
                {"name": "Income Certificate", "description": "Proof of annual income", "is_mandatory": True},
            ],
        )
        db_session.add(scheme)
        db_session.commit()
        db_session.refresh(scheme)

        # Initially citizen has uploaded nothing
        res_chk1 = client.get(f"/api/v1/documents/scheme/{scheme.id}/checklist", headers=headers)
        assert res_chk1.status_code == 200
        chk1 = res_chk1.json()
        assert chk1["total_required"] == 2
        assert chk1["total_uploaded"] == 0
        assert chk1["is_fully_prepared"] is False
        assert "does not replace government verification" in chk1["disclaimer"]

        # Citizen uploads Income Certificate
        client.post(
            "/api/v1/documents/upload",
            files={"file": ("income.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")},
            data={"document_type": "income_certificate"},
            headers=headers,
        )

        res_chk2 = client.get(f"/api/v1/documents/scheme/{scheme.id}/checklist", headers=headers)
        chk2 = res_chk2.json()
        assert chk2["total_uploaded"] == 1
        assert chk2["is_fully_prepared"] is False

        # Citizen uploads Aadhaar Card
        client.post(
            "/api/v1/documents/upload",
            files={"file": ("aadhaar.png", io.BytesIO(VALID_PNG_BYTES), "image/png")},
            data={"document_type": "aadhaar_card"},
            headers=headers,
        )

        res_chk3 = client.get(f"/api/v1/documents/scheme/{scheme.id}/checklist", headers=headers)
        chk3 = res_chk3.json()
        assert chk3["total_uploaded"] == 2
        assert chk3["is_fully_prepared"] is True
