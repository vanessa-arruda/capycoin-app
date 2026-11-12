from sqlalchemy import select

from core.security import hash_token
from models import User, UserSession
from models.enums import UserRole


def request_code(client, email="mom@example.com"):
    return client.post("/auth/otp/request", json={"email": email})


def verify(client, code, email="mom@example.com", display_name=None):
    body = {"email": email, "code": code}
    if display_name is not None:
        body["display_name"] = display_name
    return client.post("/auth/otp/verify", json=body)


def wrong(code: str) -> str:
    return f"{(int(code) + 1) % 1_000_000:06d}"


class TestRequestCode:
    def test_sends_a_six_digit_code(self, client, outbox):
        response = request_code(client)

        assert response.status_code == 202
        assert outbox.messages[-1].to == "mom@example.com"
        assert len(outbox.last_code()) == 6

    def test_same_response_whether_or_not_the_account_exists(
        self, client, outbox, make_user
    ):
        make_user(email="dad@example.com")

        known = request_code(client, "dad@example.com")
        unknown = request_code(client, "nobody@example.com")

        assert (known.status_code, known.content) == (
            unknown.status_code,
            unknown.content,
        )

    def test_limits_requests_per_email(self, client, outbox, frozen_clock):
        for _ in range(3):
            assert request_code(client).status_code == 202

        assert request_code(client).status_code == 429
        assert request_code(client, "other@example.com").status_code == 202

        frozen_clock.advance(minutes=16)
        assert request_code(client).status_code == 202

    def test_new_code_invalidates_the_previous_one(self, client, outbox):
        request_code(client)
        first = outbox.last_code()
        request_code(client)
        second = outbox.last_code()

        if first != second:
            assert verify(client, first, display_name="Mom").status_code == 401
        assert verify(client, second, display_name="Mom").status_code == 201

    def test_rejects_invalid_email(self, client, outbox):
        assert request_code(client, "not-an-email").status_code == 422


class TestVerifyCode:
    def test_sign_up_creates_a_parent_and_logs_in(self, client, outbox, db):
        request_code(client, "Mom@Example.com")

        response = verify(client, outbox.last_code(), display_name="Mom")

        assert response.status_code == 201
        body = response.json()
        assert body["user"]["role"] == "parent"
        assert body["user"]["email"] == "mom@example.com"
        assert body["user"]["display_name"] == "Mom"
        me = client.get(
            "/me", headers={"Authorization": f"Bearer {body['token']}"}
        ).json()
        assert me["id"] == body["user"]["id"]

    def test_new_email_needs_a_display_name_and_keeps_the_code(
        self, client, outbox, db
    ):
        request_code(client)
        code = outbox.last_code()

        response = verify(client, code)

        assert response.status_code == 422
        assert db.scalar(select(User).where(User.email == "mom@example.com")) is None
        assert verify(client, code, display_name="Mom").status_code == 201

    def test_existing_account_logs_in_without_display_name(
        self, client, outbox, make_user
    ):
        user = make_user(email="mom@example.com", display_name="Mom")
        request_code(client)

        response = verify(client, outbox.last_code(), display_name="Ignored")

        assert response.status_code == 200
        assert response.json()["user"]["id"] == str(user.id)
        assert response.json()["user"]["display_name"] == "Mom"

    def test_kid_with_email_logs_in_with_a_code(self, client, outbox, make_user):
        make_user(role=UserRole.KID, email="lia@example.com")
        request_code(client, "lia@example.com")

        response = verify(client, outbox.last_code(), email="lia@example.com")

        assert response.status_code == 200
        assert response.json()["user"]["role"] == "kid"

    def test_wrong_code_is_rejected(self, client, outbox):
        request_code(client)

        response = verify(client, wrong(outbox.last_code()), display_name="Mom")

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or expired code"

    def test_code_dies_after_five_wrong_attempts(self, client, outbox):
        request_code(client)
        code = outbox.last_code()
        for _ in range(5):
            assert verify(client, wrong(code), display_name="Mom").status_code == 401

        assert verify(client, code, display_name="Mom").status_code == 401

    def test_code_expires_after_ten_minutes(self, client, outbox, frozen_clock):
        request_code(client)
        frozen_clock.advance(minutes=10, seconds=1)

        assert verify(client, outbox.last_code(), display_name="Mom").status_code == 401

    def test_code_works_only_once(self, client, outbox):
        request_code(client)
        code = outbox.last_code()

        assert verify(client, code, display_name="Mom").status_code == 201
        assert verify(client, code).status_code == 401

    def test_email_validation_code_does_not_log_in(
        self, client, outbox, make_user, make_household, auth_headers
    ):
        admin = make_user(email="mom@example.com")
        household = make_household(admin)
        client.post(
            f"/households/{household.id}/kids/email-code",
            headers=auth_headers(admin),
            json={"email": "lia@example.com"},
        )

        response = verify(
            client, outbox.last_code(), email="lia@example.com", display_name="Lia"
        )

        assert response.status_code == 401

    def test_login_code_does_not_validate_an_email(
        self, client, outbox, make_user, make_household, auth_headers
    ):
        admin = make_user(email="mom@example.com")
        household = make_household(admin)
        request_code(client, "lia@example.com")

        response = client.post(
            f"/households/{household.id}/kids",
            headers=auth_headers(admin),
            json={
                "display_name": "Lia",
                "email": "lia@example.com",
                "code": outbox.last_code(),
            },
        )

        assert response.status_code == 422

    def test_code_is_not_stored_in_plain_text(self, client, outbox, db):
        from models import OtpCode

        request_code(client)

        stored = db.scalar(select(OtpCode.code_hash))
        assert outbox.last_code() not in stored


