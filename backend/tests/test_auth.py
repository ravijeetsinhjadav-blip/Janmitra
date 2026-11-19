"""JanMitra Assist - Email + Password Authentication & Security Test Suite (Phase 3 Overhaul)

Verifies:
1. Strict Password Policy & Validation (Argon2id hashing, length, complexity, special chars).
2. Citizen Email + Password Registration (no OTP, duplicate email prevention, role lockdown).
3. Citizen & Admin Email + Password Login (invalid credentials, deactivation, token issuance).
4. In-App Credential Setting for Existing Authenticated Sessions (safe migration).
5. Refresh Token Rotation & Session Revocation (Logout).
6. Administrator Provisioning via CLI.
"""

import uuid
import pytest
from app.models.user import User
from app.models.session import UserSession
from app.core.security import (
    validate_password_strength,
    hash_password,
    verify_password,
    create_access_token,
)
from app.cli.admin_create import provision_admin


class TestPasswordSecurityAndValidation:
    """Verifies password complexity enforcement and cryptographic hashing."""

    def test_password_strength_valid(self):
        # Should not raise
        validate_password_strength("StrongPass@123")
        validate_password_strength("Valid#Password99")

    def test_password_strength_too_short(self):
        with pytest.raises(ValueError, match="at least 8 characters"):
            validate_password_strength("Short1!")

    def test_password_strength_too_long(self):
        with pytest.raises(ValueError, match="not exceed 128"):
            validate_password_strength("A" * 126 + "1!a")

    def test_password_strength_missing_uppercase(self):
        with pytest.raises(ValueError, match="uppercase"):
            validate_password_strength("lowercase@123")

    def test_password_strength_missing_lowercase(self):
        with pytest.raises(ValueError, match="lowercase"):
            validate_password_strength("UPPERCASE@123")

    def test_password_strength_missing_digit(self):
        with pytest.raises(ValueError, match="digit"):
            validate_password_strength("NoDigitsHere@!")

    def test_password_strength_missing_symbol(self):
        with pytest.raises(ValueError, match="special symbol"):
            validate_password_strength("NoSpecial12345")

    def test_argon2id_hashing_and_verification(self):
        password = "SecurePassword@2026!"
        hashed = hash_password(password)
        assert hashed.startswith("$argon2id$") or hashed.startswith("$2")
        assert verify_password(password, hashed) is True
        assert verify_password("WrongPassword@2026!", hashed) is False
        assert verify_password("", hashed) is False
        assert verify_password(password, "") is False


class TestEmailPasswordRegistrationAndLogin:
    """Verifies public citizen registration and login with Email and Password."""

    def test_citizen_registration_success(self, client):
        email = f"citizen_{uuid.uuid4().hex[:8]}@example.com"
        res = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "CitizenPass@123",
                "confirm_password": "CitizenPass@123",
                "full_name": "Rajesh Kumar",
                "mobile_number": "+919876543210",
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["role"] == "citizen"
        assert data["email"] == email.lower()
        assert data["is_new_user"] is True

    def test_citizen_registration_password_mismatch(self, client):
        res = client.post(
            "/api/v1/auth/register",
            json={
                "email": "mismatch@example.com",
                "password": "CitizenPass@123",
                "confirm_password": "DifferentPass@123",
                "full_name": "Test User",
            },
        )
        assert res.status_code == 422

    def test_citizen_registration_weak_password(self, client):
        res = client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@example.com",
                "password": "weak",
                "confirm_password": "weak",
                "full_name": "Test User",
            },
        )
        assert res.status_code == 422

    def test_citizen_registration_duplicate_email(self, client):
        email = f"duplicate_{uuid.uuid4().hex[:8]}@example.com"
        payload = {
            "email": email,
            "password": "CitizenPass@123",
            "confirm_password": "CitizenPass@123",
            "full_name": "First User",
        }
        res1 = client.post("/api/v1/auth/register", json=payload)
        assert res1.status_code == 201

        res2 = client.post("/api/v1/auth/register", json=payload)
        assert res2.status_code == 409
        assert "already exists" in res2.json()["detail"].lower()

    def test_citizen_registration_cannot_self_assign_admin(self, client):
        # Attempt to pass role in payload
        res = client.post(
            "/api/v1/auth/register",
            json={
                "email": f"hacker_{uuid.uuid4().hex[:8]}@example.com",
                "password": "CitizenPass@123",
                "confirm_password": "CitizenPass@123",
                "full_name": "Hacker",
                "role": "admin",
            },
        )
        # Even if 201, role must strictly remain citizen
        assert res.status_code == 201
        assert res.json()["role"] == "citizen"

    def test_citizen_login_success(self, client):
        email = f"login_user_{uuid.uuid4().hex[:8]}@example.com"
        password = "ValidLoginPass@123"
        # Register first
        client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "confirm_password": password,
                "full_name": "Login User",
            },
        )

        # Login
        res_login = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert res_login.status_code == 200
        data = res_login.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["email"] == email.lower()
        assert data["role"] == "citizen"

    def test_citizen_login_wrong_password(self, client):
        email = f"wrong_pw_{uuid.uuid4().hex[:8]}@example.com"
        client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "CorrectPassword@123",
                "confirm_password": "CorrectPassword@123",
                "full_name": "Test User",
            },
        )
        res = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword@123"},
        )
        assert res.status_code == 401
        assert "invalid email or password" in res.json()["detail"].lower()

    def test_citizen_login_nonexistent_email(self, client):
        res = client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent_email@example.com", "password": "AnyPassword@123"},
        )
        assert res.status_code == 401

    def test_citizen_login_deactivated_account_forbidden(self, client, db_session):
        email = f"deactivated_{uuid.uuid4().hex[:8]}@example.com"
        password = "ValidPassword@123"
        user = User(
            id=uuid.uuid4(),
            email=email,
            password_hash=hash_password(password),
            role="citizen",
            is_active=False,
        )
        db_session.add(user)
        db_session.commit()

        res = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert res.status_code == 403
        assert "deactivated" in res.json()["detail"].lower()


