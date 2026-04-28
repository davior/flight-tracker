from __future__ import annotations

from fastapi.testclient import TestClient


def _register_and_login(client: TestClient, email: str, username: str, password: str) -> str:
    """Helper: register a user and return a valid access token."""
    client.post("/auth/register", json={"email": email, "username": username, "password": password})
    resp = client.post("/auth/login", json={"login": username, "password": password})
    return resp.json()["access_token"]


def test_register_creates_user_and_normalizes_credentials(app) -> None:
    with TestClient(app) as client:
        response = client.post(
            "/auth/register",
            json={
                "email": "Pilot@Example.com ",
                "username": " SpotterOne ",
                "password": "password123",
            },
        )

        assert response.status_code == 201
        assert response.json() == {
            "message": "Registration successful. Please check your email to verify your account."
        }

        login_response = client.post(
            "/auth/login",
            json={"login": "spotterone", "password": "password123"},
        )
        assert login_response.status_code == 200
        assert login_response.json()["user"]["email"] == "pilot@example.com"
        assert login_response.json()["user"]["username"] == "spotterone"
        assert login_response.json()["user"]["is_admin"] is False
        assert login_response.json()["user"]["is_active"] is True


def test_login_returns_admin_flags_for_seeded_admin(app) -> None:
    with TestClient(app) as client:
        response = client.post(
            "/auth/login",
            json={"login": "admin@chemtrail-tracker.com", "password": "change-me-admin-password"},
        )

        assert response.status_code == 200
        assert response.json()["user"]["is_admin"] is True
        assert response.json()["user"]["is_active"] is True


def test_register_returns_conflict_for_duplicate_username_case_insensitive(app) -> None:
    with TestClient(app) as client:
        first_response = client.post(
            "/auth/register",
            json={
                "email": "first@example.com",
                "username": "SpotterOne",
                "password": "password123",
            },
        )
        assert first_response.status_code == 201

        duplicate_response = client.post(
            "/auth/register",
            json={
                "email": "second@example.com",
                "username": "spotterone",
                "password": "password123",
            },
        )

        assert duplicate_response.status_code == 409
        assert duplicate_response.json() == {"detail": "This username is already taken"}


# ---------------------------------------------------------------------------
# PATCH /auth/me — profile update
# ---------------------------------------------------------------------------

def test_update_profile_username_success(app) -> None:
    with TestClient(app) as client:
        token = _register_and_login(client, "pilot@example.com", "pilot", "password123")
        response = client.patch(
            "/auth/me",
            json={"username": "newpilot"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["username"] == "newpilot"

        # Verify the change persisted
        me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.json()["username"] == "newpilot"


def test_update_profile_username_taken(app) -> None:
    with TestClient(app) as client:
        _register_and_login(client, "taken@example.com", "takenname", "password123")
        token = _register_and_login(client, "other@example.com", "otheruser", "password123")
        response = client.patch(
            "/auth/me",
            json={"username": "takenname"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 409
        assert "already taken" in response.json()["detail"]


def test_update_profile_username_too_short(app) -> None:
    with TestClient(app) as client:
        token = _register_and_login(client, "pilot@example.com", "pilot", "password123")
        response = client.patch(
            "/auth/me",
            json={"username": "ab"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422


def test_update_profile_password_success(app) -> None:
    with TestClient(app) as client:
        token = _register_and_login(client, "pilot@example.com", "pilot", "oldpass123")
        response = client.patch(
            "/auth/me",
            json={"current_password": "oldpass123", "new_password": "newpass456"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Old password no longer works
        login_old = client.post("/auth/login", json={"login": "pilot", "password": "oldpass123"})
        assert login_old.status_code == 401

        # New password works
        login_new = client.post("/auth/login", json={"login": "pilot", "password": "newpass456"})
        assert login_new.status_code == 200


def test_update_profile_password_wrong_current(app) -> None:
    with TestClient(app) as client:
        token = _register_and_login(client, "pilot@example.com", "pilot", "correctpass")
        response = client.patch(
            "/auth/me",
            json={"current_password": "wrongpass", "new_password": "newpass456"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"]


def test_update_profile_new_password_requires_current_password(app) -> None:
    with TestClient(app) as client:
        token = _register_and_login(client, "pilot@example.com", "pilot", "password123")
        response = client.patch(
            "/auth/me",
            json={"new_password": "newpass456"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422
        assert "current_password" in response.json()["detail"]


def test_update_profile_no_fields_is_noop(app) -> None:
    with TestClient(app) as client:
        token = _register_and_login(client, "pilot@example.com", "pilot", "password123")
        response = client.patch(
            "/auth/me",
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["username"] == "pilot"


def test_update_profile_requires_auth(app) -> None:
    with TestClient(app) as client:
        response = client.patch("/auth/me", json={"username": "hacker"})
        assert response.status_code == 401
