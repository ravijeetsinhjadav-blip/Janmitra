import os
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.models.document import DocumentProcessingStatus

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """Standardized OCR processing output."""
    extracted_text: str
    confidence: float
    metadata: Dict[str, Any]
    status: str
    manual_review_required: bool
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None


class BaseOCRAdapter:
    """Interface for OCR adapters."""
    def extract_text(
        self,
        file_bytes: bytes,
        mime_type: str,
        document_type: str,
        filename: str,
    ) -> OCRResult:
        raise NotImplementedError


class GoogleCloudVisionAdapter(BaseOCRAdapter):
    """Production adapter using Google Cloud Vision API."""

    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = credentials_path or settings.GOOGLE_APPLICATION_CREDENTIALS
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google.cloud import vision
            if self.credentials_path and os.path.exists(self.credentials_path):
                self._client = vision.ImageAnnotatorClient.from_service_account_json(self.credentials_path)
            else:
                # Default application credentials from environment
                self._client = vision.ImageAnnotatorClient()
        return self._client

    def extract_text(
        self,
        file_bytes: bytes,
        mime_type: str,
        document_type: str,
        filename: str,
    ) -> OCRResult:
        now = datetime.now(timezone.utc)
        try:
            from google.cloud import vision
            client = self._get_client()

            image = vision.Image(content=file_bytes)
            # Use document_text_detection for high accuracy on structured government certificates
            response = client.document_text_detection(image=image)

            if response.error.message:
                return OCRResult(
                    extracted_text="",
                    confidence=0.0,
                    metadata={"provider": "google_cloud_vision", "error": response.error.message},
                    status=DocumentProcessingStatus.OCR_FAILED,
                    manual_review_required=True,
                    error_message=f"Google Cloud Vision API error: {response.error.message}",
                    completed_at=now,
                )

            full_text = response.full_text_annotation.text if response.full_text_annotation else ""

            # Calculate average confidence across detected symbols/blocks
            confidences: List[float] = []
            detected_languages: List[str] = []
            block_count = 0
            word_count = 0

            if response.full_text_annotation and response.full_text_annotation.pages:
                for page in response.full_text_annotation.pages:
                    for lang in page.property.detected_languages:
                        if lang.language_code not in detected_languages:
                            detected_languages.append(lang.language_code)
                    for block in page.blocks:
                        block_count += 1
                        if block.confidence > 0:
                            confidences.append(block.confidence)
                        for para in block.paragraphs:
                            for word in para.words:
                                word_count += 1
                                if word.confidence > 0:
                                    confidences.append(word.confidence)

            avg_confidence = (sum(confidences) / len(confidences)) if confidences else (0.90 if full_text.strip() else 0.0)
            avg_confidence = round(float(avg_confidence), 4)

            # Manual review check: low confidence or empty text
            is_low_confidence = avg_confidence < settings.OCR_CONFIDENCE_THRESHOLD
            is_empty = len(full_text.strip()) < 10
            manual_review = is_low_confidence or is_empty

            status = (
                DocumentProcessingStatus.MANUAL_REVIEW_REQUIRED
                if manual_review
                else DocumentProcessingStatus.OCR_COMPLETED
            )

            metadata = {
                "provider": "google_cloud_vision",
                "detected_languages": detected_languages or ["en"],
                "block_count": block_count,
                "word_count": word_count,
                "confidence_threshold": settings.OCR_CONFIDENCE_THRESHOLD,
                "pages": len(response.full_text_annotation.pages) if response.full_text_annotation else 1,
            }

            return OCRResult(
                extracted_text=full_text,
                confidence=avg_confidence,
                metadata=metadata,
                status=status,
                manual_review_required=manual_review,
                error_message="Low OCR extraction confidence or unreadable text." if manual_review else None,
                completed_at=now,
            )

        except Exception as exc:
            logger.error("Google Cloud Vision OCR extraction failed: %s", exc)
            return OCRResult(
                extracted_text="",
                confidence=0.0,
                metadata={"provider": "google_cloud_vision", "exception": str(exc)},
                status=DocumentProcessingStatus.OCR_FAILED,
                manual_review_required=True,
                error_message=f"OCR processing failed: {str(exc)}",
                completed_at=now,
            )


