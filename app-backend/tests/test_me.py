from models.enums import UserRole


def login(client, login, password):
    return client.post("/auth/login", json={"login": login, "password": password})


class TestGetMe:
    def test_returns_the_caller_without_secrets(self, client, make_user, auth_headers):
        user = make_user(email="mom@example.com", display_name="Mom", password="x" * 8)

        body = client.get("/me", headers=auth_headers(user)).json()

        assert body == {
            "id": str(user.id),
            "role": "parent",
            "display_name": "Mom",
            "username": None,
            "email": "mom@example.com",
        }


class TestUpdateMe:
    def test_changes_display_name_and_lowercases_username(
        self, client, make_user, auth_headers
    ):
        headers = auth_headers(make_user(email="mom@example.com"))

        response = client.patch(
            "/me",
            headers=headers,
            json={"display_name": " Mama ", "username": "MamaBear"},
        )

        assert response.status_code == 200
        assert response.json()["display_name"] == "Mama"
        assert response.json()["username"] == "mamabear"

    def test_omitted_fields_are_unchanged(self, client, make_user, auth_headers):
        headers = auth_headers(
            make_user(email="mom@example.com", username="mom", display_name="Mom")
        )

        body = client.patch(
            "/me", headers=headers, json={"display_name": "Mama"}
        ).json()

        assert body["username"] == "mom"

    def test_username_taken_is_a_conflict(self, client, make_user, auth_headers):
        make_user(email="dad@example.com", username="taken")
        headers = auth_headers(make_user(email="mom@example.com"))

        response = client.patch("/me", headers=headers, json={"username": "Taken"})

        assert response.status_code == 409

    def test_rejects_invalid_username(self, client, make_user, auth_headers):
        headers = auth_headers(make_user(email="mom@example.com"))

        response = client.patch("/me", headers=headers, json={"username": "no spaces"})

        assert response.status_code == 422

    def test_kid_without_email_cannot_remove_username(
        self, client, make_user, auth_headers
    ):
        kid = make_user(role=UserRole.KID, username="lia", password="x" * 8)

        response = client.patch(
            "/me", headers=auth_headers(kid), json={"username": None}
        )

        assert response.status_code == 422


class TestChangePassword:
    def test_first_password_needs_no_current_password(
        self, client, make_user, auth_headers
    ):
        headers = auth_headers(make_user(email="mom@example.com"))

        response = client.put(
            "/me/password", headers=headers, json={"new_password": "new-password"}
        )

        assert response.status_code == 204
        assert login(client, "mom@example.com", "new-password").status_code == 200

    def test_changing_needs_the_current_password(self, client, make_user, auth_headers):
        headers = auth_headers(
            make_user(email="mom@example.com", password="old-password")
        )

        missing = client.put(
            "/me/password", headers=headers, json={"new_password": "new-password"}
        )
        wrong = client.put(
            "/me/password",
            headers=headers,
            json={"current_password": "not-it", "new_password": "new-password"},
        )
        right = client.put(
            "/me/password",
            headers=headers,
            json={"current_password": "old-password", "new_password": "new-password"},
        )

        assert (missing.status_code, wrong.status_code) == (422, 422)
        assert right.status_code == 204
        assert login(client, "mom@example.com", "old-password").status_code == 401

    def test_revokes_other_sessions_but_keeps_the_current_one(
        self, client, make_user, auth_headers
    ):
        user = make_user(email="mom@example.com")
        current, other = auth_headers(user), auth_headers(user)

        client.put(
            "/me/password", headers=current, json={"new_password": "new-password"}
        )

        assert client.get("/me", headers=current).status_code == 200
        assert client.get("/me", headers=other).status_code == 401

    def test_rejects_short_password(self, client, make_user, auth_headers):
        headers = auth_headers(make_user(email="mom@example.com"))

        response = client.put(
            "/me/password", headers=headers, json={"new_password": "short"}
        )

        assert response.status_code == 422
