from sqlalchemy import select

from models import Household, HouseholdMember
from models.enums import UserRole


def delete(client, household_id, headers, confirm_name):
    return client.request(
        "DELETE",
        f"/households/{household_id}",
        headers=headers,
        json={"confirm_name": confirm_name},
    )


class TestCreateHousehold:
    def test_creator_becomes_the_admin(self, client, make_user, auth_headers):
        headers = auth_headers(make_user(email="mom@example.com"))

        response = client.post(
            "/households",
            headers=headers,
            json={"name": " The Capys ", "timezone": "Europe/Stockholm"},
        )

        assert response.status_code == 201
        created = response.json()
        assert created["name"] == "The Capys"
        assert client.get("/me/households", headers=headers).json() == [
            {**created, "is_admin": True}
        ]

    def test_rejects_unknown_timezone(self, client, make_user, auth_headers):
        headers = auth_headers(make_user(email="mom@example.com"))

        response = client.post(
            "/households",
            headers=headers,
            json={"name": "Home", "timezone": "Mars/Base"},
        )

        assert response.status_code == 422


class TestMyHouseholds:
    def test_lists_only_the_callers_households(
        self, client, make_user, make_household, auth_headers
    ):
        mom = make_user(email="mom@example.com")
        dad = make_user(email="dad@example.com")
        make_household(mom, dad, name="Home")
        make_household(dad, name="Cabin")
        make_household(make_user(email="other@example.com"), name="Other")

        body = client.get("/me/households", headers=auth_headers(dad)).json()

        assert [(h["name"], h["is_admin"]) for h in body] == [
            ("Cabin", True),
            ("Home", False),
        ]


class TestGetHousehold:
    def test_kid_member_can_view_it(
        self, client, make_user, make_household, auth_headers
    ):
        kid = make_user(role=UserRole.KID, username="lia", password="x" * 8)
        household = make_household(make_user(email="mom@example.com"), kid)

        response = client.get(f"/households/{household.id}", headers=auth_headers(kid))

        assert response.json() == {
            "id": str(household.id),
            "name": "Home",
            "timezone": "Europe/Stockholm",
        }


class TestUpdateHousehold:
    def test_parent_changes_name_and_timezone(
        self, client, make_user, make_household, auth_headers
    ):
        parent = make_user(email="dad@example.com")
        household = make_household(make_user(email="mom@example.com"), parent)

        response = client.patch(
            f"/households/{household.id}",
            headers=auth_headers(parent),
            json={"name": "Capy Home", "timezone": "America/Sao_Paulo"},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Capy Home"
        assert response.json()["timezone"] == "America/Sao_Paulo"

    def test_fields_cannot_be_null(
        self, client, make_user, make_household, auth_headers
    ):
        admin = make_user(email="mom@example.com")
        household = make_household(admin)

        response = client.patch(
            f"/households/{household.id}",
            headers=auth_headers(admin),
            json={"timezone": None},
        )

        assert response.status_code == 422


class TestDeleteHousehold:
    def test_needs_the_exact_name(
        self, client, make_user, make_household, auth_headers, db
    ):
        admin = make_user(email="mom@example.com")
        household = make_household(admin, name="Home")

        response = delete(client, household.id, auth_headers(admin), "home")

        assert response.status_code == 422
        assert db.get(Household, household.id) is not None

    def test_deletes_the_household_and_memberships(
        self, client, make_user, make_household, auth_headers, db
    ):
        admin = make_user(email="mom@example.com")
        household = make_household(admin, make_user(email="dad@example.com"))
        household_id = household.id
        headers = auth_headers(admin)

        response = delete(client, household_id, headers, "Home")

        assert response.status_code == 204
        db.expire_all()
        assert db.get(Household, household_id) is None
        assert not db.scalars(
            select(HouseholdMember).where(HouseholdMember.household_id == household_id)
        ).all()
        assert (
            client.get(f"/households/{household_id}", headers=headers).status_code
            == 404
        )
