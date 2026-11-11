from datetime import date

import pytest
from sqlalchemy import func, select

from models import NotificationPreference, Task, TaskSubmission
from models.enums import NotificationType
from services import notifications


@pytest.fixture
def mom(make_user):
    return make_user(email="mom@example.com")


@pytest.fixture
def dad(make_user):
    return make_user(email="dad@example.com")


@pytest.fixture
def household(mom, dad, make_household):
    return make_household(mom, dad)


@pytest.fixture
def lia(make_kid, household):
    return make_kid(household)


@pytest.fixture
def mom_headers(mom, auth_headers):
    return auth_headers(mom)


@pytest.fixture
def lia_headers(lia, auth_headers):
    return auth_headers(lia)


def adjust(client, household, kid, headers, amount=5, note="Helped out"):
    return client.post(
        f"/households/{household.id}/kids/{kid.id}/adjustments",
        headers=headers,
        json={"amount": amount, "note": note},
    )


def submitted(db, household, kid, parents):
    """A submission by the kid, with a task_submitted notification per parent."""
    task = Task(
        household_id=household.id, title="Dishes", reward=10, starts_on=date.today()
    )
    db.add(task)
    db.flush()
    submission = TaskSubmission(
        task_id=task.id, kid_id=kid.id, period_start=date.today()
    )
    db.add(submission)
    db.flush()
    for parent in parents:
        notifications.notify(
            db,
            parent.id,
            household.id,
            NotificationType.TASK_SUBMITTED,
            task_submission_id=submission.id,
        )
    db.commit()
    return submission


def listed(client, headers, **params):
    return client.get("/notifications", headers=headers, params=params).json()["items"]


class TestListNotifications:
    def test_kid_sees_what_happened_to_their_credits_and_tasks(
        self, client, db, household, lia, mom, mom_headers, lia_headers
    ):
        submission = submitted(db, household, lia, [])
        adjust(client, household, lia, mom_headers, 5, "Helped out")
        client.post(
            f"/households/{household.id}/task-submissions/{submission.id}/approve",
            headers=mom_headers,
            json={"note": "Shiny plates"},
        )

        items = listed(client, lia_headers)

        assert [i["type"] for i in items] == ["task_approved", "credits_adjusted"]
        assert items[0]["subject"] | {"id": None} == {
            "kind": "task_submission",
            "id": None,
            "kid_id": str(lia.id),
            "kid_display_name": "Lia",
            "title": "Dishes",
            "status": "approved",
            "amount": 10,
            "note": "Shiny plates",
        }
        assert (items[1]["subject"]["amount"], items[1]["subject"]["note"]) == (
            5,
            "Helped out",
        )

    def test_parent_sees_submissions_to_review(
        self, client, db, household, lia, mom, dad, mom_headers
    ):
        submitted(db, household, lia, [mom, dad])

        items = listed(client, mom_headers)

        assert [(i["type"], i["subject"]["kind"]) for i in items] == [
            ("task_submitted", "task_submission")
        ]

    def test_filters_by_household_and_unread(
        self, client, db, household, lia, mom, mom_headers, make_household
    ):
        cabin = make_household(mom, name="Cabin")
        submitted(db, household, lia, [mom])
        submitted(db, household, lia, [mom])
        submitted(db, cabin, lia, [mom])
        first = listed(client, mom_headers)[-1]
        client.post(f"/notifications/{first['id']}/read", headers=mom_headers)

        assert len(listed(client, mom_headers)) == 3
        assert len(listed(client, mom_headers, household_id=str(cabin.id))) == 1
        unread = listed(client, mom_headers, unread="true")
        assert len(unread) == 2

    def test_hides_households_the_user_left(
        self, client, db, household, lia, mom, dad, mom_headers, auth_headers
    ):
        submitted(db, household, lia, [dad])
        dad_headers = auth_headers(dad)
        assert len(listed(client, dad_headers)) == 1

        client.delete(
            f"/households/{household.id}/members/{dad.id}", headers=mom_headers
        )

        assert listed(client, dad_headers) == []


