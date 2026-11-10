import re

import pytest
from sqlalchemy import select

from models import HouseholdInvitation


def token_in(message) -> str:
    return re.search(r"#token=(\S+)", message.body).group(1)


@pytest.fixture
def mom(make_user):
    return make_user(email="mom@example.com", display_name="Mom")


@pytest.fixture
def family(mom, make_household, auth_headers):
    return make_household(mom, name="The Capys"), auth_headers(mom)


def invite(client, household, headers, email="dad@example.com"):
    return client.post(
        f"/households/{household.id}/invitations",
        headers=headers,
        json={"email": email},
    )


def accept(client, headers, token):
    return client.post("/invitations/accept", headers=headers, json={"token": token})


class TestInvite:
    def test_sends_an_email_with_a_link(self, client, outbox, family):
        household, headers = family

        response = invite(client, household, headers, "Dad@Example.com")

        assert response.status_code == 201
        assert response.json()["email"] == "dad@example.com"
        assert response.json()["status"] == "pending"
        message = outbox.messages[-1]
        assert message.to == "dad@example.com"
        assert "Mom" in message.body and "The Capys" in message.body
        assert "/invitations/accept#token=" in message.body

    def test_token_is_stored_hashed(self, client, outbox, family, db):
        household, headers = family
        invite(client, household, headers)

        stored = db.scalar(select(HouseholdInvitation.token_hash))

        assert token_in(outbox.messages[-1]) not in stored

    def test_one_pending_invitation_per_email(self, client, outbox, family):
        household, headers = family
        invite(client, household, headers)

        assert invite(client, household, headers).status_code == 409

    def test_expired_invitation_can_be_sent_again(
        self, client, outbox, family, mom, auth_headers, frozen_clock
    ):
        household, headers = family
        invite(client, household, headers)
        frozen_clock.advance(days=7, seconds=1)
        headers = auth_headers(mom)

        assert invite(client, household, headers).status_code == 201

    def test_members_cannot_be_invited(self, client, outbox, family):
        household, headers = family

        assert invite(client, household, headers, "mom@example.com").status_code == 409


class TestListAndRevoke:
    def test_lists_only_open_invitations(
        self, client, outbox, family, mom, auth_headers, frozen_clock
    ):
        household, headers = family
        invite(client, household, headers, "old@example.com")
        frozen_clock.advance(days=8)
        headers = auth_headers(mom)
        invite(client, household, headers, "dad@example.com")
        revoked = invite(client, household, headers, "gone@example.com").json()
        client.delete(
            f"/households/{household.id}/invitations/{revoked['id']}", headers=headers
        )

        body = client.get(f"/households/{household.id}/invitations", headers=headers)

        assert [i["email"] for i in body.json()] == ["dad@example.com"]

    def test_revoked_invitation_cannot_be_accepted(
        self, client, outbox, family, make_user, auth_headers
    ):
        household, headers = family
        invitation = invite(client, household, headers).json()
        token = token_in(outbox.messages[-1])
        url = f"/households/{household.id}/invitations/{invitation['id']}"

        assert client.delete(url, headers=headers).status_code == 204
        assert client.delete(url, headers=headers).status_code == 404
        dad = auth_headers(make_user(email="dad@example.com"))
        assert accept(client, dad, token).status_code == 404


class TestAccept:
    def test_new_parent_signs_up_and_joins(self, client, outbox, family):
        household, headers = family
        invite(client, household, headers)
        token = token_in(outbox.messages[-1])
        client.post("/auth/otp/request", json={"email": "dad@example.com"})
        session = client.post(
            "/auth/otp/verify",
            json={
                "email": "dad@example.com",
                "code": outbox.last_code(),
                "display_name": "Dad",
            },
        ).json()
        dad = {"Authorization": f"Bearer {session['token']}"}

        response = accept(client, dad, token)

        assert response.status_code == 200
        assert response.json()["id"] == str(household.id)
        mine = client.get("/me/households", headers=dad).json()
        assert [(h["name"], h["is_admin"]) for h in mine] == [("The Capys", False)]
        assert (
            client.get(
                f"/households/{household.id}/invitations", headers=headers
            ).json()
            == []
        )

    def test_only_the_invited_email_can_accept(
        self, client, outbox, family, make_user, auth_headers
    ):
        household, headers = family
        invite(client, household, headers)
        someone_else = auth_headers(make_user(email="eve@example.com"))

        response = accept(client, someone_else, token_in(outbox.messages[-1]))

        assert response.status_code == 403

    def test_works_once(self, client, outbox, family, make_user, auth_headers):
        household, headers = family
        invite(client, household, headers)
        token = token_in(outbox.messages[-1])
        dad = auth_headers(make_user(email="dad@example.com"))

        assert accept(client, dad, token).status_code == 200
        assert accept(client, dad, token).status_code == 404

    def test_expires_after_seven_days(
        self, client, outbox, family, make_user, auth_headers, frozen_clock
    ):
        household, headers = family
        invite(client, household, headers)
        frozen_clock.advance(days=7, seconds=1)
        dad = auth_headers(make_user(email="dad@example.com"))

        assert accept(client, dad, token_in(outbox.messages[-1])).status_code == 404

    def test_unknown_token(self, client, make_user, auth_headers):
        dad = auth_headers(make_user(email="dad@example.com"))

        assert accept(client, dad, "made-up").status_code == 404
