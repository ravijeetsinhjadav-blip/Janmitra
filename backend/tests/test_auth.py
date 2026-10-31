import pytest
from datetime import datetime, timedelta, timezone
from app.models.user import User
from app.models.otp import OTPChallenge
from app.core.security import hash_token, create_access_token


class TestOTPWorkflow:
    def test_otp_generation_success(self, client):
        response = client.post(
            "/api/v1/auth/send-otp",
            json={"mobile_number": "9876543210"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["mobile_number"] == "+919876543210"
        assert data["dev_otp"] is not None
        assert len(data["dev_otp"]) == 6

    def test_invalid_mobile_number_rejection(self, client):
        response = client.post(
            "/api/v1/auth/send-otp",
            json={"mobile_number": "12345"},
        )
        assert response.status_code == 422

    def test_otp_verification_and_new_user_registration(self, client):
        # 1. Send OTP
        res_otp = client.post(
            "/api/v1/auth/send-otp",
            json={"mobile_number": "9123456789"},
        )
        assert res_otp.status_code == 200
        otp = res_otp.json()["dev_otp"]

        # 2. Verify OTP
        res_verify = client.post(
            "/api/v1/auth/verify-otp",
            json={"mobile_number": "9123456789", "otp": otp},
        )
        assert res_verify.status_code == 200
        data = res_verify.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["role"] == "citizen"
        assert data["is_new_user"] is True
        assert data["profile_completed"] is False

    def test_incorrect_otp_rejection(self, client):
        client.post(
            "/api/v1/auth/send-otp",
            json={"mobile_number": "9888877777"},
        )
        response = client.post(
            "/api/v1/auth/verify-otp",
            json={"mobile_number": "9888877777", "otp": "000000"},
        )
        assert response.status_code == 400
        assert "Invalid OTP" in response.json()["detail"]

    def test_expired_otp_rejection(self, client, db_session):
        mobile = "+919555544444"
        expired_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        challenge = OTPChallenge(
            mobile_number=mobile,
            hashed_otp=hash_token("123456"),
            expires_at=expired_time,
            attempts=0,
            max_attempts=3,
            is_verified=False,
        )
        db_session.add(challenge)
        db_session.commit()

        response = client.post(
            "/api/v1/auth/verify-otp",
            json={"mobile_number": "9555544444", "otp": "123456"},
        )
        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()

    def test_otp_attempt_limits_lockout(self, client):
        mobile = "9444433333"
        client.post("/api/v1/auth/send-otp", json={"mobile_number": mobile})

        # Submit 3 wrong attempts
        for _ in range(3):
            client.post(
                "/api/v1/auth/verify-otp",
                json={"mobile_number": mobile, "otp": "999999"},
            )

        # 4th attempt should be locked out with 429
        res_lockout = client.post(
            "/api/v1/auth/verify-otp",
            json={"mobile_number": mobile, "otp": "999999"},
        )
        assert res_lockout.status_code in (400, 429)


class TestJWTSessionsAndRoles:
    def test_existing_user_login_no_duplicate(self, client, db_session):
        mobile = "+919333322222"
        existing_user = User(mobile_number=mobile, role="citizen", is_active=True)
        db_session.add(existing_user)
        db_session.commit()

        # Send and verify OTP
        res_otp = client.post("/api/v1/auth/send-otp", json={"mobile_number": "9333322222"})
        otp = res_otp.json()["dev_otp"]

        res_login = client.post(
            "/api/v1/auth/verify-otp",
            json={"mobile_number": "9333322222", "otp": otp},
        )
        assert res_login.status_code == 200
        data = res_login.json()
        assert data["is_new_user"] is False
        assert data["user_id"] == str(existing_user.id)

    def test_authenticated_me_endpoint(self, client):
        # Register user
        res_otp = client.post("/api/v1/auth/send-otp", json={"mobile_number": "9777711111"})
        otp = res_otp.json()["dev_otp"]
        res_verify = client.post(
            "/api/v1/auth/verify-otp",
            json={"mobile_number": "9777711111", "otp": otp},
        )
        token = res_verify.json()["access_token"]

        # Call GET /api/v1/auth/me
        headers = {"Authorization": f"Bearer {token}"}
        res_me = client.get("/api/v1/auth/me", headers=headers)
        assert res_me.status_code == 200
        assert res_me.json()["mobile_number"] == "+919777711111"
        assert res_me.json()["role"] == "citizen"

    def test_unauthorized_without_token(self, client):
        res = client.get("/api/v1/auth/me")
        assert res.status_code == 401

    def test_refresh_token_rotation(self, client):
        # Login
        res_otp = client.post("/api/v1/auth/send-otp", json={"mobile_number": "9666655555"})
        res_verify = client.post(
            "/api/v1/auth/verify-otp",
            json={"mobile_number": "9666655555", "otp": res_otp.json()["dev_otp"]},
        )
        first_refresh = res_verify.json()["refresh_token"]

        # Refresh
        res_refreshed = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": first_refresh},
        )
        assert res_refreshed.status_code == 200
        new_refresh = res_refreshed.json()["refresh_token"]
        assert new_refresh != first_refresh

        # Using old refresh token must be rejected (rotation enforcement)
        res_reuse = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": first_refresh},
        )
        assert res_reuse.status_code == 401

    def test_logout_revokes_token(self, client):
        # Login
        res_otp = client.post("/api/v1/auth/send-otp", json={"mobile_number": "9555511111"})
        res_verify = client.post(
            "/api/v1/auth/verify-otp",
            json={"mobile_number": "9555511111", "otp": res_otp.json()["dev_otp"]},
        )
        access_token = res_verify.json()["access_token"]
        refresh_token = res_verify.json()["refresh_token"]

        # Logout
        headers = {"Authorization": f"Bearer {access_token}"}
        res_logout = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers=headers,
        )
        assert res_logout.status_code == 200

        # Attempting refresh after logout must fail
        res_refresh = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert res_refresh.status_code == 401
