import pytest
from sqlalchemy import select

from models import Notification, NotificationPreference
from models.enums import NotificationChannel, NotificationType
from tests.factories import fill_wallet


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
def lia(make_kid, household):
    return make_kid(household)


@pytest.fixture
def kid_url(household, lia):
    return f"/households/{household.id}/kids/{lia.id}"


def adjust(client, kid_url, headers, amount, note="Helped a lot"):
    return client.post(
        f"{kid_url}/adjustments", headers=headers, json={"amount": amount, "note": note}
    )


class TestAdjustments:
    def test_adds_and_removes_credits(self, client, kid_url, headers, mom):
        added = adjust(client, kid_url, headers, 5)
        adjust(client, kid_url, headers, -8, "Broke a window")

        assert added.status_code == 201
        assert added.json() | {"id": None, "created_at": None} == {
            "id": None,
            "amount": 5,
            "kind": "manual_adjustment",
            "note": "Helped a lot",
            "task_submission_id": None,
            "task_title": None,
            "prize_claim_id": None,
            "prize_name": None,
            "created_by": str(mom.id),
            "created_by_name": mom.display_name,
            "created_at": None,
        }
        kid = client.get(kid_url, headers=headers).json()
        assert kid["balance"] == -3

    @pytest.mark.parametrize(
        "body",
        [{"amount": 0, "note": "x"}, {"amount": 5}, {"amount": 5, "note": " "}],
        ids=["zero", "no note", "blank note"],
    )
    def test_rejects_invalid_adjustments(self, client, kid_url, headers, body):
        response = client.post(f"{kid_url}/adjustments", headers=headers, json=body)

        assert response.status_code == 422

    def test_notifies_the_kid(self, client, kid_url, headers, db, lia):
        entry = adjust(client, kid_url, headers, 5).json()

        notification = db.scalar(
            select(Notification).where(Notification.recipient_id == lia.id)
        )
        assert notification.type == NotificationType.CREDITS_ADJUSTED
        assert str(notification.credit_transaction_id) == entry["id"]

    def test_no_notification_when_turned_off(self, client, kid_url, headers, db, lia):
        db.add(
            NotificationPreference(
                user_id=lia.id,
                type=NotificationType.CREDITS_ADJUSTED,
                channel=NotificationChannel.IN_APP,
                enabled=False,
            )
        )
        db.commit()

        adjust(client, kid_url, headers, 5)

        assert db.scalar(select(Notification)) is None

    def test_a_parent_id_is_not_a_kid(self, client, household, headers, mom):
        response = adjust(
            client, f"/households/{household.id}/kids/{mom.id}", headers, 5
        )

        assert response.status_code == 404


class TestTransactions:
    def test_lists_newest_first_with_task_and_prize_names(
        self, client, db, household, kid_url, headers, mom, lia
    ):
        fill_wallet(db, household, lia, mom)

        body = client.get(f"{kid_url}/transactions", headers=headers).json()

        assert [
            (t["kind"], t["amount"], t["task_title"], t["prize_name"])
            for t in body["items"]
        ] == [
            ("manual_adjustment", 3, None, None),
            ("prize_claim", -4, None, "Ice cream"),
            ("task_reward", 10, "Dishes", None),
        ]
        assert body["next_before"] is None

    def test_only_this_households_credits(
        self, client, db, household, kid_url, headers, lia, make_user, make_household
    ):
        dad = make_user(email="dad@example.com")
        fill_wallet(db, make_household(dad, lia, name="Dad's"), lia, dad)

        body = client.get(f"{kid_url}/transactions", headers=headers).json()

        assert body["items"] == []

    def test_pages(self, client, kid_url, headers):
        for amount in (1, 2, 3):
            adjust(client, kid_url, headers, amount)

        first = client.get(
            f"{kid_url}/transactions", headers=headers, params={"limit": 2}
        ).json()
        second = client.get(
            f"{kid_url}/transactions",
            headers=headers,
            params={"limit": 2, "before": first["next_before"]},
        ).json()

        assert [t["amount"] for t in first["items"] + second["items"]] == [3, 2, 1]