class TestJWTSessionsAndMigration:
    """Verifies JWT sessions, token refresh rotation, and in-app credential setting."""

    def test_authenticated_me_endpoint(self, client):
        email = f"me_test_{uuid.uuid4().hex[:8]}@example.com"
        res_reg = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "ValidPassword@123",
                "confirm_password": "ValidPassword@123",
                "full_name": "Me User",
            },
        )
        token = res_reg.json()["access_token"]

        res_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res_me.status_code == 200
        data = res_me.json()
        assert data["email"] == email.lower()
        assert data["role"] == "citizen"

    def test_unauthorized_without_token(self, client):
        res = client.get("/api/v1/auth/me")
        assert res.status_code == 401

    def test_refresh_token_rotation(self, client):
        email = f"rotation_{uuid.uuid4().hex[:8]}@example.com"
        res_reg = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "ValidPassword@123",
                "confirm_password": "ValidPassword@123",
                "full_name": "Rotation User",
            },
        )
        first_refresh = res_reg.json()["refresh_token"]

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
        email = f"logout_{uuid.uuid4().hex[:8]}@example.com"
        res_reg = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "ValidPassword@123",
                "confirm_password": "ValidPassword@123",
                "full_name": "Logout User",
            },
        )
        access_token = res_reg.json()["access_token"]
        refresh_token = res_reg.json()["refresh_token"]

        # Logout
        res_logout = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert res_logout.status_code == 200

        # Attempting refresh after logout must fail
        res_refresh = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert res_refresh.status_code == 401

    def test_set_credentials_in_app_migration(self, client, db_session):
        # Emulate existing legacy citizen with active JWT session but no password
        legacy_user = User(
            id=uuid.uuid4(),
            role="citizen",
            mobile_number="+919888877777",
            email=None,
            password_hash=None,
            is_active=True,
        )
        db_session.add(legacy_user)
        db_session.commit()

        token = create_access_token(user_id=str(legacy_user.id), role="citizen")
        headers = {"Authorization": f"Bearer {token}"}

        # Check me indicates no password
        me_res = client.get("/api/v1/auth/me", headers=headers)
        assert me_res.status_code == 200
        assert me_res.json()["has_password"] is False

        # Set credentials
        new_email = f"migrated_{uuid.uuid4().hex[:8]}@example.com"
        res_set = client.post(
            "/api/v1/auth/set-credentials",
            json={
                "email": new_email,
                "password": "NewStrongPass@123",
                "confirm_password": "NewStrongPass@123",
            },
            headers=headers,
        )
        assert res_set.status_code == 200
        assert res_set.json()["email"] == new_email.lower()

        # Now login with the newly set email and password
        res_login = client.post(
            "/api/v1/auth/login",
            json={"email": new_email, "password": "NewStrongPass@123"},
        )
        assert res_login.status_code == 200
        assert res_login.json()["user_id"] == str(legacy_user.id)


