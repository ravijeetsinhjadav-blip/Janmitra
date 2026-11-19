import uuid
import math
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.notification import Notification, DeviceToken
from app.models.user import User


class FCMDispatchResult:
    def __init__(self, success_count: int, failure_count: int, invalid_tokens: List[str]):
        self.success_count = success_count
        self.failure_count = failure_count
        self.invalid_tokens = invalid_tokens


class BaseFCMAdapter(ABC):
    @abstractmethod
    def send_multicast(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
    ) -> FCMDispatchResult:
        pass


class MockFCMAdapter(BaseFCMAdapter):
    """High-fidelity in-memory mock adapter for deterministic test automation and offline development.
    Never initiates external cloud network connections.
    """
    def __init__(self):
        self.sent_dispatches: List[Dict[str, Any]] = []
        self.invalid_tokens_to_simulate: set = set()

    def send_multicast(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
    ) -> FCMDispatchResult:
        valid_tokens = [t for t in tokens if t not in self.invalid_tokens_to_simulate]
        invalid_tokens = [t for t in tokens if t in self.invalid_tokens_to_simulate]

        self.sent_dispatches.append({
            "tokens": valid_tokens,
            "title": title,
            "body": body,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc),
        })

        return FCMDispatchResult(
            success_count=len(valid_tokens),
            failure_count=len(invalid_tokens),
            invalid_tokens=invalid_tokens,
        )

    def clear(self):
        self.sent_dispatches.clear()
        self.invalid_tokens_to_simulate.clear()


class FirebaseAdminAdapter(BaseFCMAdapter):
    """Production FCM adapter using firebase-admin SDK.
    Strictly isolates privileged credentials to backend server.
    """
    def __init__(self):
        self._initialized = False
        try:
            import firebase_admin
            from firebase_admin import messaging, credentials
            if not firebase_admin._apps:
                # Initialize using default application credentials
                firebase_admin.initialize_app()
            self._messaging = messaging
            self._initialized = True
        except Exception:
            self._initialized = False

    def send_multicast(
        self,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
    ) -> FCMDispatchResult:
        if not self._initialized:
            # In development/fallback, return safe result
            return FCMDispatchResult(success_count=0, failure_count=len(tokens), invalid_tokens=[])

        try:
            notification = self._messaging.Notification(title=title, body=body)
            message = self._messaging.MulticastMessage(
                tokens=tokens,
                notification=notification,
                data=data or {},
            )
            response = self._messaging.send_each_for_multicast(message)

            invalid_tokens = []
            for idx, resp in enumerate(response.responses):
                if not resp.success:
                    err = resp.exception
                    # Check for unregistered/invalid tokens
                    if err and hasattr(err, "code") and err.code in ("UNREGISTERED", "INVALID_ARGUMENT"):
                        invalid_tokens.append(tokens[idx])

            return FCMDispatchResult(
                success_count=response.success_count,
                failure_count=response.failure_count,
                invalid_tokens=invalid_tokens,
            )
        except Exception:
            return FCMDispatchResult(success_count=0, failure_count=len(tokens), invalid_tokens=[])


class FCMService:
    """Service managing citizen device tokens, in-app notification ledger, and push delivery."""

    _adapter: BaseFCMAdapter = MockFCMAdapter()

    @classmethod
    def get_adapter(cls) -> BaseFCMAdapter:
        return cls._adapter

    @classmethod
    def set_adapter(cls, adapter: BaseFCMAdapter) -> None:
        cls._adapter = adapter

    @classmethod
    def register_device_token(
        cls,
        db: Session,
        user: User,
        device_token: str,
        device_type: str = "android",
    ) -> DeviceToken:
        """Register or refresh a device token under authenticated citizen ownership."""
        token_str = device_token.strip()
        existing = db.query(DeviceToken).filter(DeviceToken.device_token == token_str).first()

        now = datetime.now(timezone.utc)
        if existing:
            # Reassign to current user if previously registered on another account, reactivate
            existing.user_id = user.id
            existing.device_type = device_type
            existing.is_active = True
            existing.updated_at = now
            db.commit()
            db.refresh(existing)
            return existing

        new_record = DeviceToken(
            user_id=user.id,
            device_token=token_str,
            device_type=device_type,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        return new_record

    @classmethod
    def deactivate_device_token(
        cls,
        db: Session,
        user: User,
        device_token: str,
    ) -> bool:
        """Deactivate device token on logout with ownership verification."""
        token_str = device_token.strip()
        record = db.query(DeviceToken).filter(
            DeviceToken.device_token == token_str,
            DeviceToken.user_id == user.id,
        ).first()

        if record:
            record.is_active = False
            record.updated_at = datetime.now(timezone.utc)
            db.commit()
            return True
        return False

    @classmethod
    def dispatch_notification(
        cls,
        db: Session,
        user_id: uuid.UUID,
        title: str,
        message: str,
        notification_type: str = "system",
        data: Optional[Dict[str, str]] = None,
    ) -> Notification:
        """Persist in-app notification record and deliver via FCM push to user active devices."""
        now = datetime.now(timezone.utc)
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            is_read=False,
            created_at=now,
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)

        # Query user active device tokens
        active_tokens = db.query(DeviceToken.device_token).filter(
            DeviceToken.user_id == user_id,
            DeviceToken.is_active == True,
        ).all()

        token_list = [t[0] for t in active_tokens]
        if token_list:
            dispatch_data = data or {}
            dispatch_data["notification_id"] = str(notification.id)
            dispatch_data["notification_type"] = notification_type

            result = cls._adapter.send_multicast(
                tokens=token_list,
                title=title,
                body=message,
                data=dispatch_data,
            )

            # Invalidate expired tokens if reported by gateway
            if result.invalid_tokens:
                db.query(DeviceToken).filter(
                    DeviceToken.device_token.in_(result.invalid_tokens),
                ).update({"is_active": False}, synchronize_session=False)
                db.commit()

        return notification

    @classmethod
    def list_user_notifications(
        cls,
        db: Session,
        user: User,
        page: int = 1,
        page_size: int = 20,
        is_read: Optional[bool] = None,
    ) -> Tuple[List[Notification], int, int, int]:
        """List citizen in-app notifications with pagination and strict tenant isolation."""
        query = db.query(Notification).filter(Notification.user_id == user.id)

        if is_read is not None:
            query = query.filter(Notification.is_read == is_read)

        total = query.count()
        unread_count = db.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.is_read == False,
        ).count()

        total_pages = math.ceil(total / page_size) if total > 0 else 0
        offset = (page - 1) * page_size
        items = query.order_by(Notification.created_at.desc()).offset(offset).limit(page_size).all()

        return items, total, unread_count, total_pages

    @classmethod
    def mark_notification_as_read(
        cls,
        db: Session,
        user: User,
        notification_id: uuid.UUID,
    ) -> Notification:
        """Mark single notification as read with strict IDOR verification."""
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user.id,
        ).first()

        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )

        notification.is_read = True
        db.commit()
        db.refresh(notification)
        return notification

    @classmethod
    def mark_all_notifications_as_read(
        cls,
        db: Session,
        user: User,
    ) -> int:
        """Mark all unread notifications as read for authenticated citizen."""
        updated_count = db.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.is_read == False,
        ).update({"is_read": True}, synchronize_session=False)

        db.commit()
        return updated_count

    @classmethod
    def get_unread_count(
        cls,
        db: Session,
        user: User,
    ) -> int:
        """Get instant unread count for badge indicators."""
        return db.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.is_read == False,
        ).count()