class MockOCRAdapter(BaseOCRAdapter):
    """High-fidelity mock OCR adapter for local development, CI testing, and offline MCA project demonstration.
    
    Generates realistic extracted text for standard Indian government certificates and supports
    deterministic testing of edge cases (low confidence, blurred images, corrupt files).
    """

    TEMPLATES = {
        "income_certificate": (
            "GOVERNMENT OF MAHARASHTRA / UTTAR PRADESH\n"
            "OFFICE OF THE TAHSILDAR / REVENUE DEPARTMENT\n"
            "INCOME CERTIFICATE\n\n"
            "Certificate No: INC/2026/894120\n"
            "Date of Issue: 12/01/2026\n\n"
            "This is to certify that upon due enquiry, the annual family income of\n"
            "Shri/Smt/Kumari citizen applicant from all verified sources is found to be\n"
            "INR 1,20,000 (Rupees One Lakh Twenty Thousand Only).\n\n"
            "This certificate is valid for official welfare scheme eligibility assessment.\n"
            "Digitally Signed by Competent Authority / Tahsildar."
        ),
        "caste_certificate": (
            "GOVERNMENT OF INDIA / STATE GOVERNMENT\n"
            "CASTE / COMMUNITY CERTIFICATE\n\n"
            "Certificate No: CST/2025/44129\n"
            "Date of Issue: 18/06/2025\n\n"
            "This is to certify that the applicant belongs to Other Backward Classes (OBC) / SC / ST\n"
            "under the Constitution (Scheduled Castes / Scheduled Tribes) Order.\n"
            "Sub-caste: Recognized under State / Central List.\n"
            "Issuing Officer: Sub-Divisional Magistrate (SDM)."
        ),
        "domicile_certificate": (
            "STATE REVENUE & DISTRICT MAGISTRATE DEPARTMENT\n"
            "DOMICILE / PERMANENT RESIDENT CERTIFICATE\n\n"
            "Certificate No: DOM/2026/71004\n"
            "Date: 05/02/2026\n\n"
            "Certified that the applicant is a bonafide permanent resident of State / District,\n"
            "having resided continuously for a period exceeding 15 years.\n"
            "Verified by Revenue Inspector."
        ),
        "ration_card": (
            "FOOD, CIVIL SUPPLIES & CONSUMER AFFAIRS DEPARTMENT\n"
            "NATIONAL FOOD SECURITY ACT (NFSA) RATION CARD\n\n"
            "Ration Card No: RC-9921-8841-0021\n"
            "Card Category: Priority Household (BPL / PHH)\n"
            "Fair Price Shop No: FPS-402\n"
            "Family Head: Registered Citizen\n"
            "Number of Entitled Beneficiaries: 4."
        ),
        "aadhaar_card": (
            "UNIQUE IDENTIFICATION AUTHORITY OF INDIA (UIDAI)\n"
            "GOVERNMENT OF INDIA\n\n"
            "Name: Citizen User\n"
            "DOB: 15/08/1990\n"
            "Gender: Male / Female\n"
            "Aadhaar Number: XXXX XXXX 4192 (Virtual ID: 9182 4410 2931 0019)\n"
            "Address: Verified Resident Address, India."
        ),
        "land_record": (
            "DEPARTMENT OF REVENUE & LAND RECORDS\n"
            "RECORD OF RIGHTS (7/12 EXTRACT / KHATAUNI / JAMABANDI)\n\n"
            "Survey / Khasra No: 142/2A\n"
            "Total Land Area: 1.45 Hectares\n"
            "Land Classification: Irrigated Agricultural Land (Jirayat)\n"
            "Owner / Khatedar: Citizen Family\n"
            "Remarks: Cultivable land under agricultural operation."
        ),
    }

    def extract_text(
        self,
        file_bytes: bytes,
        mime_type: str,
        document_type: str,
        filename: str,
    ) -> OCRResult:
        now = datetime.now(timezone.utc)
        name_lower = filename.lower()

        # Edge case 1: Corrupted or failed extraction
        if "corrupt" in name_lower or "fail" in name_lower:
            return OCRResult(
                extracted_text="",
                confidence=0.0,
                metadata={"provider": "mock_ocr", "test_case": "forced_failure"},
                status=DocumentProcessingStatus.OCR_FAILED,
                manual_review_required=True,
                error_message="Document scan unreadable or image stream corrupted.",
                completed_at=now,
            )

        # Edge case 2: Low quality / blurry document requiring manual review
        if "blurry" in name_lower or "low_quality" in name_lower or "poor" in name_lower:
            partial_text = "GOVERNMENT OF INDIA ... [Unreadable / Blurred Text] ... Income: ????"
            return OCRResult(
                extracted_text=partial_text,
                confidence=0.52,
                metadata={
                    "provider": "mock_ocr",
                    "test_case": "low_confidence",
                    "word_count": 8,
                    "confidence_threshold": settings.OCR_CONFIDENCE_THRESHOLD,
                },
                status=DocumentProcessingStatus.MANUAL_REVIEW_REQUIRED,
                manual_review_required=True,
                error_message="Low OCR confidence (0.52 < threshold 0.70). Manual citizen verification required.",
                completed_at=now,
            )

        # Edge case 3: Blank / empty document
        if "blank" in name_lower or "empty" in name_lower:
            return OCRResult(
                extracted_text="",
                confidence=0.10,
                metadata={"provider": "mock_ocr", "test_case": "blank_document"},
                status=DocumentProcessingStatus.MANUAL_REVIEW_REQUIRED,
                manual_review_required=True,
                error_message="Document appears blank or contains insufficient text.",
                completed_at=now,
            )

        # Standard successful extraction
        text = self.TEMPLATES.get(
            document_type.lower(),
            (
                f"OFFICIAL DOCUMENT - {document_type.upper().replace('_', ' ')}\n"
                f"Original Filename: {filename}\n"
                f"File MIME Type: {mime_type}\n"
                "Certified and verified document for government service application."
            ),
        )

        confidence = 0.94
        metadata = {
            "provider": "mock_ocr",
            "detected_languages": ["en", "hi"],
            "block_count": 5,
            "word_count": len(text.split()),
            "confidence_threshold": settings.OCR_CONFIDENCE_THRESHOLD,
        }

        return OCRResult(
            extracted_text=text,
            confidence=confidence,
            metadata=metadata,
            status=DocumentProcessingStatus.OCR_COMPLETED,
            manual_review_required=False,
            error_message=None,
            completed_at=now,
        )