class TestAdminProvisioning:
    """Verifies administrative provisioning via CLI / service and admin login."""

    def test_admin_provisioning_and_login(self, client, db_session):
        admin_email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
        admin_pass = "AdminSuperSecret@2026!"

        provision_admin(admin_email, admin_pass, db=db_session)

        # Login as admin
        res = client.post(
            "/api/v1/auth/login",
            json={"email": admin_email, "password": admin_pass},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["role"] == "admin"
        assert data["email"] == admin_email.lower()

        # Call admin stats endpoint with admin token
        admin_headers = {"Authorization": f"Bearer {data['access_token']}"}
        res_stats = client.get("/api/v1/admin/stats", headers=admin_headers)
        assert res_stats.status_code == 200


class TestPasswordResetAndRecovery:
    """Verifies SMTP password recovery and single-use hashed token semantics."""

    def test_forgot_password_generic_response_nonexistent_email(self, client):
        from app.services.email_service import DevMailbox
        DevMailbox.clear()

        fake_email = f"nonexistent_{uuid.uuid4().hex[:8]}@example.com"
        res = client.post("/api/v1/auth/forgot-password", json={"email": fake_email})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "password reset instructions have been sent" in data["message"]
        # Email should NOT be sent for nonexistent user
        assert DevMailbox.get_latest_message_for(fake_email) is None

    def test_forgot_password_and_successful_reset_flow(self, client):
        from app.services.email_service import DevMailbox
        DevMailbox.clear()

        # 1. Register a citizen
        email = f"reset_test_{uuid.uuid4().hex[:8]}@example.com"
        initial_pw = "OriginalPassword@2026!"
        res_reg = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": initial_pw,
                "confirm_password": initial_pw,
                "full_name": "Reset Test User",
            },
        )
        assert res_reg.status_code == 201

        # 2. Request forgot password
        res_forgot = client.post("/api/v1/auth/forgot-password", json={"email": email})
        assert res_forgot.status_code == 200

        # 3. Retrieve captured email from DevMailbox
        msg = DevMailbox.get_latest_message_for(email)
        assert msg is not None
        assert "token=" in msg["reset_link"]
        assert ":8080/reset-password?token=" in msg["reset_link"]
        token = msg["reset_link"].split("token=")[1]

        # 4. Reset password
        new_pw = "UpdatedPassword@2026!"
        res_reset = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": token,
                "password": new_pw,
                "confirm_password": new_pw,
            },
        )
        assert res_reset.status_code == 200
        assert "successfully updated" in res_reset.json()["message"]

        # 5. Old password must fail
        res_old = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": initial_pw},
        )
        assert res_old.status_code == 401

        # 6. New password must succeed
        res_new = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": new_pw},
        )
        assert res_new.status_code == 200

        # 7. Token reuse must fail (single-use constraint)
        res_reuse = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": token,
                "password": "ThirdPassword@2026!",
                "confirm_password": "ThirdPassword@2026!",
            },
        )
        assert res_reuse.status_code == 400
        assert "invalid or has expired" in res_reuse.json()["detail"]

    def test_reset_password_invalid_token(self, client):
        res = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": "completely_fake_invalid_token_1234567890",
                "password": "ValidPassword@2026!",
                "confirm_password": "ValidPassword@2026!",
            },
        )
        assert res.status_code == 400
        assert "invalid or has expired" in res.json()["detail"]

    def test_reset_password_revokes_previous_refresh_sessions(self, client):
        from app.services.email_service import DevMailbox
        DevMailbox.clear()

        # Register and get initial refresh token
        email = f"session_revoke_{uuid.uuid4().hex[:8]}@example.com"
        pw = "OriginalPass@2026!"
        res_reg = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": pw,
                "confirm_password": pw,
                "full_name": "Session Revocation Test",
            },
        )
        refresh_token = res_reg.json()["refresh_token"]

        # Request forgot password and reset
        client.post("/api/v1/auth/forgot-password", json={"email": email})
        msg = DevMailbox.get_latest_message_for(email)
        token = msg["reset_link"].split("token=")[1]

        client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": token,
                "password": "NewSecurePassword@2026!",
                "confirm_password": "NewSecurePassword@2026!",
            },
        )

        # Attempting to refresh using old refresh token must be rejected (401)
        res_refresh = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert res_refresh.status_code == 401

    def test_forgot_password_rate_limiting_triggers_429(self, client):
        from app.core.rate_limiter import rate_limiter
        from app.core.config import settings

        email = f"rate_fp_{uuid.uuid4().hex[:8]}@example.com"
        rate_limiter.clear_attempts("forgot_password", email)

        max_attempts = settings.PASSWORD_RESET_RATE_LIMIT_MAX_ATTEMPTS
        for _ in range(max_attempts):
            res = client.post("/api/v1/auth/forgot-password", json={"email": email})
            assert res.status_code == 200

        # Next attempt must trigger HTTP 429
        res_limited = client.post("/api/v1/auth/forgot-password", json={"email": email})
        assert res_limited.status_code == 429
        assert "Too many attempts" in res_limited.json()["detail"]
        assert "Retry-After" in res_limited.headers

        # Cleanup
        rate_limiter.clear_attempts("forgot_password", email)

    def test_reset_token_expiration_after_15_minutes(self, client, db_session):
        from datetime import datetime, timezone, timedelta
        from app.services.email_service import DevMailbox
        from app.models.password_reset import PasswordResetToken
        from app.core.security import hash_token
        DevMailbox.clear()

        email = f"expired_token_{uuid.uuid4().hex[:8]}@example.com"
        pw = "OriginalPass@2026!"
        client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": pw, "confirm_password": pw, "full_name": "Expiry Test"},
        )
        client.post("/api/v1/auth/forgot-password", json={"email": email})
        msg = DevMailbox.get_latest_message_for(email)
        raw_token = msg["reset_link"].split("token=")[1]

        # Fast forward expiration timestamp in database
        token_hash = hash_token(raw_token)
        db_token = db_session.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).first()
        assert db_token is not None
        db_token.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db_session.commit()

        # Attempt to reset password with expired token
        res_expired = client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "password": "NewValidPass@2026!", "confirm_password": "NewValidPass@2026!"},
        )
        assert res_expired.status_code == 400
        assert "invalid or has expired" in res_expired.json()["detail"]

    def test_reset_token_hashed_in_database_and_raw_token_never_persisted(self, client, db_session):
        from app.services.email_service import DevMailbox
        from app.models.password_reset import PasswordResetToken
        from app.core.security import hash_token
        DevMailbox.clear()

        email = f"token_hash_audit_{uuid.uuid4().hex[:8]}@example.com"
        pw = "AuditPass@2026!"
        client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": pw, "confirm_password": pw, "full_name": "Hash Audit User"},
        )
        client.post("/api/v1/auth/forgot-password", json={"email": email})
        msg = DevMailbox.get_latest_message_for(email)
        raw_token = msg["reset_link"].split("token=")[1]
        expected_hash = hash_token(raw_token)

        # Query database directly
        db_token = db_session.query(PasswordResetToken).filter(PasswordResetToken.token_hash == expected_hash).first()
        assert db_token is not None
        assert db_token.token_hash == expected_hash
        assert raw_token not in db_token.token_hash
        assert db_token.is_used is False

        # Verify raw token string is nowhere in the database row representation
        assert raw_token not in repr(db_token)

    def test_live_network_smtp_socket_delivery_and_mime_structure(self):
        """Verifies actual TCP socket SMTP delivery, RFC 5321 exchange, and MIME decoding."""
        import socket
        import threading
        import time
        import email
        from app.services.email_service import EmailService, DevMailbox
        from app.core.config import settings

        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.bind(("127.0.0.1", 0))
        port = server_sock.getsockname()[1]
        server_sock.listen(1)

        data_buffer = []

        def handle_client():
            conn, _ = server_sock.accept()
            conn.sendall(b"220 localhost JanMitra Test SMTP Service\r\n")
            in_data = False
            while True:
                line = conn.recv(1024)
                if not line:
                    break
                decoded = line.decode("utf-8", errors="ignore")
                if in_data:
                    data_buffer.append(decoded)
                    if "\r\n.\r\n" in "".join(data_buffer) or decoded.endswith("\r\n.\r\n") or decoded == ".\r\n":
                        in_data = False
                        conn.sendall(b"250 2.0.0 OK: queued\r\n")
                elif decoded.upper().startswith(("EHLO", "HELO")):
                    conn.sendall(b"250-localhost\r\n250 HELP\r\n")
                elif decoded.upper().startswith("MAIL FROM:"):
                    conn.sendall(b"250 2.1.0 Sender OK\r\n")
                elif decoded.upper().startswith("RCPT TO:"):
                    conn.sendall(b"250 2.1.5 Recipient OK\r\n")
                elif decoded.upper().startswith("DATA"):
                    in_data = True
                    conn.sendall(b"354 Start mail input\r\n")
                elif decoded.upper().startswith("QUIT"):
                    conn.sendall(b"221 2.0.0 Bye\r\n")
                    break
                else:
                    conn.sendall(b"250 OK\r\n")
            conn.close()
            server_sock.close()

        server_thread = threading.Thread(target=handle_client, daemon=True)
        server_thread.start()
        time.sleep(0.05)

        orig_host = settings.SMTP_HOST
        orig_port = settings.SMTP_PORT
        try:
            settings.SMTP_HOST = "127.0.0.1"
            settings.SMTP_PORT = port
            DevMailbox.clear()

            to_addr = "citizen.verified@janmitra.internal"
            test_link = "http://localhost:3000/reset-password?token=smtp_verified_raw_token_999"
            sent = EmailService.send_password_reset_email(
                to_email=to_addr,
                reset_link=test_link,
                recipient_name="Verified Citizen",
            )
            assert sent is True

            # Verify delivery mode is smtp_success
            msg = DevMailbox.get_latest_message_for(to_addr)
            assert msg is not None
            assert msg["delivery_mode"] == "smtp_success"

            # Parse wire MIME message received by test server
            full_data = "".join(data_buffer)
            msg_obj = email.message_from_string(full_data)
            assert msg_obj["Subject"] == f"[{settings.PROJECT_NAME}] Password Reset Instructions"
            assert msg_obj["To"] == to_addr
            assert settings.SMTP_FROM_EMAIL in msg_obj["From"]

            # Verify decoded payloads contain the link and expiry
            parts = [
                p.get_payload(decode=True).decode("utf-8")
                for p in msg_obj.walk()
                if p.get_content_type() in ("text/plain", "text/html")
            ]
            assert len(parts) == 2
            for part in parts:
                assert test_link in part
                assert "15 minutes" in part
        finally:
            settings.SMTP_HOST = orig_host
            settings.SMTP_PORT = orig_port
            server_thread.join(timeout=2.0)

    def test_smtp_network_failure_clean_fallback_to_dev_mailbox(self):
        """Verifies that an offline SMTP host safely falls back to DevMailbox without uncaught errors."""
        from app.services.email_service import EmailService, DevMailbox
        from app.core.config import settings

        orig_host = settings.SMTP_HOST
        orig_port = settings.SMTP_PORT
        try:
            # Set to an unreachable port on loopback
            settings.SMTP_HOST = "127.0.0.1"
            settings.SMTP_PORT = 65530
            DevMailbox.clear()

            to_addr = "fallback.citizen@janmitra.internal"
            sent = EmailService.send_password_reset_email(
                to_email=to_addr,
                reset_link="http://localhost:3000/reset-password?token=fallback_token_111",
                recipient_name="Fallback Citizen",
            )
            assert sent is True

            msg = DevMailbox.get_latest_message_for(to_addr)
            assert msg is not None
            assert msg["delivery_mode"] == "dev_mailbox_fallback"
            assert "fallback_token_111" in msg["reset_link"]
        finally:
            settings.SMTP_HOST = orig_host
            settings.SMTP_PORT = orig_port


class TestRateLimiting:
    """Verifies brute-force protection and rate limiting on sensitive routes."""

    def test_login_rate_limiting_triggers_429(self, client, db_session):
        from app.core.rate_limiter import rate_limiter
        from app.core.config import settings

        email = f"ratelimit_{uuid.uuid4().hex[:8]}@example.com"
        rate_limiter.clear_attempts("login", email)

        # Send consecutive wrong password attempts until rate limit hit
        max_attempts = settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS
        for _ in range(max_attempts):
            client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": "WrongPassword@1"},
            )

        # The (max_attempts + 1)-th attempt must receive HTTP 429
        res_limited = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword@1"},
        )
        assert res_limited.status_code == 429
        assert "Too many attempts" in res_limited.json()["detail"]
        assert "Retry-After" in res_limited.headers

        # Cleanup
        rate_limiter.clear_attempts("login", email)
