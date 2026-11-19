import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_citizen
from app.models.user import User
from app.schemas.notification import (
    DeviceTokenRegister,
    DeviceTokenResponse,
    NotificationResponse,
    NotificationListResponse,
    NotificationReadResponse,
    UnreadCountResponse,
)
from app.services.fcm_service import FCMService

router = APIRouter()


@router.post(
    "/devices",
    response_model=DeviceTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Register or refresh FCM device token",
    description="Registers an FCM device token under the authenticated citizen's account for push notifications.",
)
def register_device(
    payload: DeviceTokenRegister,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    record = FCMService.register_device_token(
        db=db,
        user=current_user,
        device_token=payload.device_token,
        device_type=payload.device_type,
    )
    return DeviceTokenResponse.model_validate(record)


@router.delete(
    "/devices/{device_token}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate device token on logout",
    description="Deactivates an active device token associated with the authenticated caller.",
)
def deactivate_device(
    device_token: str,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    FCMService.deactivate_device_token(
        db=db,
        user=current_user,
        device_token=device_token,
    )
    return {"status": "success", "message": "Device token deactivated."}


@router.get(
    "",
    response_model=NotificationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List citizen notifications",
    description="Retrieve paginated in-app notifications for the authenticated citizen with unread count.",
)
def list_notifications(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    is_read: Optional[bool] = Query(None, description="Filter by read receipt status"),
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    items, total, unread_count, total_pages = FCMService.list_user_notifications(
        db=db,
        user=current_user,
        page=page,
        page_size=page_size,
        is_read=is_read,
    )
    return NotificationListResponse(
        total=total,
        unread_count=unread_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        notifications=[NotificationResponse.model_validate(item) for item in items],
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationReadResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark notification as read",
    description="Update read receipt for a single notification with citizen ownership verification.",
)
def mark_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    notif = FCMService.mark_notification_as_read(
        db=db,
        user=current_user,
        notification_id=notification_id,
    )
    return NotificationReadResponse(
        id=notif.id,
        is_read=notif.is_read,
    )


@router.post(
    "/read-all",
    status_code=status.HTTP_200_OK,
    summary="Mark all notifications as read",
    description="Mark all unread in-app notifications as read for the authenticated caller.",
)
def mark_all_read(
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    count = FCMService.mark_all_notifications_as_read(
        db=db,
        user=current_user,
    )
    return {"status": "success", "marked_read_count": count}


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    status_code=status.HTTP_200_OK,
    summary="Get unread notification count",
    description="Fast badge counter endpoint returning number of unread notifications.",
)
def get_unread_count(
    current_user: User = Depends(get_current_active_citizen),
    db: Session = Depends(get_db),
):
    count = FCMService.get_unread_count(
        db=db,
        user=current_user,
    )
    return UnreadCountResponse(unread_count=count)

