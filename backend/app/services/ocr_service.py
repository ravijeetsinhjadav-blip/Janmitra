import os
import re
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from app.models.document import DocumentProcessingStatus

logger = logging.getLogger(__name__)


def sanitize_ocr_error_message(msg: str) -> str:
    """Strip internal server filesystem paths, hostnames, and credentials from error messages."""
    if not msg:
        return "OCR extraction encountered an error."
    # Strip Windows drive and folder paths (e.g., C:\Users\... or D:\Janmitra\...)
    clean = re.sub(r'[A-Za-z]:\\[\w\\\.\-]+', '[LOCAL_PATH]', msg)
    # Strip Unix paths (/home/..., /var/..., etc.)
    clean = re.sub(r'/(?:[\w\.\-]+/)+[\w\.\-]+', '[LOCAL_PATH]', clean)
    # Strip GCP project IDs or email addresses if present
    clean = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[REDACTED_IDENTITY]', clean)
    return clean.strip()


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
    """Production adapter using Google Cloud Vision API.
    
    Supports:
    1. Images (JPEG, PNG): Synchronous `document_text_detection`.
    2. PDFs: Synchronous `batch_annotate_files` (up to 5 pages, no GCS required).
    """

    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = credentials_path or settings.GOOGLE_APPLICATION_CREDENTIALS
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google.cloud import vision
            from google.auth.exceptions import DefaultCredentialsError, GoogleAuthError

            # Always refresh credentials_path from settings if not explicitly passed
            creds = self.credentials_path or getattr(settings, "GOOGLE_APPLICATION_CREDENTIALS", None)
            if creds:
                if not os.path.exists(creds):
                    raise FileNotFoundError(
                        f"Google Cloud Vision credentials file not found at: {creds}"
                    )
                try:
                    self._client = vision.ImageAnnotatorClient.from_service_account_json(creds)
                except Exception as json_err:
                    raise RuntimeError(
                        f"Invalid Google Cloud Vision service account JSON credentials: {json_err}"
                    ) from json_err
            else:
                try:
                    self._client = vision.ImageAnnotatorClient()
                except (DefaultCredentialsError, GoogleAuthError, Exception) as auth_err:
                    raise RuntimeError(
                        "Google Cloud Vision credentials not configured: no valid service account file "
                        "or Application Default Credentials found. Set GOOGLE_APPLICATION_CREDENTIALS."
                    ) from auth_err
        return self._client

    def _extract_from_image(self, client, file_bytes: bytes, now: datetime) -> OCRResult:
        from google.cloud import vision
        image = vision.Image(content=file_bytes)
        response = client.document_text_detection(image=image)

        if response.error.message:
            clean_err = sanitize_ocr_error_message(response.error.message)
            return OCRResult(
                extracted_text="",
                confidence=0.0,
                metadata={"provider": "google_cloud_vision", "is_mock": False, "error": clean_err},
                status=DocumentProcessingStatus.OCR_FAILED,
                manual_review_required=True,
                error_message=f"Google Cloud Vision API error: {clean_err}",
                completed_at=now,
            )

        full_text = response.full_text_annotation.text if response.full_text_annotation else ""
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
            "is_mock": False,
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

    def _extract_from_pdf(self, client, file_bytes: bytes, now: datetime) -> OCRResult:
        from google.cloud import vision
        # Synchronous batch file annotation for PDF files (up to 5 pages, in-memory)
        input_config = vision.InputConfig(
            content=file_bytes,
            mime_type="application/pdf",
        )
        feature = vision.Feature(type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)
        # By leaving `pages` unspecified, the Vision API automatically annotates
        # up to the first 5 pages of the document without failing on shorter PDFs.
        request = vision.AnnotateFileRequest(
            input_config=input_config,
            features=[feature],
        )

        response = client.batch_annotate_files(requests=[request])
        if not response.responses:
            return OCRResult(
                extracted_text="",
                confidence=0.0,
                metadata={"provider": "google_cloud_vision", "is_mock": False, "error": "Empty response from Vision API"},
                status=DocumentProcessingStatus.OCR_FAILED,
                manual_review_required=True,
                error_message="Vision API returned empty response for PDF file.",
                completed_at=now,
            )

        file_response = response.responses[0]
        if file_response.error.message:
            clean_err = sanitize_ocr_error_message(file_response.error.message)
            return OCRResult(
                extracted_text="",
                confidence=0.0,
                metadata={"provider": "google_cloud_vision", "is_mock": False, "error": clean_err},
                status=DocumentProcessingStatus.OCR_FAILED,
                manual_review_required=True,
                error_message=f"Google Cloud Vision PDF error: {clean_err}",
                completed_at=now,
            )

        extracted_pages_text: List[str] = []
        confidences: List[float] = []
        detected_languages: List[str] = []
        total_blocks = 0
        total_words = 0

        for page_resp in file_response.responses:
            if page_resp.error.message:
                continue
            if page_resp.full_text_annotation:
                extracted_pages_text.append(page_resp.full_text_annotation.text)
                for page in page_resp.full_text_annotation.pages:
                    for lang in page.property.detected_languages:
                        if lang.language_code not in detected_languages:
                            detected_languages.append(lang.language_code)
                    for block in page.blocks:
                        total_blocks += 1
                        if block.confidence > 0:
                            confidences.append(block.confidence)
                        for para in block.paragraphs:
                            for word in para.words:
                                total_words += 1
                                if word.confidence > 0:
                                    confidences.append(word.confidence)

        full_text = "\n\n--- Page Break ---\n\n".join(extracted_pages_text).strip()
        avg_confidence = (sum(confidences) / len(confidences)) if confidences else (0.90 if full_text else 0.0)
        avg_confidence = round(float(avg_confidence), 4)

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
            "is_mock": False,
            "detected_languages": detected_languages or ["en"],
            "block_count": total_blocks,
            "word_count": total_words,
            "confidence_threshold": settings.OCR_CONFIDENCE_THRESHOLD,
            "pages": len(file_response.responses),
            "note": "Processed via synchronous batch_annotate_files (first 5 pages). Multi-page PDFs exceeding 5 pages require GCS bucket async pipeline.",
        }

        return OCRResult(
            extracted_text=full_text,
            confidence=avg_confidence,
            metadata=metadata,
            status=status,
            manual_review_required=manual_review,
            error_message="Low OCR extraction confidence or unreadable PDF text." if manual_review else None,
            completed_at=now,
        )

    def extract_text(
        self,
        file_bytes: bytes,
        mime_type: str,
        document_type: str,
        filename: str,
    ) -> OCRResult:
        now = datetime.now(timezone.utc)

        # 1. Input format & size validations
        if not file_bytes or len(file_bytes) == 0:
            return OCRResult(
                extracted_text="",
                confidence=0.0,
                metadata={"provider": "google_cloud_vision", "is_mock": False, "error": "empty_file"},
                status=DocumentProcessingStatus.OCR_FAILED,
                manual_review_required=True,
                error_message="Uploaded document is empty (0 bytes).",
                completed_at=now,
            )

        if len(file_bytes) > settings.MAX_DOCUMENT_FILE_SIZE_BYTES:
            return OCRResult(
                extracted_text="",
                confidence=0.0,
                metadata={"provider": "google_cloud_vision", "is_mock": False, "error": "file_too_large"},
                status=DocumentProcessingStatus.OCR_FAILED,
                manual_review_required=True,
                error_message=f"Document exceeds maximum permitted file size of {settings.MAX_DOCUMENT_FILE_SIZE_BYTES} bytes.",
                completed_at=now,
            )

        norm_mime = (mime_type or "").lower().strip()
        if norm_mime not in ["application/pdf", "image/jpeg", "image/jpg", "image/png"]:
            return OCRResult(
                extracted_text="",
                confidence=0.0,
                metadata={"provider": "google_cloud_vision", "is_mock": False, "error": "unsupported_format"},
                status=DocumentProcessingStatus.OCR_FAILED,
                manual_review_required=True,
                error_message=f"Unsupported document format '{mime_type}'. Supported formats: PDF, JPEG, PNG.",
                completed_at=now,
            )

        try:
            client = self._get_client()
            if norm_mime == "application/pdf":
                return self._extract_from_pdf(client, file_bytes, now)
            else:
                return self._extract_from_image(client, file_bytes, now)
        except Exception as exc:
            clean_err = sanitize_ocr_error_message(str(exc))
            logger.error("Google Cloud Vision OCR extraction failed: %s", clean_err)
            return OCRResult(
                extracted_text="",
                confidence=0.0,
                metadata={"provider": "google_cloud_vision", "is_mock": False, "exception": clean_err},
                status=DocumentProcessingStatus.OCR_FAILED,
                manual_review_required=True,
                error_message=f"OCR processing failed: {clean_err}",
                completed_at=now,
            )


