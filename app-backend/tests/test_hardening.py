import pytest
from sqlalchemy import select

from main import app
from models import RateLimitEvent


def login(client, login, password="wrong-password"):
    return client.post("/auth/login", json={"login": login, "password": password})


class TestLoginRateLimit:
    def test_locks_a_login_after_five_failures(self, client, make_user, frozen_clock):
        make_user(email="mom@example.com", password="right-password")
        make_user(email="dad@example.com", password="right-password")
        for _ in range(5):
            assert login(client, "mom@example.com").status_code == 401

        assert login(client, "mom@example.com", "right-password").status_code == 429
        assert login(client, "dad@example.com", "right-password").status_code == 200
        frozen_clock.advance(minutes=15, seconds=1)
        assert login(client, "mom@example.com", "right-password").status_code == 200

    def test_unknown_logins_are_limited_the_same_way(self, client, frozen_clock):
        for _ in range(5):
            assert login(client, "nobody@example.com").status_code == 401

        assert login(client, "nobody@example.com").status_code == 429

    def test_locks_an_ip_address_trying_many_logins(
        self, client, make_user, frozen_clock
    ):
        make_user(email="mom@example.com", password="right-password")
        for number in range(20):
            assert login(client, f"guess{number}@example.com").status_code == 401

        assert login(client, "mom@example.com", "right-password").status_code == 429

    def test_stores_only_hashes(self, client, db, frozen_clock):
        login(client, "mom@example.com")

        keys = db.scalars(select(RateLimitEvent.key)).all()

        assert len(keys) == 2
        assert not any("mom" in key or "testclient" in key for key in keys)

    def test_old_events_are_deleted(self, client, db, frozen_clock):
        login(client, "mom@example.com")
        frozen_clock.advance(days=1, seconds=1)

        login(client, "dad@example.com")

        assert len(db.scalars(select(RateLimitEvent.key)).all()) == 2


class TestEmailRateLimits:
    def test_code_requests_per_ip_address(self, client, outbox, frozen_clock):
        for number in range(10):
            response = client.post(
                "/auth/otp/request", json={"email": f"kid{number}@example.com"}
            )
            assert response.status_code == 202

        response = client.post("/auth/otp/request", json={"email": "new@example.com"})

        assert response.status_code == 429

    def test_emails_sent_by_a_household(
        self, client, outbox, make_user, make_household, auth_headers, frozen_clock
    ):
        admin = make_user(email="mom@example.com")
        household = make_household(admin)
        headers = auth_headers(admin)
        url = f"/households/{household.id}"
        for number in range(19):
            response = client.post(
                f"{url}/invitations",
                headers=headers,
                json={"email": f"parent{number}@example.com"},
            )
            assert response.status_code == 201
        code = client.post(
            f"{url}/kids/email-code", headers=headers, json={"email": "kid@example.com"}
        )
        assert code.status_code == 202

        response = client.post(
            f"{url}/invitations",
            headers=headers,
            json={"email": "one-more@example.com"},
        )

        assert response.status_code == 429
        assert len(outbox.messages) == 20


class TestHeaders:
    @pytest.mark.parametrize("path", ["/health", "/me", "/households/not-a-uuid"])
    def test_security_headers_on_every_response(self, client, path):
        response = client.get(path)

        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Cache-Control"] == "no-store"
        assert "default-src 'none'" in response.headers["Content-Security-Policy"]

    def test_api_docs_still_load(self, client):
        response = client.get("/docs")

        assert response.status_code == 200
        assert "Content-Security-Policy" not in response.headers

    def test_cors_allows_only_listed_origins(self, client):
        def preflight(origin):
            return client.options(
                "/me",
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "Authorization",
                },
            )

        allowed = preflight("http://localhost:5173")
        other = preflight("https://evil.example")

        assert allowed.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
        assert "Access-Control-Allow-Origin" not in other.headers


SECRET_FIELDS = {"password", "password_hash", "token_hash", "code_hash", "code"}


def _response_schemas(spec):
    for operations in spec["paths"].values():
        for operation in operations.values():
            for response in operation.get("responses", {}).values():
                for content in response.get("content", {}).values():
                    yield content["schema"]


def _properties(schema, spec, seen):
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        if name in seen:
            return
        seen.add(name)
        schema = spec["components"]["schemas"][name]
    for name, value in schema.get("properties", {}).items():
        yield name
        yield from _properties(value, spec, seen)
    for key in ("items", "additionalProperties"):
        if isinstance(schema.get(key), dict):
            yield from _properties(schema[key], spec, seen)
    for key in ("anyOf", "allOf", "oneOf"):
        for part in schema.get(key, []):
            yield from _properties(part, spec, seen)


def test_no_response_includes_secrets():
    spec = app.openapi()
    seen = set()
    names = {
        name
        for schema in _response_schemas(spec)
        for name in _properties(schema, spec, seen)
    }

    assert names, "found no response fields; the schema walk is broken"
    assert names & SECRET_FIELDS == set()
