from __future__ import annotations

from fastapi.testclient import TestClient


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
