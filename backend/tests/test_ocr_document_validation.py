import io
from PIL import Image, ImageDraw
import numpy as np
import pytest

from app.models.document import DocumentProcessingStatus
from app.services.ocr_service import validate_document_content, ocr_service
from tests.test_documents import get_auth_headers


def create_test_image_bytes(text: str) -> bytes:
    """Generate image bytes with rendered text for testing RapidOCR & validation pipeline."""
    img = Image.new("RGB", (900, 350), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((30, 40), text, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def create_random_image_bytes() -> bytes:
    """Generate random non-text photo bytes (like a photo of nature or a room)."""
    # Create gradient / random noise image with 0 text
    img = Image.new("RGB", (600, 600), color=(140, 180, 220))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


class TestOCRDocumentValidation:
    """Validate that only genuine matching documents are accepted and random/mismatched photos are rejected."""

    def test_random_photo_rejected(self, client):
        """Random photo without certificate text is rejected with OCR_FAILED and zero synthetic citizen details."""
        headers = get_auth_headers(client, "+919911223344")
        random_bytes = create_random_image_bytes()

        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("IMG_20260219_random.jpg", io.BytesIO(random_bytes), "image/jpeg")},
            data={"document_type": "income_certificate"},
            headers=headers,
        )

        assert response.status_code == 201
        doc = response.json()["document"]
        assert doc["ocr_status"] == DocumentProcessingStatus.OCR_FAILED
        assert doc["manual_review_required"] is True
        # CRITICAL: Extracted text must NOT contain fake template income details
        assert "INC/2026/894120" not in (doc["ocr_extracted_text"] or "")
        assert "1,20,000" not in (doc["ocr_extracted_text"] or "")
        assert "Income Certificate" in doc["ocr_error_message"]

    def test_mismatched_document_type_rejected(self, client):
        """Uploading a Ration Card when Income Certificate was selected is rejected with a clear mismatch error."""
        headers = get_auth_headers(client, "+919911223355")
        ration_card_text = (
            "DEPARTMENT OF FOOD AND CIVIL SUPPLIES\n"
            "NATIONAL FOOD SECURITY ACT (NFSA) RATION CARD\n"
            "Card Category: Priority Household (BPL / PHH)\n"
            "Fair Price Shop No: FPS-102"
        )
        ration_img_bytes = create_test_image_bytes(ration_card_text)

        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("camera_doc_scan.jpg", io.BytesIO(ration_img_bytes), "image/jpeg")},
            data={"document_type": "income_certificate"},
            headers=headers,
        )

        assert response.status_code == 201
        doc = response.json()["document"]
        assert doc["ocr_status"] == DocumentProcessingStatus.OCR_FAILED
        assert "Ration Card" in doc["ocr_error_message"]

    def test_genuine_income_certificate_accepted(self, client):
        """Genuine income certificate is accepted with OCR_COMPLETED and real extracted text."""
        headers = get_auth_headers(client, "+919911223366")
        income_text = (
            "GOVERNMENT OF MAHARASHTRA\n"
            "OFFICE OF THE TAHSILDAR / REVENUE DEPARTMENT\n"
            "INCOME CERTIFICATE\n"
            "Annual Family Income: INR 85,000"
        )
        income_img_bytes = create_test_image_bytes(income_text)

        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("camera_income_cert.jpg", io.BytesIO(income_img_bytes), "image/jpeg")},
            data={"document_type": "income_certificate"},
            headers=headers,
        )

        assert response.status_code == 201
        doc = response.json()["document"]
        assert doc["ocr_status"] == DocumentProcessingStatus.OCR_COMPLETED
        assert doc["manual_review_required"] is False
        assert "INCOME" in doc["ocr_extracted_text"].upper()
