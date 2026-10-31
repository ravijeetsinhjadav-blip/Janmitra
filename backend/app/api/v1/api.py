from fastapi import APIRouter
from app.api.v1.endpoints import auth, users

api_router = APIRouter()

# Authentication & Session Management (Phase 3)
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# Citizen User & Profile Management (Phase 3)
api_router.include_router(users.router, prefix="/users", tags=["Users & Profiles"])
