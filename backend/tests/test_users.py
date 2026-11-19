import pytest
from app.models.user import User
from app.core.security import create_access_token


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


class TestUserProfileManagement:
    def test_create_and_get_profile(self, client):
        headers = get_auth_headers(client, "9111122222")

        # 1. Profile initially 404
        res_get_404 = client.get("/api/v1/users/me/profile", headers=headers)
        assert res_get_404.status_code == 404

        # 2. Create profile
        profile_payload = {
            "full_name": "Ramesh Kumar",
            "date_of_birth": "1995-05-15",
            "state": "Gujarat",
            "district": "Ahmedabad",
            "residence_type": "urban",
            "annual_family_income": 180000.0,
            "occupation": "Artisan",
            "education_level": "Higher Secondary",
        }
        res_create = client.put(
            "/api/v1/users/me/profile",
            json=profile_payload,
            headers=headers,
        )
        assert res_create.status_code == 200
        data = res_create.json()
        assert data["full_name"] == "Ramesh Kumar"
        assert data["state"] == "Gujarat"
        assert data["residence_type"] == "urban"

        # 3. Get profile
        res_get = client.get("/api/v1/users/me/profile", headers=headers)
        assert res_get.status_code == 200
        assert res_get.json()["district"] == "Ahmedabad"

    def test_patch_profile(self, client):
        headers = get_auth_headers(client, "9222233333")

        # Create
        client.put(
            "/api/v1/users/me/profile",
            json={
                "full_name": "Pooja Sharma",
                "date_of_birth": "1998-08-20",
                "state": "Rajasthan",
                "district": "Jaipur",
                "residence_type": "rural",
            },
            headers=headers,
        )

        # Patch district and income
        res_patch = client.patch(
            "/api/v1/users/me/profile",
            json={"district": "Udaipur", "annual_family_income": 250000.0},
            headers=headers,
        )
        assert res_patch.status_code == 200
        data = res_patch.json()
        assert data["district"] == "Udaipur"
        assert data["full_name"] == "Pooja Sharma"  # preserved
        assert data["annual_family_income"] == 250000.0

    def test_user_data_isolation(self, client):
        """User A must never receive or alter User B's profile."""
        headers_a = get_auth_headers(client, "9333344444")
        headers_b = get_auth_headers(client, "9444455555")

        # User A sets profile
        client.put(
            "/api/v1/users/me/profile",
            json={
                "full_name": "Citizen A",
                "date_of_birth": "1990-01-01",
                "state": "Punjab",
                "district": "Amritsar",
                "residence_type": "rural",
            },
            headers=headers_a,
        )

        # User B queries their profile -> must be 404 (not User A's data)
        res_b = client.get("/api/v1/users/me/profile", headers=headers_b)
        assert res_b.status_code == 404

    def test_delete_profile(self, client):
        headers = get_auth_headers(client, "9555566666")

        client.put(
            "/api/v1/users/me/profile",
            json={
                "full_name": "Anita Verma",
                "date_of_birth": "1992-04-10",
                "state": "Maharashtra",
                "district": "Pune",
                "residence_type": "urban",
            },
            headers=headers,
        )

        # Delete profile
        res_del = client.delete("/api/v1/users/me/profile", headers=headers)
        assert res_del.status_code == 200

        # Query profile -> 404
        assert client.get("/api/v1/users/me/profile", headers=headers).status_code == 404

    def test_account_deletion_request_workflow(self, client):
        headers = get_auth_headers(client, "9666677777")

        res_del_req = client.post(
            "/api/v1/users/me/delete-request",
            json={"reason": "No longer needed"},
            headers=headers,
        )
        assert res_del_req.status_code == 202
        data = res_del_req.json()
        assert data["status"] == "pending"
        assert "scheduled_for" in data
        assert "All active sessions have been revoked" in data["message"]

        # Subsequent requests with same token should be rejected as citizen account is now deactivated
        res_after = client.get("/api/v1/users/me", headers=headers)
        assert res_after.status_code in (401, 403)

