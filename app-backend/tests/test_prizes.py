import pytest

from models import PrizeClaim
from models.enums import UserRole


@pytest.fixture
def mom(make_user):
    return make_user(email="mom@example.com")


@pytest.fixture
def household(mom, make_household):
    return make_household(mom)


@pytest.fixture
def headers(mom, auth_headers):
    return auth_headers(mom)


@pytest.fixture
def url(household):
    return f"/households/{household.id}/prizes"


def create(client, url, headers, **fields):
    return client.post(
        url, headers=headers, json={"name": "Ice cream", "cost": 5, **fields}
    )


class TestCreatePrize:
    def test_creates_a_prize(self, client, url, headers, mom):
        response = create(client, url, headers, name=" Movie night ", description="")

        assert response.status_code == 201
        body = response.json()
        assert (body["name"], body["cost"], body["description"]) == (
            "Movie night",
            5,
            None,
        )
        assert body["created_by"] == str(mom.id)

    @pytest.mark.parametrize("cost", [0, -1, 1_000_001])
    def test_cost_must_be_in_range(self, client, url, headers, cost):
        assert create(client, url, headers, cost=cost).status_code == 422


class TestListPrizes:
    def test_hides_archived_prizes(self, client, url, headers):
        create(client, url, headers, name="Ice cream")
        old = create(client, url, headers, name="Old").json()
        client.delete(f"{url}/{old['id']}", headers=headers)

        active = client.get(url, headers=headers).json()
        archived = client.get(url, headers=headers, params={"archived": "true"}).json()

        assert [p["name"] for p in active["items"]] == ["Ice cream"]
        assert [p["name"] for p in archived["items"]] == ["Old"]


class TestUpdatePrize:
    def test_new_cost_does_not_change_pending_claims(
        self, client, url, headers, db, household, make_user
    ):
        prize = create(client, url, headers, cost=5).json()
        kid = make_user(role=UserRole.KID, username="lia", password="x" * 8)
        claim = PrizeClaim(prize_id=prize["id"], kid_id=kid.id, cost=5)
        db.add(claim)
        db.commit()

        response = client.patch(
            f"{url}/{prize['id']}", headers=headers, json={"cost": 9}
        )

        assert response.json()["cost"] == 9
        db.refresh(claim)
        assert claim.cost == 5

    @pytest.mark.parametrize("field", ["name", "cost"])
    def test_required_fields_cannot_be_null(self, client, url, headers, field):
        prize = create(client, url, headers).json()

        response = client.patch(
            f"{url}/{prize['id']}", headers=headers, json={field: None}
        )

        assert response.status_code == 422

    def test_archived_prize_cannot_be_changed(self, client, url, headers):
        prize = create(client, url, headers).json()
        client.delete(f"{url}/{prize['id']}", headers=headers)

        response = client.patch(
            f"{url}/{prize['id']}", headers=headers, json={"cost": 9}
        )

        assert response.status_code == 409


class TestArchivePrize:
    def test_archives_instead_of_deleting(self, client, url, headers):
        prize = create(client, url, headers).json()

        assert client.delete(f"{url}/{prize['id']}", headers=headers).status_code == 204
        body = client.get(f"{url}/{prize['id']}", headers=headers).json()
        assert body["archived_at"] is not None
