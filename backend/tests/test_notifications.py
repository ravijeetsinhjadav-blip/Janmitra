import uuid
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.core.security import normalize_mobile_number
from app.models.user import User
from app.models.notification import Notification, DeviceToken
from app.services.fcm_service import FCMService, MockFCMAdapter


def get_auth_headers(client, mobile_number: str = "+919876543210") -> dict:
    """Authenticate citizen via Email+Password and return Bearer headers."""
    clean_id = "".join(c for c in mobile_number if c.isalnum()) or "default"
    email = f"user_{clean_id}@example.com"
    res_reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password@12345",
            "confirm_password": "Password@12345",
            "full_name": "Test Citizen",
            "mobile_number": mobile_number,
        },
    )
    if res_reg.status_code == 201:
        token = res_reg.json()["access_token"]
    else:
        res_login = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "Password@12345"},
        )
        token = res_login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestFCMAndNotificationsModule:
    @pytest.fixture(autouse=True)
    def setup_mock_fcm(self):
        adapter = MockFCMAdapter()
        FCMService.set_adapter(adapter)
        yield
        adapter.clear()

    def test_register_device_token_success(self, client: TestClient, db_session):
        mobile = "+919944000001"
        headers = get_auth_headers(client, mobile)
        user = db_session.query(User).filter(User.mobile_number == normalize_mobile_number(mobile)).first()

        token_str = "fcm_token_sample_abc123456789"
        response = client.post(
            "/api/v1/notifications/devices",
            headers=headers,
            json={"device_token": token_str, "device_type": "android"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["device_token"] == token_str
        assert data["device_type"] == "android"
        assert data["is_active"] is True

        # Verify persisted in database
        db_token = db_session.query(DeviceToken).filter(DeviceToken.device_token == token_str).first()
        assert db_token is not None
        assert db_token.user_id == user.id
        assert db_token.is_active is True

    def test_reregister_existing_token_updates_timestamp_and_activates(self, client: TestClient, db_session):
        mobile = "+919944000002"
        headers = get_auth_headers(client, mobile)

        token_str = "fcm_token_sample_reactivate_987"
        client.post(
            "/api/v1/notifications/devices",
            headers=headers,
            json={"device_token": token_str, "device_type": "android"},
        )
        # Deactivate
        client.delete(f"/api/v1/notifications/devices/{token_str}", headers=headers)
        db_token = db_session.query(DeviceToken).filter(DeviceToken.device_token == token_str).first()
        assert db_token.is_active is False

        # Re-register
        response = client.post(
            "/api/v1/notifications/devices",
            headers=headers,
            json={"device_token": token_str, "device_type": "ios"},
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is True
        assert response.json()["device_type"] == "ios"

    def test_deactivate_device_token(self, client: TestClient, db_session):
        mobile = "+919944000003"
        headers = get_auth_headers(client, mobile)

        token_str = "fcm_token_to_logout_123"
        client.post(
            "/api/v1/notifications/devices",
            headers=headers,
            json={"device_token": token_str, "device_type": "android"},
        )

        response = client.delete(f"/api/v1/notifications/devices/{token_str}", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        db_token = db_session.query(DeviceToken).filter(DeviceToken.device_token == token_str).first()
        assert db_token.is_active is False

    def test_list_notifications_and_unread_count(self, client: TestClient, db_session):
        mobile = "+919944000004"
        headers = get_auth_headers(client, mobile)
        user = db_session.query(User).filter(User.mobile_number == normalize_mobile_number(mobile)).first()

        # Dispatch 3 notifications
        FCMService.dispatch_notification(
            db=db_session,
            user_id=user.id,
            title="Scheme Alert: PM-KISAN 17th Installment",
            message="Check your bank account for DBT credit.",
            notification_type="scheme_alert",
        )
        FCMService.dispatch_notification(
            db=db_session,
            user_id=user.id,
            title="Document Reminder",
            message="Income certificate expires in 15 days.",
            notification_type="document_reminder",
        )
        FCMService.dispatch_notification(
            db=db_session,
            user_id=user.id,
            title="Status Update",
            message="Application under review by department.",
            notification_type="status_update",
        )

        # Get list
        response = client.get("/api/v1/notifications?page=1&page_size=10", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["unread_count"] == 3
        assert len(data["notifications"]) == 3

        # Unread count endpoint
        unread_res = client.get("/api/v1/notifications/unread-count", headers=headers)
        assert unread_res.status_code == 200
        assert unread_res.json()["unread_count"] == 3

    def test_mark_single_notification_read_and_idor(self, client: TestClient, db_session):
        mobile = "+919944000005"
        headers = get_auth_headers(client, mobile)
        user = db_session.query(User).filter(User.mobile_number == normalize_mobile_number(mobile)).first()

        notif = FCMService.dispatch_notification(
            db=db_session,
            user_id=user.id,
            title="Test Notice",
            message="Test Message Content",
        )

        # Mark read
        res = client.patch(f"/api/v1/notifications/{notif.id}/read", headers=headers)
        assert res.status_code == 200
        assert res.json()["is_read"] is True

        # Non-existent ID -> 404
        fake_id = uuid.uuid4()
        res_404 = client.patch(f"/api/v1/notifications/{fake_id}/read", headers=headers)
        assert res_404.status_code == 404

    def test_mark_all_read(self, client: TestClient, db_session):
        mobile = "+919944000006"
        headers = get_auth_headers(client, mobile)
        user = db_session.query(User).filter(User.mobile_number == normalize_mobile_number(mobile)).first()

        FCMService.dispatch_notification(
            db=db_session,
            user_id=user.id,
            title="Notice 1",
            message="Body 1",
        )
        FCMService.dispatch_notification(
            db=db_session,
            user_id=user.id,
            title="Notice 2",
            message="Body 2",
        )

        res = client.post("/api/v1/notifications/read-all", headers=headers)
        assert res.status_code == 200
        assert res.json()["marked_read_count"] >= 2

        unread_res = client.get("/api/v1/notifications/unread-count", headers=headers)
        assert unread_res.json()["unread_count"] == 0

    def test_mock_fcm_push_dispatch_and_invalidation(self, client: TestClient, db_session):
        mobile = "+919944000007"
        headers = get_auth_headers(client, mobile)
        user = db_session.query(User).filter(User.mobile_number == normalize_mobile_number(mobile)).first()

        adapter: MockFCMAdapter = FCMService.get_adapter()
        valid_token = "valid_fcm_token_111"
        expired_token = "expired_fcm_token_999"

        FCMService.register_device_token(db_session, user, valid_token)
        FCMService.register_device_token(db_session, user, expired_token)

        # Simulate expired token in adapter
        adapter.invalid_tokens_to_simulate.add(expired_token)

        # Dispatch notification
        notif = FCMService.dispatch_notification(
            db=db_session,
            user_id=user.id,
            title="Biometrics Reminder",
            message="Visit Aadhaar center today.",
            notification_type="document_reminder",
            data={"action": "open_application"},
        )

        assert notif is not None
        # Verify mock captured the push
        assert len(adapter.sent_dispatches) == 1
        dispatch = adapter.sent_dispatches[0]
        assert valid_token in dispatch["tokens"]
        assert expired_token not in dispatch["tokens"]
        assert dispatch["title"] == "Biometrics Reminder"

        # Verify expired token was automatically deactivated in database
        db_expired = db_session.query(DeviceToken).filter(DeviceToken.device_token == expired_token).first()
        assert db_expired.is_active is False
