import uuid
import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, UploadFile

from app.core.database import SessionLocal
from app.models.document import DocumentMetadata, DocumentProcessingStatus
from app.models.scheme import Scheme
from app.models.user import User
from app.services.storage_service import storage_service
from app.services.ocr_service import ocr_service, sanitize_ocr_error_message, OCRResult
from app.services.subscription_service import SubscriptionService
from app.schemas.document import (
    DocumentMetadataResponse,
    DocumentListResponse,
    SchemeDocumentChecklistResponse,
    SchemeDocumentChecklistItem,
)

logger = logging.getLogger(__name__)


class DocumentService:
    """Business logic for JanMitra Document Vault & OCR Pipeline."""

    @staticmethod
    def upload_document(
        db: Session,
        user: User,
        file: UploadFile,
        document_type: str,
    ) -> DocumentMetadata:
        """Validate, reserve quota, persist to disk, run OCR, and store metadata (SEC-05, SEC-06, AUD-03, AUD-04)."""
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename cannot be empty.",
            )

        sanitized_filename = storage_service.sanitize_filename(file.filename)
        
        # Read file contents
        try:
            file_bytes = file.file.read()
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to read uploaded file: {str(exc)}",
            )

        # 1. Phase 0: Validate file size, extension, and magic bytes (ZERO quota touched if invalid)
        detected_mime, normalized_ext = storage_service.validate_file(
            file_bytes=file_bytes,
            filename=sanitized_filename,
            declared_content_type=file.content_type,
        )

        # 2. Phase 1: Concurrency-safe quota reservation under pessimistic row lock
        SubscriptionService.reserve_document_analysis_quota(db=db, user_id=user.id)

        # 3. Save to disk with opaque storage reference
        storage_reference = storage_service.save_file(
            user_id=user.id,
            file_bytes=file_bytes,
            extension=normalized_ext,
        )

        # 4. Generate worker processing lease token and expiration (AUD-03, AUD-04)
        processing_token = uuid.uuid4()
        now = datetime.now(timezone.utc)
        lease_expires_at = now + timedelta(seconds=300)

        # Create DocumentMetadata record in PROCESSING status to hold in-flight reservation
        doc_record = DocumentMetadata(
            user_id=user.id,
            document_type=document_type.strip().lower(),
            original_filename=sanitized_filename,
            storage_reference=storage_reference,
            mime_type=detected_mime,
            file_size=len(file_bytes),
            upload_status="uploaded",
            ocr_status=DocumentProcessingStatus.PROCESSING,
            processing_token=processing_token,
            lease_expires_at=lease_expires_at,
            ocr_extracted_text=None,
            ocr_confidence=0.0,
            ocr_metadata={},
            ocr_completed_at=None,
            manual_review_required=False,
            ocr_error_message=None,
        )

        try:
            db.add(doc_record)
            db.commit()
            db.refresh(doc_record)
        except Exception as exc:
            db.rollback()
            storage_service.delete_file(storage_reference)
            logger.error("Failed to persist initial document metadata: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred while persisting document metadata.",
            )

        # 5. Phase 2: Execute OCR processing with active lease heartbeat (AUD-03, AUD-04)
        stop_heartbeat = threading.Event()

        def _heartbeat_worker():
            while not stop_heartbeat.wait(timeout=30.0):
                try:
                    hb_db = SessionLocal()
                    SubscriptionService.renew_document_lease(
                        db=hb_db,
                        doc_id=doc_record.id,
                        processing_token=processing_token,
                        extend_seconds=300,
                    )
                    hb_db.close()
                except Exception as hb_exc:
                    logger.debug(f"Heartbeat renewal error for doc {doc_record.id}: {hb_exc}")

        hb_thread = threading.Thread(target=_heartbeat_worker, daemon=True)
        hb_thread.start()

        try:
            ocr_result = ocr_service.process_document(
                file_bytes=file_bytes,
                mime_type=detected_mime,
                document_type=document_type,
                filename=sanitized_filename,
            )
        except Exception as exc:
            safe_msg = sanitize_ocr_error_message(str(exc))
            logger.error("OCR service exception: %s", safe_msg)
            ocr_result = OCRResult(
                extracted_text="",
                confidence=0.0,
                metadata={"error": safe_msg},
                status=DocumentProcessingStatus.OCR_FAILED,
                manual_review_required=True,
                error_message=f"OCR execution failure: {safe_msg}",
            )
        finally:
            stop_heartbeat.set()
            hb_thread.join(timeout=1.0)

        # 6. Phase 3: Finalize or Release quota based on OCR outcome with lease token verification
        if ocr_result and ocr_result.status in [
            DocumentProcessingStatus.OCR_COMPLETED,
            DocumentProcessingStatus.MANUAL_REVIEW_REQUIRED,
        ]:
            # Atomic lease verification and finalization
            finalized = SubscriptionService.finalize_document_analysis(
                db=db,
                user_id=user.id,
                doc_id=doc_record.id,
                processing_token=processing_token,
            )
            if finalized:
                doc_record.ocr_status = ocr_result.status
                doc_record.ocr_extracted_text = ocr_result.extracted_text
                doc_record.ocr_confidence = ocr_result.confidence
                doc_record.ocr_metadata = ocr_result.metadata
                doc_record.ocr_completed_at = ocr_result.completed_at
                doc_record.manual_review_required = ocr_result.manual_review_required
                doc_record.ocr_error_message = ocr_result.error_message
                doc_record.processing_token = None
                doc_record.lease_expires_at = None
                try:
                    db.commit()
                    db.refresh(doc_record)
                except Exception as exc:
                    db.rollback()
                    logger.error("Failed to update completed document status: %s", exc)
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Database error occurred while updating document status.",
                    )
            else:
                logger.warning(
                    f"Lease expired/revoked for document {doc_record.id}. Discarding stale worker finalization."
                )
        else:
            # Failure: mark document as OCR_FAILED and release quota reservation with token check
            released = SubscriptionService.release_document_analysis_quota(
                db=db,
                user_id=user.id,
                doc_id=doc_record.id,
                processing_token=processing_token,
            )
            if released:
                doc_record.ocr_status = DocumentProcessingStatus.OCR_FAILED
                doc_record.ocr_extracted_text = ocr_result.extracted_text if ocr_result else None
                doc_record.ocr_confidence = ocr_result.confidence if ocr_result else 0.0
                doc_record.ocr_metadata = ocr_result.metadata if ocr_result else {}
                doc_record.ocr_completed_at = ocr_result.completed_at if ocr_result else None
                doc_record.manual_review_required = True
                doc_record.ocr_error_message = (
                    ocr_result.error_message if ocr_result else "OCR execution failure"
                )
                doc_record.processing_token = None
                doc_record.lease_expires_at = None
                try:
                    db.commit()
                    db.refresh(doc_record)
                except Exception as exc:
                    db.rollback()
                    logger.error("Failed to update failed document status: %s", exc)
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Database error occurred while updating document status.",
                    )

        return doc_record

    @staticmethod
    def list_user_documents(
        db: Session,
        user: User,
        document_type: Optional[str] = None,
        ocr_status: Optional[str] = None,
    ) -> List[DocumentMetadata]:
        """Fetch all documents belonging to the authenticated citizen."""
        query = db.query(DocumentMetadata).filter(DocumentMetadata.user_id == user.id)

        if document_type:
            query = query.filter(DocumentMetadata.document_type == document_type.strip().lower())
        if ocr_status:
            query = query.filter(DocumentMetadata.ocr_status == ocr_status.strip().upper())

        return query.order_by(DocumentMetadata.created_at.desc()).all()

    @staticmethod
    def get_document_by_id(
        db: Session,
        document_id: uuid.UUID,
        user: User,
    ) -> DocumentMetadata:
        """Fetch a specific document record, enforcing ownership authorization (prevents IDOR)."""
        doc = db.query(DocumentMetadata).filter(DocumentMetadata.id == document_id).first()
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found.",
            )

        # Enforce strict user ownership
        if doc.user_id != user.id and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this document.",
            )

        return doc

    @staticmethod
    def sanitize_header_filename(filename: str) -> str:
        """Sanitize filename to prevent header injection."""
        return storage_service.sanitize_header_filename(filename)

    @staticmethod
    def get_document_file(
        db: Session,
        document_id: uuid.UUID,
        user: User,
    ) -> Tuple[bytes, str, str]:
        """Retrieve binary file bytes for download/viewing."""
        doc = DocumentService.get_document_by_id(db, document_id, user)
        file_bytes = storage_service.get_file_bytes(doc.storage_reference)
        return file_bytes, doc.mime_type, doc.original_filename

    @staticmethod
    def delete_document(
        db: Session,
        document_id: uuid.UUID,
        user: User,
    ) -> bool:
        """Delete document file from storage and remove record from database."""
        doc = DocumentService.get_document_by_id(db, document_id, user)
        storage_ref = doc.storage_reference

        # Remove from database
        try:
            db.delete(doc)
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.error("Failed to delete document metadata from database: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred while deleting document record.",
            )

        # Remove binary file from disk
        storage_service.delete_file(storage_ref)
        return True

    @staticmethod
    def retry_ocr(
        db: Session,
        document_id: uuid.UUID,
        user: User,
    ) -> DocumentMetadata:
        """Re-run OCR extraction on a failed document with concurrency and quota safety (AUD-03, AUD-04, AUD-05, AUD-06)."""
        # 1. Fetch document under exclusive row lock to serialize concurrent retry attempts (AUD-06)
        doc = (
            db.query(DocumentMetadata)
            .filter(DocumentMetadata.id == document_id)
            .with_for_update()
            .first()
        )
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found.",
            )

        # Enforce strict user ownership
        if doc.user_id != user.id and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this document.",
            )

        # 2. Reject retries for already successful or review-pending documents (AUD-05)
        if doc.ocr_status in [
            DocumentProcessingStatus.OCR_COMPLETED,
            DocumentProcessingStatus.MANUAL_REVIEW_REQUIRED,
        ]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Document OCR extraction is already '{doc.ocr_status}' and cannot be retried. "
                    "Retry is only permitted for failed document extractions."
                ),
            )

        # 3. Prevent duplicate concurrent processing
        if doc.ocr_status in [
            DocumentProcessingStatus.PROCESSING,
            DocumentProcessingStatus.PENDING_OCR,
        ]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="OCR extraction is already currently processing for this document.",
            )

        # Ensure strictly only OCR_FAILED documents are retryable
        if doc.ocr_status != DocumentProcessingStatus.OCR_FAILED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Document with status '{doc.ocr_status}' is not eligible for OCR retry.",
            )

        # 4. Reserve quota slot before processing (only eligible failed documents reach here)
        SubscriptionService.reserve_document_analysis_quota(db=db, user_id=user.id)

        file_bytes = storage_service.get_file_bytes(doc.storage_reference)

        # 5. Generate unique worker processing lease token and expiration (AUD-03, AUD-04)
        processing_token = uuid.uuid4()
        now = datetime.now(timezone.utc)
        lease_expires_at = now + timedelta(seconds=300)

        # Update status to processing under lease ownership
        doc.ocr_status = DocumentProcessingStatus.PROCESSING
        doc.processing_token = processing_token
        doc.lease_expires_at = lease_expires_at
        db.commit()
        db.refresh(doc)

        # 6. Run OCR with active lease heartbeat (AUD-03, AUD-04)
        stop_heartbeat = threading.Event()

        def _heartbeat_worker():
            while not stop_heartbeat.wait(timeout=30.0):
                try:
                    hb_db = SessionLocal()
                    SubscriptionService.renew_document_lease(
                        db=hb_db,
                        doc_id=doc.id,
                        processing_token=processing_token,
                        extend_seconds=300,
                    )
                    hb_db.close()
                except Exception as hb_exc:
                    logger.debug(f"Heartbeat renewal error for retry doc {doc.id}: {hb_exc}")

        hb_thread = threading.Thread(target=_heartbeat_worker, daemon=True)
        hb_thread.start()

        try:
            ocr_result = ocr_service.process_document(
                file_bytes=file_bytes,
                mime_type=doc.mime_type,
                document_type=doc.document_type,
                filename=doc.original_filename,
            )
        except Exception as exc:
            safe_msg = sanitize_ocr_error_message(str(exc))
            logger.error("OCR retry exception: %s", safe_msg)
            ocr_result = OCRResult(
                extracted_text="",
                confidence=0.0,
                metadata={"error": safe_msg},
                status=DocumentProcessingStatus.OCR_FAILED,
                manual_review_required=True,
                error_message=f"OCR execution failure: {safe_msg}",
            )
        finally:
            stop_heartbeat.set()
            hb_thread.join(timeout=1.0)

        # 7. Finalize or Release quota based on OCR outcome with lease token verification
        if ocr_result and ocr_result.status in [
            DocumentProcessingStatus.OCR_COMPLETED,
            DocumentProcessingStatus.MANUAL_REVIEW_REQUIRED,
        ]:
            finalized = SubscriptionService.finalize_document_analysis(
                db=db,
                user_id=user.id,
                doc_id=doc.id,
                processing_token=processing_token,
            )
            if finalized:
                doc.ocr_status = ocr_result.status
                doc.ocr_extracted_text = ocr_result.extracted_text
                doc.ocr_confidence = ocr_result.confidence
                doc.ocr_metadata = ocr_result.metadata
                doc.ocr_completed_at = ocr_result.completed_at
                doc.manual_review_required = ocr_result.manual_review_required
                doc.ocr_error_message = ocr_result.error_message
                doc.processing_token = None
                doc.lease_expires_at = None
                db.commit()
                db.refresh(doc)
            else:
                logger.warning(
                    f"Lease expired/revoked for document {doc.id}. Discarding stale retry finalization."
                )
        else:
            released = SubscriptionService.release_document_analysis_quota(
                db=db,
                user_id=user.id,
                doc_id=doc.id,
                processing_token=processing_token,
            )
            if released:
                doc.ocr_status = DocumentProcessingStatus.OCR_FAILED
                doc.ocr_extracted_text = ocr_result.extracted_text if ocr_result else None
                doc.ocr_confidence = ocr_result.confidence if ocr_result else 0.0
                doc.ocr_metadata = ocr_result.metadata if ocr_result else {}
                doc.ocr_completed_at = ocr_result.completed_at if ocr_result else None
                doc.manual_review_required = True
                doc.ocr_error_message = (
                    ocr_result.error_message if ocr_result else "OCR execution failure"
                )
                doc.processing_token = None
                doc.lease_expires_at = None
                db.commit()
                db.refresh(doc)

        return doc


    @staticmethod
    def get_scheme_document_checklist(
        db: Session,
        scheme_id: uuid.UUID,
        user: User,
    ) -> SchemeDocumentChecklistResponse:
        """Match citizen's uploaded documents with a scheme's required documents list."""
        scheme = db.query(Scheme).filter(Scheme.id == scheme_id).first()
        if not scheme:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scheme not found.",
            )

        # Fetch user's documents
        user_docs = db.query(DocumentMetadata).filter(DocumentMetadata.user_id == user.id).all()
        # Map user doc types to their records (latest first)
        user_doc_map = {}
        for d in sorted(user_docs, key=lambda x: x.created_at, reverse=True):
            norm_type = d.document_type.lower()
            if norm_type not in user_doc_map:
                user_doc_map[norm_type] = d

        checklist_items: List[SchemeDocumentChecklistItem] = []
        req_docs = scheme.required_documents or []

        for req in req_docs:
            if isinstance(req, str):
                doc_name = req
                doc_desc = None
                mandatory = True
            elif isinstance(req, dict):
                doc_name = req.get("name") or req.get("document_type", "")
                doc_desc = req.get("description")
                mandatory = req.get("is_mandatory", True)
            else:
                continue

            # Standardize match
            clean_key = doc_name.lower().replace(" ", "_").replace("-", "_")
            matched_doc = None
            for k, doc in user_doc_map.items():
                if k == clean_key or clean_key in k or k in clean_key:
                    matched_doc = doc
                    break

            is_uploaded = matched_doc is not None
            checklist_items.append(
                SchemeDocumentChecklistItem(
                    document_type=doc_name,
                    description=doc_desc,
                    is_mandatory=mandatory,
                    is_uploaded=is_uploaded,
                    uploaded_document_id=matched_doc.id if matched_doc else None,
                    ocr_status=matched_doc.ocr_status if matched_doc else None,
                    manual_review_required=matched_doc.manual_review_required if matched_doc else False,
                )
            )

        total_req = len(checklist_items)
        total_up = sum(1 for item in checklist_items if item.is_uploaded)

        return SchemeDocumentChecklistResponse(
            scheme_id=scheme.id,
            scheme_name=scheme.scheme_name,
            total_required=total_req,
            total_uploaded=total_up,
            is_fully_prepared=(total_up >= total_req) if total_req > 0 else True,
            checklist=checklist_items,
        )


document_service = DocumentService()

