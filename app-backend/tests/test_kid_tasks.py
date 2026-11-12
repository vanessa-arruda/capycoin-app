from datetime import UTC, date, datetime

import pytest

from models import Notification, Task, TaskAssignment, TaskSubmission
from models.enums import NotificationType, Recurrence, ReviewStatus
from tests.factories import count

# Wednesday 11 November 2026, 11:00 in Stockholm.
NOW = datetime(2026, 11, 11, 10, 0, tzinfo=UTC)
TODAY = date(2026, 11, 11)


@pytest.fixture(autouse=True)
def clock_at_now(frozen_clock):
    frozen_clock.current = NOW
    return frozen_clock


@pytest.fixture
def mom(make_user):
    return make_user(email="mom@example.com", display_name="Mom")


@pytest.fixture
def dad(make_user):
    return make_user(email="dad@example.com", display_name="Dad")


@pytest.fixture
def household(mom, dad, make_household):
    return make_household(mom, dad)


@pytest.fixture
def lia(make_kid, household):
    return make_kid(household)


@pytest.fixture
def theo(make_kid, household):
    return make_kid(household, username="theo", display_name="Theo")


@pytest.fixture
def kid_headers(lia, auth_headers):
    return auth_headers(lia)


@pytest.fixture
def url(household):
    return f"/households/{household.id}/me/tasks"


@pytest.fixture
def make_task(db, household, lia):
    def make(kid=None, title="Dishes", **fields):
        fields.setdefault("starts_on", TODAY)
        task = Task(
            household_id=household.id,
            title=title,
            reward=10,
            assignments=[TaskAssignment(kid_id=(kid or lia).id)],
            **fields,
        )
        db.add(task)
        db.commit()
        return task

    return make


def add_submission(db, task, kid, status, period_start=None):
    submission = TaskSubmission(
        task_id=task.id,
        kid_id=kid.id,
        period_start=period_start or task.starts_on,
        status=status,
    )
    db.add(submission)
    db.commit()
    return submission


def titles(client, url, headers):
    response = client.get(url, headers=headers)
    assert response.status_code == 200
    return [task["title"] for task in response.json()]


def test_lists_started_tasks_assigned_to_the_kid(
    client, db, url, kid_headers, make_task, theo
):
    make_task(title="Mine")
    make_task(title="Theo's", kid=theo)
    make_task(title="Later", starts_on=date(2026, 11, 12))
    make_task(title="Archived", archived_at=NOW)

    assert titles(client, url, kid_headers) == ["Mine"]


def test_one_off_task_is_hidden_once_approved(
    client, db, url, kid_headers, make_task, lia
):
    task = make_task()
    add_submission(db, task, lia, ReviewStatus.APPROVED)

    assert titles(client, url, kid_headers) == []


def test_one_off_task_past_due_stays_only_while_pending(
    client, db, url, kid_headers, make_task, lia
):
    due = datetime(2026, 11, 11, 9, 0, tzinfo=UTC)
    make_task(title="Missed", due_at=due)
    waiting = make_task(title="Waiting", due_at=due)
    add_submission(db, waiting, lia, ReviewStatus.PENDING)

    assert titles(client, url, kid_headers) == ["Waiting"]


def test_recurring_task_is_hidden_after_it_stops(client, url, kid_headers, make_task):
    make_task(
        recurrence=Recurrence.DAILY,
        starts_on=date(2026, 11, 1),
        due_at=datetime(2026, 11, 10, 12, 0, tzinfo=UTC),
    )

    assert titles(client, url, kid_headers) == []


@pytest.mark.parametrize(
    "recurrence, start, end",
    [
        (Recurrence.DAILY, date(2026, 11, 11), date(2026, 11, 11)),
        (Recurrence.WEEKLY, date(2026, 11, 9), date(2026, 11, 15)),
        (Recurrence.MONTHLY, date(2026, 11, 1), date(2026, 11, 30)),
        (Recurrence.NONE, date(2026, 11, 3), None),
    ],
)
def test_current_period(client, url, kid_headers, make_task, recurrence, start, end):
    make_task(recurrence=recurrence, starts_on=date(2026, 11, 3))

    [task] = client.get(url, headers=kid_headers).json()

    assert task["period_start"] == start.isoformat()
    assert task["period_end"] == (end.isoformat() if end else None)


def test_days_follow_the_household_timezone(
    client, url, kid_headers, make_task, clock_at_now
):
    # Sunday 23:30 in UTC is already Monday in Stockholm.
    clock_at_now.current = datetime(2026, 11, 15, 23, 30, tzinfo=UTC)
    make_task(recurrence=Recurrence.WEEKLY)

    [task] = client.get(url, headers=kid_headers).json()

    assert task["period_start"] == "2026-11-16"


def test_only_this_period_submission_is_shown(
    client, db, url, kid_headers, make_task, lia
):
    task = make_task(recurrence=Recurrence.DAILY, starts_on=date(2026, 11, 1))
    add_submission(db, task, lia, ReviewStatus.APPROVED, date(2026, 11, 10))

    [item] = client.get(url, headers=kid_headers).json()

    assert item["submission"] is None


