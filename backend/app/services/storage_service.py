import os
import uuid
import re
from pathlib import Path
from typing import Tuple, Optional
from fastapi import HTTPException, status
from app.core.config import settings

# Recognized magic byte signatures
MAGIC_SIGNATURES = {
    "pdf": [b"%PDF"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "png": [b"\x89PNG\r\n\x1a\n", b"\x89PNG"],
    "webp": [b"RIFF"],
}

MIME_TYPE_MAPPING = {
    "pdf": "application/pdf",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


class StorageService:
    """Secure document storage manager.
    
    Adheres strictly to the JanMitra Assist Privacy & Security architecture:
    - Binary files are stored exclusively on secure filesystem disk, NEVER in PostgreSQL.
    - Path traversal attacks are mitigated by sanitizing filenames and using generated opaque UUID keys.
    - Enforces magic byte verification to prevent extension spoofing.
    - Enforces configurable maximum file size limit (default 10 MB).
    """

    def __init__(self, base_storage_path: Optional[str] = None):
        self.base_path = Path(base_storage_path or settings.DOCUMENT_STORAGE_PATH).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def validate_file(
        self,
        file_bytes: bytes,
        filename: str,
        declared_content_type: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Validate file size, extension, and content magic bytes.
        
        Returns:
            Tuple of (detected_mime_type, normalized_extension)
        Raises:
            HTTPException with 400 status if validation fails.
        """
        # 1. Size check
        if not file_bytes or len(file_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty.",
            )

        if len(file_bytes) > settings.MAX_DOCUMENT_FILE_SIZE_BYTES:
            max_mb = settings.MAX_DOCUMENT_FILE_SIZE_BYTES // (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds the maximum allowed limit of {max_mb} MB.",
            )

        # 2. Extension check
        raw_ext = filename.rsplit(".", 1)[-1].strip().lower() if filename and "." in filename else ""
        allowed = settings.allowed_extensions
        if raw_ext and raw_ext not in allowed and raw_ext not in ("tmp", "temp", "jpeg", "jpg", "png", "pdf", "webp"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file extension '.{raw_ext}'. Allowed formats: {', '.join(allowed)}.",
            )

        # 3. Magic byte signature verification
        is_signature_valid = False
        detected_format = None
        for fmt, sigs in MAGIC_SIGNATURES.items():
            for sig in sigs:
                if file_bytes.startswith(sig):
                    if fmt == "webp":
                        # Verify WEBP magic at offset 8-12
                        if len(file_bytes) >= 12 and file_bytes[8:12] == b"WEBP":
                            is_signature_valid = True
                            detected_format = "webp"
                            break
                    else:
                        is_signature_valid = True
                        detected_format = fmt
                        break
            if is_signature_valid:
                break

        # Fallback inspection via PIL Image for valid image streams
        if not is_signature_valid:
            try:
                import io
                from PIL import Image
                with Image.open(io.BytesIO(file_bytes)) as pil_img:
                    fmt = (pil_img.format or "").lower()
                    if fmt in ("jpeg", "jpg"):
                        detected_format = "jpg"
                        is_signature_valid = True
                    elif fmt == "png":
                        detected_format = "png"
                        is_signature_valid = True
                    elif fmt == "webp":
                        detected_format = "webp"
                        is_signature_valid = True
            except Exception:
                pass

        if not is_signature_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File content signature validation failed. Please upload a valid document or photo (PDF, JPG, PNG, WEBP).",
            )

        # 3. Extension resolution & auto-normalization
        raw_ext = ""
        if filename and "." in filename:
            raw_ext = filename.rsplit(".", 1)[-1].strip().lower()

        # If extension is missing, unknown, or mismatched with detected bytes, auto-correct to detected format
        normalized_ext = "jpg" if detected_format in ("jpg", "jpeg") else detected_format
        mime_type = MIME_TYPE_MAPPING.get(normalized_ext, declared_content_type or "application/octet-stream")
        return mime_type, normalized_ext

    def sanitize_filename(self, filename: str) -> str:
        """Strip insecure characters and path traversal segments from original filename."""
        clean = Path(filename).name  # Strips directory paths
        clean = re.sub(r'[^a-zA-Z0-9_.-]', '_', clean)
        return clean or "document"

    def sanitize_header_filename(self, filename: str) -> str:
        """Sanitize filename specifically for use in HTTP Content-Disposition headers.
        
        Prevents HTTP Response Splitting, CRLF injection, and quote escape attacks.
        """
        # Strip path traversal and quotes/CRLF
        clean = Path(filename).name
        clean = re.sub(r'[\r\n\t"\';]', '', clean)
        clean = re.sub(r'[^a-zA-Z0-9_.-]', '_', clean)
        return clean or "document"


    def save_file(
        self,
        user_id: uuid.UUID,
        file_bytes: bytes,
        extension: str,
    ) -> str:
        """Persist file to disk using opaque UUID storage reference.
        
        Structure: <base_path>/<user_id>/<doc_uuid>.<ext>
        Returns:
            storage_reference string
        """
        user_folder = self.base_path / str(user_id)
        user_folder.mkdir(parents=True, exist_ok=True)

        opaque_filename = f"{uuid.uuid4().hex}.{extension.lower().lstrip('.')}"
        target_path = user_folder / opaque_filename

        with open(target_path, "wb") as f:
            f.write(file_bytes)

        # Storage reference is relative to base_path or a standardized key
        # e.g., "storage/documents/<user_id>/<file>"
        storage_reference = str(Path(str(user_id)) / opaque_filename).replace("\\", "/")
        return storage_reference

    def resolve_path(self, storage_reference: str) -> Path:
        """Resolve storage reference safely, checking against directory traversal."""
        # Normalize and resolve
        resolved = (self.base_path / storage_reference).resolve()
        # Verify the resolved path starts with the base path
        try:
            resolved.relative_to(self.base_path)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid storage reference or directory traversal detected.",
            )
        return resolved

    def get_file_bytes(self, storage_reference: str) -> bytes:
        """Read document binary content from disk."""
        target_path = self.resolve_path(storage_reference)
        if not target_path.exists() or not target_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document file not found on storage.",
            )
        return target_path.read_bytes()

    def delete_file(self, storage_reference: str) -> bool:
        """Safely delete document binary from disk."""
        try:
            target_path = self.resolve_path(storage_reference)
            if target_path.exists() and target_path.is_file():
                target_path.unlink()
                return True
        except Exception:
            return False
        return False


storage_service = StorageService()

