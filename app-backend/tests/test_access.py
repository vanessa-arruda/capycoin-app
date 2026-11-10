"""Who can call each route. Every route must be listed in ROUTES."""

import uuid
from datetime import date, timedelta
from enum import StrEnum

import pytest

from core import clock
from core.security import hash_token, new_token
from main import app
from models import HouseholdInvitation, Prize, Task
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
    ("GET", "/households/{household_id}/members"): Access.PARENT,
    ("DELETE", "/households/{household_id}/members/{user_id}"): Access.ADMIN,
    ("GET", "/households/{household_id}/invitations"): Access.ADMIN,
    ("POST", "/households/{household_id}/invitations"): Access.ADMIN,
    ("DELETE", "/households/{household_id}/invitations/{invitation_id}"): Access.ADMIN,
    ("POST", "/invitations/accept"): Access.PARENT_ACCOUNT,
    ("GET", "/households/{household_id}/kids"): Access.PARENT,
    ("POST", "/households/{household_id}/kids"): Access.ADMIN,
    ("POST", "/households/{household_id}/kids/email-code"): Access.ADMIN,
    ("GET", "/households/{household_id}/kids/{kid_id}"): Access.PARENT,
    ("PATCH", "/households/{household_id}/kids/{kid_id}"): Access.ADMIN,
    ("DELETE", "/households/{household_id}/kids/{kid_id}"): Access.ADMIN,
    ("GET", "/households/{household_id}/tasks"): Access.PARENT,
    ("POST", "/households/{household_id}/tasks"): Access.PARENT,
    ("GET", "/households/{household_id}/tasks/{task_id}"): Access.PARENT,
    ("PATCH", "/households/{household_id}/tasks/{task_id}"): Access.PARENT,
    ("DELETE", "/households/{household_id}/tasks/{task_id}"): Access.PARENT,
    ("GET", "/households/{household_id}/prizes"): Access.PARENT,
    ("POST", "/households/{household_id}/prizes"): Access.PARENT,
    ("GET", "/households/{household_id}/prizes/{prize_id}"): Access.PARENT,
    ("PATCH", "/households/{household_id}/prizes/{prize_id}"): Access.PARENT,
    ("DELETE", "/households/{household_id}/prizes/{prize_id}"): Access.PARENT,
    ("GET", "/households/{household_id}/kids/{kid_id}/transactions"): Access.PARENT,
    ("POST", "/households/{household_id}/kids/{kid_id}/adjustments"): Access.PARENT,
}

# Valid bodies for routes with record ids where {} is not enough, so requests
# get past validation to the record lookup.
BODIES = {
    ("POST", "/households/{household_id}/kids/{kid_id}/adjustments"): {
        "amount": 1,
        "note": "test",
    },
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


def invite(db, household, email):
    invitation = HouseholdInvitation(
        household_id=household.id,
        email=email,
        token_hash=hash_token(new_token()),
        expires_at=clock.now() + timedelta(days=7),
    )
    db.add(invitation)
    db.commit()
    return invitation


def make_task(db, household):
    task = Task(
        household_id=household.id, title="Dishes", reward=5, starts_on=date.today()
    )
    db.add(task)
    db.commit()
    return task


def make_prize(db, household):
    prize = Prize(household_id=household.id, name="Ice cream", cost=5)
    db.add(prize)
    db.commit()
    return prize


@pytest.fixture
def home(db, make_user, make_household, auth_headers):
    """A household with each kind of caller, and an outsider with their own.

    `ids` fills path placeholders with records of the household; `foreign_ids`
    keeps the household but uses records of the outsider's household.
    """
    admin = make_user(email="admin@example.com")
    parent = make_user(email="parent@example.com")
    kid = make_user(role=UserRole.KID, username="kid", password="x" * 8)
    outsider = make_user(email="outsider@example.com")
    household = make_household(admin, parent, kid)
    other_kid = make_user(role=UserRole.KID, username="other-kid", password="x" * 8)
    other = make_household(outsider, other_kid, name="Other home")
    ids = {
        "household_id": household.id,
        "user_id": parent.id,
        "invitation_id": invite(db, household, "new@example.com").id,
        "kid_id": kid.id,
        "task_id": make_task(db, household).id,
        "prize_id": make_prize(db, household).id,
    }
    foreign_ids = {
        "household_id": household.id,
        "user_id": outsider.id,
        "invitation_id": invite(db, other, "new@example.com").id,
        "kid_id": other_kid.id,
        "task_id": make_task(db, other).id,
        "prize_id": make_prize(db, other).id,
    }
    return {
        "ids": ids,
        "foreign_ids": foreign_ids,
        "headers": {
            "admin": auth_headers(admin),
            "parent": auth_headers(parent),
            "kid": auth_headers(kid),
            "outsider": auth_headers(outsider),
        },
    }


def call(client, method, path, ids, headers=None, json=None):
    return client.request(method, path.format(**ids), headers=headers, json=json)


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
    assert call(client, method, path, home["ids"]).status_code == 401


@pytest.mark.parametrize("method, path", routes(*HOUSEHOLD_LEVELS))
def test_other_household_gets_404(client, home, method, path):
    response = call(client, method, path, home["ids"], home["headers"]["outsider"])

    assert response.status_code == 404
    assert response.json()["detail"] == "Household not found"


@pytest.mark.parametrize("method, path", routes(*HOUSEHOLD_LEVELS))
def test_unknown_household_gets_404(client, home, method, path):
    ids = {**home["ids"], "household_id": uuid.uuid7()}

    response = call(client, method, path, ids, home["headers"]["admin"])

    assert response.status_code == 404


@pytest.mark.parametrize(
    "method, path",
    [route for route in routes(*HOUSEHOLD_LEVELS) if route.values[1].count("{") > 1],
)
def test_record_of_another_household_gets_404(client, home, method, path):
    response = call(
        client,
        method,
        path,
        home["foreign_ids"],
        home["headers"]["admin"],
        json=BODIES.get((method, path), {}),
    )

    assert response.status_code == 404


@pytest.mark.parametrize("method, path", routes(*HOUSEHOLD_LEVELS))
@pytest.mark.parametrize("caller", ["kid", "parent", "admin"])
def test_household_roles(client, home, method, path, caller):
    response = call(client, method, path, home["ids"], home["headers"][caller])

    if caller in ALLOWED[ROUTES[(method, path)]]:
        assert response.status_code not in DENIED
    else:
        assert response.status_code == 403


@pytest.mark.parametrize("method, path", routes(Access.PARENT_ACCOUNT))
def test_kid_account_gets_403(client, home, method, path):
    response = call(client, method, path, home["ids"], home["headers"]["kid"])

    assert response.status_code == 403
