import uuid
import pytest
from app.models.user import User
from app.models.session import UserSession
from app.core.security import hash_password, hash_token


def test_web_register_sets_httponly_and_csrf_cookies(client, db_session):
    """Test citizen registration sets HttpOnly access & refresh cookies and readable CSRF cookie."""
    unique_email = f"web_reg_{uuid.uuid4().hex[:8]}@example.com"
    unique_mobile = f"+9198{uuid.uuid4().int % 100000000:08d}"
    payload = {
        "email": unique_email,
        "password": "StrongPassword123!",
        "confirm_password": "StrongPassword123!",
        "full_name": "Web Citizen",
        "mobile_number": unique_mobile,
    }

    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert "csrf_token" in data
    assert data["role"] == "citizen"

    # Verify cookies
    cookies = response.cookies
    assert "access_token_cookie" in cookies
    assert "refresh_token_cookie" in cookies
    assert "csrf_token_cookie" in cookies
    assert cookies["csrf_token_cookie"] == data["csrf_token"]


def test_web_login_sets_httponly_and_csrf_cookies(client, db_session):
    """Test user login issues access & refresh cookies and CSRF token."""
    email = f"web_login_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash=hash_password("LoginPass123!"),
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "LoginPass123!",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "admin"
    assert "csrf_token" in data

    cookies = response.cookies
    assert "access_token_cookie" in cookies
    assert "refresh_token_cookie" in cookies
    assert "csrf_token_cookie" in cookies


def test_cookie_authenticated_get_me(client, db_session):
    """Test GET /auth/me succeeds with access_token_cookie without CSRF header."""
    email = f"cookie_get_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash=hash_password("GetPass123!"),
        role="citizen",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "GetPass123!",
    })
    assert login_res.status_code == 200
    access_cookie = login_res.cookies["access_token_cookie"]

    # Safe GET method with cookie
    me_res = client.get(
        "/api/v1/auth/me",
        cookies={"access_token_cookie": access_cookie},
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email


def test_cookie_authenticated_post_rejected_without_csrf(client, db_session):
    """Test mutating POST request with access_token_cookie is rejected (403) when X-CSRF-Token is missing."""
    email = f"csrf_rej_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash=hash_password("CsrfPass123!"),
        role="citizen",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "CsrfPass123!",
    })
    assert login_res.status_code == 200
    access_cookie = login_res.cookies["access_token_cookie"]

    # Mutating request without CSRF header should return 403 Forbidden
    res = client.post(
        "/api/v1/auth/set-credentials",
        cookies={"access_token_cookie": access_cookie},
        json={
            "email": f"updated_{email}",
            "password": "NewPassword123!",
            "confirm_password": "NewPassword123!",
        },
    )
    assert res.status_code == 403
    assert "CSRF validation failed" in res.json()["detail"]


def test_cookie_authenticated_post_succeeds_with_valid_csrf(client, db_session):
    """Test mutating POST request with access_token_cookie succeeds when valid X-CSRF-Token is provided."""
    email = f"csrf_ok_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash=hash_password("CsrfOkPass123!"),
        role="citizen",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "CsrfOkPass123!",
    })
    assert login_res.status_code == 200
    access_cookie = login_res.cookies["access_token_cookie"]
    csrf_token = login_res.cookies["csrf_token_cookie"]

    new_email = f"new_{email}"
    res = client.post(
        "/api/v1/auth/set-credentials",
        cookies={
            "access_token_cookie": access_cookie,
            "csrf_token_cookie": csrf_token,
        },
        headers={"X-CSRF-Token": csrf_token},
        json={
            "email": new_email,
            "password": "NewStrongPass123!",
            "confirm_password": "NewStrongPass123!",
        },
    )
    assert res.status_code == 200
    assert res.json()["email"] == new_email


def test_web_refresh_token_rotation(client, db_session):
    """Test refreshing token rotates refresh token and updates cookies."""
    email = f"refresh_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash=hash_password("RefreshPass123!"),
        role="citizen",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "RefreshPass123!",
    })
    assert login_res.status_code == 200
    old_refresh = login_res.cookies["refresh_token_cookie"]
    csrf_token = login_res.cookies["csrf_token_cookie"]

    refresh_res = client.post(
        "/api/v1/auth/refresh",
        cookies={
            "refresh_token_cookie": old_refresh,
            "csrf_token_cookie": csrf_token,
        },
        headers={"X-CSRF-Token": csrf_token},
        json={},
    )
    assert refresh_res.status_code == 200
    new_data = refresh_res.json()
    assert new_data["refresh_token"] != old_refresh
    assert refresh_res.cookies["refresh_token_cookie"] == new_data["refresh_token"]

    # Verify old session was revoked in database
    old_hash = hash_token(old_refresh)
    old_session = db_session.query(UserSession).filter(UserSession.token_hash == old_hash).first()
    assert old_session is not None
    assert old_session.is_revoked is True


def test_web_logout_clears_cookies_and_revokes_session(client, db_session):
    """Test logout clears session cookies and revokes active session."""
    email = f"logout_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash=hash_password("LogoutPass123!"),
        role="citizen",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "LogoutPass123!",
    })
    assert login_res.status_code == 200
    access_cookie = login_res.cookies["access_token_cookie"]
    refresh_cookie = login_res.cookies["refresh_token_cookie"]
    csrf_token = login_res.cookies["csrf_token_cookie"]

    logout_res = client.post(
        "/api/v1/auth/logout",
        cookies={
            "access_token_cookie": access_cookie,
            "refresh_token_cookie": refresh_cookie,
            "csrf_token_cookie": csrf_token,
        },
        headers={"X-CSRF-Token": csrf_token},
        json={"all_sessions": False},
    )
    assert logout_res.status_code == 200
    assert logout_res.json()["status"] == "success"

    # Verify session revoked in DB
    ref_hash = hash_token(refresh_cookie)
    sess = db_session.query(UserSession).filter(UserSession.token_hash == ref_hash).first()
    assert sess is not None
    assert sess.is_revoked is True


def test_mobile_bearer_token_unaffected(client, db_session):
    """Test mobile Bearer token authentication operates directly without cookies or CSRF header."""
    email = f"mobile_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash=hash_password("MobilePass123!"),
        role="citizen",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    login_res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "MobilePass123!",
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # Native mobile client passes Authorization header with no cookies and no X-CSRF-Token
    headers = {"Authorization": f"Bearer {token}"}
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email


def test_unauthorized_access_rejected(client):
    """Test requests without token or cookie return 401 Unauthorized."""
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
    assert "Authentication required" in res.json()["detail"]
