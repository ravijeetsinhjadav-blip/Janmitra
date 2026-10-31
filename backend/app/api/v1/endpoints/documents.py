import uuid
from typing import Optional
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    UploadFile,
    Response,
    status,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_active_citizen
from app.models.user import User
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentMetadataResponse,
    DocumentListResponse,
    SchemeDocumentChecklistResponse,
)
from app.services.document_service import document_service

router = APIRouter()


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload citizen document to vault",
    description="Upload a PDF, JPG, JPEG, or PNG document. Validates size & magic bytes, stores securely, and runs OCR.",
)
def upload_document(
    document_type: str = Form(..., description="Document type: income_certificate, caste_certificate, ration_card, etc."),
    file: UploadFile = File(..., description="Binary document file"),
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Securely upload document and perform OCR extraction."""
    doc = document_service.upload_document(
        db=db,
        user=current_user,
        file=file,
        document_type=document_type,
    )
    return DocumentUploadResponse(
        message="Document uploaded and processed successfully.",
        document=DocumentMetadataResponse.model_validate(doc),
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List citizen vault documents",
    description="Retrieve all documents in the authenticated user's secure vault.",
)
def list_documents(
    document_type: Optional[str] = None,
    ocr_status: Optional[str] = None,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """List documents belonging to current authenticated citizen."""
    docs = document_service.list_user_documents(
        db=db,
        user=current_user,
        document_type=document_type,
        ocr_status=ocr_status,
    )
    return DocumentListResponse(
        total=len(docs),
        documents=[DocumentMetadataResponse.model_validate(d) for d in docs],
    )


@router.get(
    "/scheme/{scheme_id}/checklist",
    response_model=SchemeDocumentChecklistResponse,
    summary="Check scheme document requirements against citizen vault",
    description="Compare citizen's uploaded documents with a scheme's required checklist.",
)
def get_scheme_document_checklist(
    scheme_id: uuid.UUID,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Retrieve document readiness checklist for a specific scheme."""
    return document_service.get_scheme_document_checklist(
        db=db,
        scheme_id=scheme_id,
        user=current_user,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentMetadataResponse,
    summary="Get document details & OCR text",
    description="Retrieve metadata, OCR extracted text, and review status for a specific document.",
)
def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Get single document metadata and OCR results."""
    doc = document_service.get_document_by_id(db=db, document_id=document_id, user=current_user)
    return DocumentMetadataResponse.model_validate(doc)


@router.get(
    "/{document_id}/download",
    summary="Download/view document file",
    description="Download binary content for an owned document file.",
)
def download_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Stream binary document file with correct MIME type headers."""
    file_bytes, mime_type, filename = document_service.get_document_file(
        db=db,
        document_id=document_id,
        user=current_user,
    )
    safe_filename = document_service.sanitize_header_filename(filename)
    return Response(
        content=file_bytes,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{safe_filename}"',
            "Cache-Control": "private, no-cache, no-store, must-revalidate",
            "X-Content-Type-Options": "nosniff",
        },
    )



@router.delete(
    "/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete document from vault",
    description="Permanently deletes the document file and its metadata.",
)
def delete_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Delete a document from user's vault."""
    document_service.delete_document(db=db, document_id=document_id, user=current_user)
    return {"message": "Document deleted successfully."}


@router.post(
    "/{document_id}/retry-ocr",
    response_model=DocumentMetadataResponse,
    summary="Retry OCR extraction",
    description="Re-run OCR extraction for a document (e.g. if previous OCR failed or required review).",
)
def retry_ocr(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Re-run OCR processing on document."""
    doc = document_service.retry_ocr(db=db, document_id=document_id, user=current_user)
    return DocumentMetadataResponse.model_validate(doc)

