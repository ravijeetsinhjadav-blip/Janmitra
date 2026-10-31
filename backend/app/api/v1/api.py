from fastapi import APIRouter
from app.api.v1.endpoints import auth, schemes, users, documents, advisory, assistance

api_router = APIRouter()

# Authentication & Session Management (Phase 3)
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# Citizen User & Profile Management (Phase 3)
api_router.include_router(users.router, prefix="/users", tags=["Users & Profiles"])

# Government Scheme Discovery & Eligibility Engine (Phase 4)
api_router.include_router(schemes.router, prefix="/schemes", tags=["Schemes & Eligibility"])

# Document Vault & OCR Pipeline (Phase 5)
api_router.include_router(documents.router, prefix="/documents", tags=["Document Vault & OCR"])

# AI Advisory & Readiness Assessment Engine (Phase 6)
api_router.include_router(advisory.router, tags=["AI Advisory & Readiness"])

# Application Assistance Module (Phase 7.1)
api_router.include_router(assistance.router, prefix="/assistance", tags=["Application Assistance"])




