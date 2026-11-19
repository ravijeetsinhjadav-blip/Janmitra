import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DeviceTokenRegister(BaseModel):
    device_token: str = Field(..., min_length=10, max_length=255, description="FCM device registration token")
    device_type: str = Field(default="android", pattern="^(android|ios|web)$", description="Device platform")


class DeviceTokenResponse(BaseModel):
    id: uuid.UUID
    device_token: str
    device_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    message: str
    notification_type: str
    scheduled_at: Optional[datetime] = None
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    total: int
    unread_count: int
    page: int
    page_size: int
    total_pages: int
    notifications: List[NotificationResponse]


class NotificationReadResponse(BaseModel):
    id: uuid.UUID
    is_read: bool
    message: str = "Notification marked as read."


class UnreadCountResponse(BaseModel):
    unread_count: int