def test_sorted_to_do_then_waiting_then_done(
    client, db, url, kid_headers, make_task, lia
):
    done = make_task(title="A done", recurrence=Recurrence.DAILY)
    waiting = make_task(title="B waiting")
    make_task(title="C to do")
    add_submission(db, done, lia, ReviewStatus.APPROVED)
    add_submission(db, waiting, lia, ReviewStatus.PENDING)

    assert titles(client, url, kid_headers) == ["C to do", "B waiting", "A done"]


def test_denied_submission_shows_the_review(
    client, db, url, kid_headers, make_task, lia, mom, auth_headers
):
    task = make_task()
    submission = add_submission(db, task, lia, ReviewStatus.PENDING)
    client.post(
        f"/households/{task.household_id}/task-submissions/{submission.id}/deny",
        json={"note": "Some plates are still dirty"},
        headers=auth_headers(mom),
    )

    [item] = client.get(url, headers=kid_headers).json()

    assert item["submission"]["status"] == "denied"
    assert item["submission"]["review_note"] == "Some plates are still dirty"
    assert item["submission"]["reviewed_by_name"] == "Mom"
    assert item["submission"]["has_photo"] is False


def test_get_task_works_after_it_leaves_the_list(
    client, db, url, kid_headers, make_task, lia
):
    task = make_task()
    add_submission(db, task, lia, ReviewStatus.APPROVED)

    response = client.get(f"{url}/{task.id}", headers=kid_headers)

    assert response.status_code == 200
    assert response.json()["submission"]["status"] == "approved"


@pytest.mark.parametrize("kind", ["other kid", "archived"])
def test_get_task_hides_tasks_the_kid_cannot_do(
    client, url, kid_headers, make_task, theo, kind
):
    if kind == "other kid":
        task = make_task(kid=theo)
    else:
        task = make_task(archived_at=NOW)

    response = client.get(f"{url}/{task.id}", headers=kid_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_submit_creates_a_pending_submission_and_notifies_parents(
    client, db, url, kid_headers, make_task, lia, mom, dad
):
    task = make_task(recurrence=Recurrence.WEEKLY)

    response = client.post(
        f"{url}/{task.id}/submissions",
        data={"note": "  All done  "},
        headers=kid_headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["note"] == "All done"
    assert body["submitted_at"] == "2026-11-11T10:00:00Z"
    submission = db.get(TaskSubmission, body["id"])
    assert submission.period_start == date(2026, 11, 9)
    for parent in (mom, dad):
        assert (
            count(
                db,
                Notification,
                recipient_id=parent.id,
                type=NotificationType.TASK_SUBMITTED,
                task_submission_id=submission.id,
            )
            == 1
        )


def test_submit_without_a_note(client, url, kid_headers, make_task):
    task = make_task()

    response = client.post(f"{url}/{task.id}/submissions", headers=kid_headers)

    assert response.status_code == 201
    assert response.json()["note"] is None


@pytest.mark.parametrize("status", [ReviewStatus.PENDING, ReviewStatus.APPROVED])
def test_submit_twice_in_a_period_gives_409(
    client, db, url, kid_headers, make_task, lia, status
):
    task = make_task(recurrence=Recurrence.DAILY)
    add_submission(db, task, lia, status)

    response = client.post(f"{url}/{task.id}/submissions", headers=kid_headers)

    assert response.status_code == 409


def test_submit_again_after_a_denial(client, db, url, kid_headers, make_task, lia):
    task = make_task()
    add_submission(db, task, lia, ReviewStatus.DENIED)

    response = client.post(f"{url}/{task.id}/submissions", headers=kid_headers)

    assert response.status_code == 201


def test_submit_in_the_next_period(
    client, db, url, kid_headers, make_task, lia, clock_at_now
):
    task = make_task(recurrence=Recurrence.DAILY)
    add_submission(db, task, lia, ReviewStatus.APPROVED)
    clock_at_now.advance(days=1)

    response = client.post(f"{url}/{task.id}/submissions", headers=kid_headers)

    assert response.status_code == 201


def test_one_off_task_counts_submissions_before_starts_on_moved(
    client, db, url, kid_headers, make_task, lia
):
    task = make_task(starts_on=date(2026, 11, 5))
    add_submission(db, task, lia, ReviewStatus.APPROVED, date(2026, 11, 2))

    response = client.post(f"{url}/{task.id}/submissions", headers=kid_headers)

    assert response.status_code == 409


@pytest.mark.parametrize(
    "fields, detail",
    [
        ({"starts_on": date(2026, 11, 12)}, "This task has not started yet"),
        (
            {"due_at": datetime(2026, 11, 11, 9, 0, tzinfo=UTC)},
            "This task is past its due time",
        ),
    ],
)
def test_submit_outside_the_task_dates_gives_409(
    client, url, kid_headers, make_task, fields, detail
):
    task = make_task(**fields)

    response = client.post(f"{url}/{task.id}/submissions", headers=kid_headers)

    assert response.status_code == 409
    assert response.json()["detail"] == detail


def test_submit_note_too_long_gives_422(client, url, kid_headers, make_task):
    task = make_task()

    response = client.post(
        f"{url}/{task.id}/submissions", data={"note": "x" * 501}, headers=kid_headers
    )

    assert response.status_code == 422
