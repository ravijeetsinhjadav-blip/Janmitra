from fastapi import APIRouter
from app.api.v1.endpoints import auth, schemes, users

api_router = APIRouter()

# Authentication & Session Management (Phase 3)
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# Citizen User & Profile Management (Phase 3)
api_router.include_router(users.router, prefix="/users", tags=["Users & Profiles"])

# Government Scheme Discovery & Eligibility Engine (Phase 4)
api_router.include_router(schemes.router, prefix="/schemes", tags=["Schemes & Eligibility"])