class TestOneNotification:
    def test_only_the_recipient_can_see_or_read_it(
        self, client, db, household, lia, mom, dad, mom_headers, auth_headers
    ):
        submitted(db, household, lia, [mom])
        notification_id = listed(client, mom_headers)[0]["id"]
        url = f"/notifications/{notification_id}"
        dad_headers = auth_headers(dad)

        assert client.get(url, headers=mom_headers).status_code == 200
        assert client.get(url, headers=dad_headers).status_code == 404
        assert client.post(f"{url}/read", headers=dad_headers).status_code == 404
        assert client.get(url, headers=mom_headers).json()["read_at"] is None

    def test_mark_read(self, client, db, household, lia, mom, mom_headers):
        submitted(db, household, lia, [mom])
        url = f"/notifications/{listed(client, mom_headers)[0]['id']}"

        assert client.post(f"{url}/read", headers=mom_headers).status_code == 204
        read_at = client.get(url, headers=mom_headers).json()["read_at"]
        assert read_at is not None
        client.post(f"{url}/read", headers=mom_headers)
        assert client.get(url, headers=mom_headers).json()["read_at"] == read_at

    def test_read_all_in_one_household(
        self, client, db, household, lia, mom, mom_headers, make_household
    ):
        cabin = make_household(mom, name="Cabin")
        submitted(db, household, lia, [mom])
        submitted(db, cabin, lia, [mom])

        response = client.post(
            "/notifications/read-all",
            headers=mom_headers,
            json={"household_id": str(household.id)},
        )

        assert response.status_code == 204
        unread = listed(client, mom_headers, unread="true")
        assert [i["household_id"] for i in unread] == [str(cabin.id)]
        client.post("/notifications/read-all", headers=mom_headers)
        assert listed(client, mom_headers, unread="true") == []


class TestPreferences:
    def test_defaults_depend_on_the_account_type(
        self, client, mom_headers, lia_headers
    ):
        parent = client.get("/me/notification-preferences", headers=mom_headers).json()
        kid = client.get("/me/notification-preferences", headers=lia_headers).json()

        assert {(p["type"], p["channel"], p["enabled"]) for p in parent} == {
            ("task_submitted", "in_app", True),
            ("task_submitted", "email", False),
            ("prize_claimed", "in_app", True),
            ("prize_claimed", "email", False),
        }
        assert {p["type"] for p in kid} == {
            "task_approved",
            "task_denied",
            "prize_claim_approved",
            "prize_claim_denied",
            "credits_adjusted",
        }

    def test_saves_only_changes_from_the_default(self, client, db, lia, lia_headers):
        def put(enabled):
            return client.put(
                "/me/notification-preferences",
                headers=lia_headers,
                json={
                    "preferences": [
                        {
                            "type": "credits_adjusted",
                            "channel": "in_app",
                            "enabled": enabled,
                        }
                    ]
                },
            )

        def stored():
            return db.scalar(
                select(func.count())
                .select_from(NotificationPreference)
                .where(NotificationPreference.user_id == lia.id)
            )

        off = put(False).json()
        assert {
            "type": "credits_adjusted",
            "channel": "in_app",
            "enabled": False,
        } in off
        assert stored() == 1
        put(True)
        assert stored() == 0

    def test_turned_off_type_is_not_created(
        self, client, db, household, lia, mom_headers, lia_headers
    ):
        client.put(
            "/me/notification-preferences",
            headers=lia_headers,
            json={
                "preferences": [
                    {"type": "credits_adjusted", "channel": "in_app", "enabled": False}
                ]
            },
        )

        adjust(client, household, lia, mom_headers)

        assert listed(client, lia_headers) == []

    def test_rejects_types_for_the_other_account_type(self, client, lia_headers):
        response = client.put(
            "/me/notification-preferences",
            headers=lia_headers,
            json={
                "preferences": [
                    {"type": "task_submitted", "channel": "in_app", "enabled": False}
                ]
            },
        )

        assert response.status_code == 422