class MockOCRAdapter(BaseOCRAdapter):
    """High-fidelity mock OCR adapter strictly restricted to development/test environments.
    
    Generates realistic simulated text for standard Indian government certificates and supports
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
                metadata={"provider": "mock_ocr", "is_mock": True, "test_case": "forced_failure"},
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
                    "is_mock": True,
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
                metadata={"provider": "mock_ocr", "is_mock": True, "test_case": "blank_document"},
                status=DocumentProcessingStatus.MANUAL_REVIEW_REQUIRED,
                manual_review_required=True,
                error_message="Document appears blank or contains insufficient text.",
                completed_at=now,
            )

        # Standard successful simulated extraction
        text = self.TEMPLATES.get(
            document_type.lower(),
            (
                f"OFFICIAL DOCUMENT - {document_type.upper().replace('_', ' ')}\n"
                f"Original Filename: {filename}\n"
                f"File MIME Type: {mime_type}\n"
                "Certified document for government service application."
            ),
        )

        confidence = 0.94
        metadata = {
            "provider": "mock_ocr",
            "is_mock": True,
            "detected_languages": ["en", "hi"],
            "block_count": 5,
            "word_count": len(text.split()),
            "confidence_threshold": settings.OCR_CONFIDENCE_THRESHOLD,
            "notice": "Simulated mock extraction for local development and MCA demonstration.",
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
    
    Security & Production Safety Architecture:
    - In production (ENVIRONMENT == 'production' or DEBUG is False), MockOCRAdapter is
      STRICTLY FORBIDDEN. It will NEVER execute or fall back silently.
    - If Google Cloud Vision credentials are missing in production, an explicit failure
      status (OCR_FAILED) is returned.
    """

    def __init__(self):
        self._gcv_adapter = GoogleCloudVisionAdapter()
        self._mock_adapter = MockOCRAdapter()

    @staticmethod
    def is_production() -> bool:
        """Check whether the application is running under production constraints."""
        env = getattr(settings, "ENVIRONMENT", "").lower()
        debug = getattr(settings, "DEBUG", False)
        return env == "production" or not debug

    def _should_use_gcv(self) -> bool:
        """Determine whether Google Cloud Vision should be used based on available credentials."""
        creds_file = getattr(settings, "GOOGLE_APPLICATION_CREDENTIALS", None)
        if creds_file and os.path.exists(creds_file):
            return True
        env_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if env_creds and os.path.exists(env_creds):
            return True
        return False

    def process_document(
        self,
        file_bytes: bytes,
        mime_type: str,
        document_type: str,
        filename: str,
    ) -> OCRResult:
        """Process document through the configured OCR pipeline.

        Enforces strict provider routing:
        - When in production:
            Only Google Cloud Vision is permitted.
            If credentials are not configured (not self._should_use_gcv()), immediately return OCR_FAILED
            with an explicit message: 'OCR processing service unavailable in production: Cloud Vision credentials not configured.'
            Otherwise invoke the Google Cloud Vision adapter.
        - When in development/test:
            If OCR_PROVIDER == 'google_cloud_vision': invoke Google Cloud Vision adapter directly (no fallback).
            If OCR_PROVIDER == 'mock': invoke MockOCRAdapter.
            Any other value: return OCR_FAILED with unsupported provider error.
        """
        now = datetime.now(timezone.utc)
        provider = (getattr(settings, "OCR_PROVIDER", "mock") or "mock").lower()

        # 1. Production Mode Constraints
        if self.is_production():
            if not self._should_use_gcv():
                logger.error("Production OCR error: Cloud Vision credentials not configured.")
                return OCRResult(
                    extracted_text="",
                    confidence=0.0,
                    metadata={"provider": "google_cloud_vision", "is_mock": False, "error": "credentials_not_configured"},
                    status=DocumentProcessingStatus.OCR_FAILED,
                    manual_review_required=True,
                    error_message="OCR processing service unavailable in production: Cloud Vision credentials not configured.",
                    completed_at=now,
                )

            logger.info("Processing document '%s' via Google Cloud Vision API in production", filename)
            return self._gcv_adapter.extract_text(
                file_bytes=file_bytes,
                mime_type=mime_type,
                document_type=document_type,
                filename=filename,
            )

        # 2. Development / Test Mode Routing
        if provider == "google_cloud_vision":
            logger.info("Processing document '%s' via Google Cloud Vision API (development mode)", filename)
            # Direct invocation without silent mock fallback
            return self._gcv_adapter.extract_text(
                file_bytes=file_bytes,
                mime_type=mime_type,
                document_type=document_type,
                filename=filename,
            )
        elif provider == "mock":
            logger.info("Processing document '%s' via Mock OCR Adapter (development mode).", filename)
            return self._mock_adapter.extract_text(
                file_bytes=file_bytes,
                mime_type=mime_type,
                document_type=document_type,
                filename=filename,
            )
        else:
            logger.error("Unknown OCR provider configured: %s", provider)
            return OCRResult(
                extracted_text="",
                confidence=0.0,
                metadata={"provider": provider, "is_mock": False, "error": "unknown_provider"},
                status=DocumentProcessingStatus.OCR_FAILED,
                manual_review_required=True,
                error_message=f"Unknown OCR provider configured: '{provider}'. Supported: 'google_cloud_vision', 'mock'.",
                completed_at=now,
            )


ocr_service = OCRService()
