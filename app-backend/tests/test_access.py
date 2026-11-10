"""Who can call each route. Every route must be listed in ROUTES."""

import uuid
from enum import StrEnum

import pytest

from main import app
from models.enums import UserRole


class Access(StrEnum):
    ANYONE = "anyone"
    LOGGED_IN = "logged in"
    PARENT_ACCOUNT = "parent account"
    MEMBER = "member"
    PARENT = "parent of the household"
    ADMIN = "admin of the household"


ROUTES = {
    ("GET", "/"): Access.ANYONE,
    ("GET", "/health"): Access.ANYONE,
    ("POST", "/auth/otp/request"): Access.ANYONE,
    ("POST", "/auth/otp/verify"): Access.ANYONE,
    ("POST", "/auth/login"): Access.ANYONE,
    ("POST", "/auth/logout"): Access.LOGGED_IN,
    ("GET", "/me"): Access.LOGGED_IN,
    ("PATCH", "/me"): Access.LOGGED_IN,
    ("PUT", "/me/password"): Access.LOGGED_IN,
    ("GET", "/me/households"): Access.LOGGED_IN,
    ("POST", "/households"): Access.PARENT_ACCOUNT,
    ("GET", "/households/{household_id}"): Access.MEMBER,
    ("PATCH", "/households/{household_id}"): Access.PARENT,
    ("DELETE", "/households/{household_id}"): Access.ADMIN,
}

HOUSEHOLD_LEVELS = (Access.MEMBER, Access.PARENT, Access.ADMIN)
ALLOWED = {
    Access.MEMBER: ("kid", "parent", "admin"),
    Access.PARENT: ("parent", "admin"),
    Access.ADMIN: ("admin",),
}
DENIED = {401, 403, 404}


def routes(*levels: Access) -> list:
    return [
        pytest.param(method, path, id=f"{method} {path}")
        for (method, path), access in ROUTES.items()
        if access in levels
    ]


@pytest.fixture
def home(make_user, make_household, auth_headers):
    """A household with each kind of caller, and an outsider with their own."""
    admin = make_user(email="admin@example.com")
    parent = make_user(email="parent@example.com")
    kid = make_user(role=UserRole.KID, username="kid", password="x" * 8)
    outsider = make_user(email="outsider@example.com")
    household = make_household(admin, parent, kid)
    make_household(outsider, name="Other home")
    return {
        "household": household,
        "headers": {
            "admin": auth_headers(admin),
            "parent": auth_headers(parent),
            "kid": auth_headers(kid),
            "outsider": auth_headers(outsider),
        },
    }


def call(client, method, path, household_id=None, headers=None):
    return client.request(
        method, path.format(household_id=household_id), headers=headers
    )


def test_every_route_is_listed():
    served = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
    }

    assert served == set(ROUTES)


@pytest.mark.parametrize(
    "method, path", routes(*(level for level in Access if level != Access.ANYONE))
)
def test_anonymous_gets_401(client, home, method, path):
    assert call(client, method, path, home["household"].id).status_code == 401


@pytest.mark.parametrize("method, path", routes(*HOUSEHOLD_LEVELS))
def test_other_household_gets_404(client, home, method, path):
    response = call(
        client, method, path, home["household"].id, home["headers"]["outsider"]
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Household not found"


@pytest.mark.parametrize("method, path", routes(*HOUSEHOLD_LEVELS))
def test_unknown_household_gets_404(client, home, method, path):
    response = call(client, method, path, uuid.uuid7(), home["headers"]["admin"])

    assert response.status_code == 404


@pytest.mark.parametrize("method, path", routes(*HOUSEHOLD_LEVELS))
@pytest.mark.parametrize("caller", ["kid", "parent", "admin"])
def test_household_roles(client, home, method, path, caller):
    response = call(client, method, path, home["household"].id, home["headers"][caller])

    if caller in ALLOWED[ROUTES[(method, path)]]:
        assert response.status_code not in DENIED
    else:
        assert response.status_code == 403


@pytest.mark.parametrize("method, path", routes(Access.PARENT_ACCOUNT))
def test_kid_account_gets_403(client, home, method, path):
    assert call(client, method, path, headers=home["headers"]["kid"]).status_code == 403
