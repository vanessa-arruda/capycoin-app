import pytest


class TestParentRegistration:
    def test_register_parent_success(self, client, parent_payload):
        response = client.post("/auth/register/parent", json=parent_payload)
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == parent_payload["email"]
        assert data["name"] == parent_payload["name"]
        assert "password" not in data
        assert "password_hash" not in data

    def test_register_parent_duplicate_email(self, client, parent_payload):
        client.post("/auth/register/parent", json=parent_payload)
        response = client.post("/auth/register/parent", json=parent_payload)
        assert response.status_code == 409

    def test_register_parent_missing_fields(self, client):
        response = client.post("/auth/register/parent", json={"email": "x@x.com"})
        assert response.status_code == 422


class TestLogin:
    def test_login_parent_success(self, client, registered_parent, parent_payload):
        response = client.post(
            "/auth/login",
            json={"email": parent_payload["email"], "password": parent_payload["password"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, registered_parent, parent_payload):
        response = client.post(
            "/auth/login",
            json={"email": parent_payload["email"], "password": "wrongpassword"},
        )
        assert response.status_code == 401

    def test_login_unknown_email(self, client):
        response = client.post(
            "/auth/login",
            json={"email": "nobody@nowhere.com", "password": "anything"},
        )
        assert response.status_code == 401

    def test_login_child_success(self, client, registered_child, child_payload):
        response = client.post(
            "/auth/login",
            json={"email": child_payload["email"], "password": child_payload["password"]},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()


class TestProtectedRoutes:
    def test_access_protected_route_without_token(self, client):
        response = client.get("/parents/me")
        assert response.status_code == 401

    def test_access_protected_route_with_invalid_token(self, client):
        response = client.get("/parents/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert response.status_code == 401

    def test_access_protected_route_with_valid_token(self, client, parent_token):
        response = client.get("/parents/me", headers={"Authorization": f"Bearer {parent_token}"})
        assert response.status_code == 200

    def test_child_cannot_access_parent_route(self, client, child_token):
        response = client.get("/parents/me", headers={"Authorization": f"Bearer {child_token}"})
        assert response.status_code == 403