class OCRService:
    """Orchestrator for document text recognition.
    
    Determines whether to use Google Cloud Vision API or the Mock adapter based on
    system configuration and credential availability.
    """

    def __init__(self):
        self._gcv_adapter = GoogleCloudVisionAdapter()
        self._mock_adapter = MockOCRAdapter()

    def _should_use_gcv(self) -> bool:
        if settings.OCR_PROVIDER != "google_cloud_vision":
            return False
        # Check if Google application credentials are provided and exist
        creds_file = settings.GOOGLE_APPLICATION_CREDENTIALS
        if creds_file and os.path.exists(creds_file):
            return True
        if os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and os.path.exists(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")):
            return True
        return False

    def process_document(
        self,
        file_bytes: bytes,
        mime_type: str,
        document_type: str,
        filename: str,
    ) -> OCRResult:
        """Process document through the selected OCR pipeline."""
        if self._should_use_gcv():
            logger.info("Processing document '%s' via Google Cloud Vision API", filename)
            result = self._gcv_adapter.extract_text(
                file_bytes=file_bytes,
                mime_type=mime_type,
                document_type=document_type,
                filename=filename,
            )
            # If GCV encountered an unhandled infrastructure/auth error, fallback safely if in development
            if result.status == DocumentProcessingStatus.OCR_FAILED and settings.DEBUG:
                logger.warning("GCV failed in development; falling back to mock adapter.")
                return self._mock_adapter.extract_text(
                    file_bytes=file_bytes,
                    mime_type=mime_type,
                    document_type=document_type,
                    filename=filename,
                )
            return result
        else:
            logger.info("Processing document '%s' via Mock OCR Adapter (Google Cloud credentials not set).", filename)
            return self._mock_adapter.extract_text(
                file_bytes=file_bytes,
                mime_type=mime_type,
                document_type=document_type,
                filename=filename,
            )


ocr_service = OCRService()
