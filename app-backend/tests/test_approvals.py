from datetime import date

import pytest
from sqlalchemy import select

from models import (
    CreditTransaction,
    Notification,
    Prize,
    PrizeClaim,
    Task,
    TaskSubmission,
)
from models.enums import CreditTransactionKind, NotificationType


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
def url(household):
    return f"/households/{household.id}"


def submit(db, household, kid, reward=10, title="Dishes"):
    task = Task(
        household_id=household.id, title=title, reward=reward, starts_on=date.today()
    )
    db.add(task)
    db.flush()
    submission = TaskSubmission(
        task_id=task.id, kid_id=kid.id, period_start=date.today()
    )
    db.add(submission)
    db.commit()
    return submission


def claim(db, household, kid, cost=5, name="Ice cream"):
    prize = Prize(household_id=household.id, name=name, cost=cost)
    db.add(prize)
    db.flush()
    prize_claim = PrizeClaim(prize_id=prize.id, kid_id=kid.id, cost=cost)
    db.add(prize_claim)
    db.commit()
    return prize_claim


def give(db, household, kid, amount):
    db.add(
        CreditTransaction(
            household_id=household.id,
            kid_id=kid.id,
            amount=amount,
            kind=CreditTransactionKind.MANUAL_ADJUSTMENT,
        )
    )
    db.commit()


def balance(client, url, headers, kid):
    body = client.get(f"{url}/kids/{kid.id}", headers=headers).json()
    return body["balance"], body["reserved"], body["available"]


def notification_types(db, kid):
    return db.scalars(
        select(Notification.type).where(Notification.recipient_id == kid.id)
    ).all()


class TestSubmissions:
    def test_lists_pending_submissions(self, client, db, household, url, headers, lia):
        submit(db, household, lia, title="Dishes")
        reviewed = submit(db, household, lia, title="Bed")
        client.post(f"{url}/task-submissions/{reviewed.id}/deny", headers=headers)

        pending = client.get(f"{url}/task-submissions", headers=headers).json()
        denied = client.get(
            f"{url}/task-submissions", headers=headers, params={"status": "denied"}
        ).json()

        assert [(s["task_title"], s["kid_display_name"]) for s in pending["items"]] == [
            ("Dishes", "Lia")
        ]
        assert [s["task_title"] for s in denied["items"]] == ["Bed"]

    def test_approval_credits_the_current_reward(
        self, client, db, household, url, headers, lia, mom
    ):
        submission = submit(db, household, lia, reward=10)
        client.patch(
            f"{url}/tasks/{submission.task_id}", headers=headers, json={"reward": 12}
        )

        response = client.post(
            f"{url}/task-submissions/{submission.id}/approve",
            headers=headers,
            json={"note": "Great job"},
        )

        body = response.json()
        assert response.status_code == 200
        assert (body["status"], body["review_note"]) == ("approved", "Great job")
        assert body["reviewed_by"] == str(mom.id)
        assert balance(client, url, headers, lia) == (12, 0, 12)
        assert notification_types(db, lia) == [NotificationType.TASK_APPROVED]

    def test_deny_credits_nothing(self, client, db, household, url, headers, lia):
        submission = submit(db, household, lia)

        response = client.post(
            f"{url}/task-submissions/{submission.id}/deny", headers=headers
        )

        assert response.json()["status"] == "denied"
        assert balance(client, url, headers, lia) == (0, 0, 0)
        assert notification_types(db, lia) == [NotificationType.TASK_DENIED]

    @pytest.mark.parametrize("second", ["approve", "deny"])
    def test_reviewed_once_only(self, client, db, household, url, headers, lia, second):
        submission = submit(db, household, lia, reward=10)
        client.post(f"{url}/task-submissions/{submission.id}/approve", headers=headers)

        response = client.post(
            f"{url}/task-submissions/{submission.id}/{second}", headers=headers
        )

        assert response.status_code == 409
        assert balance(client, url, headers, lia) == (10, 0, 10)

    def test_archived_task_can_still_be_reviewed(
        self, client, db, household, url, headers, lia
    ):
        submission = submit(db, household, lia)
        client.delete(f"{url}/tasks/{submission.task_id}", headers=headers)

        response = client.post(
            f"{url}/task-submissions/{submission.id}/approve", headers=headers
        )

        assert response.status_code == 200


class TestClaims:
    def test_approval_pays_with_the_claimed_cost(
        self, client, db, household, url, headers, lia
    ):
        give(db, household, lia, 10)
        prize_claim = claim(db, household, lia, cost=5)
        client.patch(
            f"{url}/prizes/{prize_claim.prize_id}", headers=headers, json={"cost": 8}
        )
        assert balance(client, url, headers, lia) == (10, 5, 5)

        response = client.post(
            f"{url}/prize-claims/{prize_claim.id}/approve", headers=headers
        )

        assert response.json()["status"] == "approved"
        assert balance(client, url, headers, lia) == (5, 0, 5)
        assert notification_types(db, lia) == [NotificationType.PRIZE_CLAIM_APPROVED]

    def test_not_enough_credits(self, client, db, household, url, headers, lia):
        give(db, household, lia, 4)
        prize_claim = claim(db, household, lia, cost=5)

        response = client.post(
            f"{url}/prize-claims/{prize_claim.id}/approve", headers=headers
        )

        assert response.status_code == 409
        detail = client.get(f"{url}/prize-claims/{prize_claim.id}", headers=headers)
        assert detail.json()["status"] == "pending"
        assert balance(client, url, headers, lia) == (4, 5, -1)

    def test_other_pending_claims_keep_their_credits(
        self, client, db, household, url, headers, lia
    ):
        give(db, household, lia, 10)
        first = claim(db, household, lia, cost=6, name="Movie")
        second = claim(db, household, lia, cost=6, name="Game")

        blocked = client.post(f"{url}/prize-claims/{first.id}/approve", headers=headers)
        client.post(f"{url}/prize-claims/{second.id}/deny", headers=headers)
        approved = client.post(
            f"{url}/prize-claims/{first.id}/approve", headers=headers
        )

        assert blocked.status_code == 409
        assert approved.status_code == 200
        assert balance(client, url, headers, lia) == (4, 0, 4)

    def test_deny_releases_the_reserved_credits(
        self, client, db, household, url, headers, lia
    ):
        give(db, household, lia, 10)
        prize_claim = claim(db, household, lia, cost=5)

        response = client.post(
            f"{url}/prize-claims/{prize_claim.id}/deny",
            headers=headers,
            json={"note": "Not this week"},
        )

        assert response.json()["review_note"] == "Not this week"
        assert balance(client, url, headers, lia) == (10, 0, 10)
        assert notification_types(db, lia) == [NotificationType.PRIZE_CLAIM_DENIED]

    def test_reviewed_once_only(self, client, db, household, url, headers, lia):
        give(db, household, lia, 10)
        prize_claim = claim(db, household, lia, cost=5)
        approve = f"{url}/prize-claims/{prize_claim.id}/approve"
        client.post(approve, headers=headers)

        assert client.post(approve, headers=headers).status_code == 409
        assert balance(client, url, headers, lia) == (5, 0, 5)
