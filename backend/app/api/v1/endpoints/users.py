from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_active_citizen
from app.models.user import User
from app.models.profile import UserProfile
from app.models.account_deletion import AccountDeletionRequest
from app.models.session import UserSession
from app.schemas.user import (
    UserResponse,
    UserProfileCreate,
    UserProfileUpdate,
    UserProfileResponse,
    AccountDeletionCreate,
    AccountDeletionResponse,
)
from app.schemas.auth import MessageResponse

router = APIRouter()


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current citizen user account information",
)
def get_user_me(current_user: User = Depends(get_current_active_citizen)):
    """Fetch current authenticated citizen user details including associated profile."""
    return current_user


@router.get(
    "/me/profile",
    response_model=UserProfileResponse,
    summary="Get current citizen profile",
)
def get_user_profile(
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Retrieve citizen profile for scheme eligibility evaluations."""
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Citizen profile not found. Please complete profile setup.",
        )
    return profile


@router.put(
    "/me/profile",
    response_model=UserProfileResponse,
    summary="Create or replace citizen profile",
)
def upsert_user_profile(
    profile_data: UserProfileCreate,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Create or overwrite citizen profile.
    
    Privacy rule: Only current authenticated citizen's profile is updated.
    Arbitrary user IDs in client payloads are strictly prohibited.
    """
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()

    if profile:
        profile.full_name = profile_data.full_name
        profile.date_of_birth = profile_data.date_of_birth
        profile.state = profile_data.state
        profile.district = profile_data.district
        profile.residence_type = profile_data.residence_type
        profile.annual_family_income = profile_data.annual_family_income
        profile.occupation = profile_data.occupation
        profile.education_level = profile_data.education_level
    else:
        profile = UserProfile(
            user_id=current_user.id,
            full_name=profile_data.full_name,
            date_of_birth=profile_data.date_of_birth,
            state=profile_data.state,
            district=profile_data.district,
            residence_type=profile_data.residence_type,
            annual_family_income=profile_data.annual_family_income,
            occupation=profile_data.occupation,
            education_level=profile_data.education_level,
        )
        db.add(profile)

    db.commit()
    db.refresh(profile)
    return profile


@router.patch(
    "/me/profile",
    response_model=UserProfileResponse,
    summary="Partially update citizen profile",
)
def patch_user_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Partially update specific fields in citizen profile."""
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Please create a profile first.",
        )

    update_dict = profile_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile


@router.delete(
    "/me/profile",
    response_model=MessageResponse,
    summary="Request citizen profile removal",
)
def delete_user_profile(
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Remove citizen demographic profile data."""
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found.",
        )
    db.delete(profile)
    db.commit()
    return MessageResponse(
        status="success",
        message="Citizen profile data removed successfully.",
    )


@router.post(
    "/me/delete-request",
    response_model=AccountDeletionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit an account deletion request",
)
def request_account_deletion(
    request_data: AccountDeletionCreate,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    """Submit an account deletion request.
    
    Privacy Architecture Rules:
    1. Revokes all active refresh sessions immediately.
    2. Schedules deletion after 30-day statutory retention window.
    3. Retains audit compliance data safely without immediate destructive wipe.
    """
    now = datetime.now(timezone.utc)
    scheduled_for = now + timedelta(days=settings.ACCOUNT_DELETION_RETENTION_DAYS)

    # Check for existing pending request
    existing = (
        db.query(AccountDeletionRequest)
        .filter(
            AccountDeletionRequest.user_id == current_user.id,
            AccountDeletionRequest.status == "pending",
        )
        .first()
    )

    if existing:
        return AccountDeletionResponse(
            status="pending",
            message="An account deletion request is already pending.",
            request_id=existing.id,
            requested_at=existing.requested_at,
            scheduled_for=existing.scheduled_for,
        )

    deletion_req = AccountDeletionRequest(
        user_id=current_user.id,
        status="pending",
        reason=request_data.reason,
        requested_at=now,
        scheduled_for=scheduled_for,
    )
    db.add(deletion_req)

    # Deactivate citizen account upon deletion request to prevent access during retention
    current_user.is_active = False

    # Revoke all active sessions immediately
    db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.is_revoked == False,
    ).update({"is_revoked": True})

    db.commit()
    db.refresh(deletion_req)

    return AccountDeletionResponse(
        status="pending",
        message="Account deletion request received. All active sessions have been revoked. Scheduled for permanent processing.",
        request_id=deletion_req.id,
        requested_at=deletion_req.requested_at,
        scheduled_for=deletion_req.scheduled_for,
    )