class TestPasswordLogin:
    def test_logs_in_with_email_or_username(self, client, make_user):
        make_user(
            role=UserRole.KID,
            username="lia",
            email="lia@example.com",
            password="s3cret-pass",
        )

        by_email = client.post(
            "/auth/login", json={"login": "LIA@example.com", "password": "s3cret-pass"}
        )
        by_username = client.post(
            "/auth/login", json={"login": "Lia", "password": "s3cret-pass"}
        )

        assert by_email.status_code == 200
        assert by_username.status_code == 200
        assert by_username.json()["user"]["username"] == "lia"

    def test_every_failure_looks_the_same(self, client, make_user):
        make_user(email="mom@example.com", password="right-password")
        make_user(email="dad@example.com")

        responses = [
            client.post("/auth/login", json={"login": login, "password": password})
            for login, password in [
                ("mom@example.com", "wrong-password"),
                ("nobody@example.com", "right-password"),
                ("dad@example.com", "any-password"),
            ]
        ]

        assert {r.status_code for r in responses} == {401}
        assert {r.json()["detail"] for r in responses} == {"Invalid login or password"}


class TestSessions:
    def test_requires_a_token(self, client):
        assert client.get("/me").status_code == 401

    def test_rejects_an_unknown_token(self, client):
        response = client.get("/me", headers={"Authorization": "Bearer made-up"})

        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"

    def test_token_is_stored_hashed(self, client, make_user, db):
        make_user(email="mom@example.com", password="right-password")

        token = client.post(
            "/auth/login",
            json={"login": "mom@example.com", "password": "right-password"},
        ).json()["token"]

        stored = db.scalars(select(UserSession.token_hash)).all()
        assert stored == [hash_token(token)]

    def test_logout_revokes_the_session(self, client, make_user, auth_headers):
        headers = auth_headers(make_user(email="mom@example.com"))

        assert client.post("/auth/logout", headers=headers).status_code == 204
        assert client.get("/me", headers=headers).status_code == 401

    def test_logout_keeps_other_sessions(self, client, make_user, auth_headers):
        user = make_user(email="mom@example.com")
        phone, laptop = auth_headers(user), auth_headers(user)

        client.post("/auth/logout", headers=phone)

        assert client.get("/me", headers=laptop).status_code == 200

    def test_expires_after_seven_idle_days(
        self, client, make_user, auth_headers, frozen_clock
    ):
        headers = auth_headers(make_user(email="mom@example.com"))

        frozen_clock.advance(days=7, seconds=1)

        assert client.get("/me", headers=headers).status_code == 401

    def test_use_extends_the_idle_timeout(
        self, client, make_user, auth_headers, frozen_clock
    ):
        headers = auth_headers(make_user(email="mom@example.com"))

        frozen_clock.advance(days=6)
        assert client.get("/me", headers=headers).status_code == 200
        frozen_clock.advance(days=6)

        assert client.get("/me", headers=headers).status_code == 200

    def test_expires_thirty_days_after_login_even_when_used(
        self, client, make_user, auth_headers, frozen_clock
    ):
        headers = auth_headers(make_user(email="mom@example.com"))
        for _ in range(4):
            frozen_clock.advance(days=6)
            assert client.get("/me", headers=headers).status_code == 200

        frozen_clock.advance(days=6)

        assert client.get("/me", headers=headers).status_code == 401
