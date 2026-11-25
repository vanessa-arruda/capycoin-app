import pytest

from models import HouseholdMember
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
def kids(db, make_user, household):
    found = []
    for name in ("lia", "theo"):
        kid = make_user(role=UserRole.KID, username=name, password="x" * 8)
        db.add(HouseholdMember(household_id=household.id, user_id=kid.id))
        found.append(kid)
    db.commit()
    return found


@pytest.fixture
def tasks_url(household):
    return f"/households/{household.id}/tasks"


def create(client, url, headers, kid_ids, **fields):
    body = {
        "title": "Dishes",
        "reward": 5,
        "starts_on": "2026-11-10",
        "kid_ids": [str(kid_id) for kid_id in kid_ids],
        **fields,
    }
    return client.post(url, headers=headers, json=body)


class TestCreateTask:
    def test_creates_a_task_for_several_kids(
        self, client, tasks_url, headers, kids, mom
    ):
        lia, theo = kids

        response = create(
            client,
            tasks_url,
            headers,
            [lia.id, theo.id, lia.id],
            recurrence="weekly",
            due_on="2026-12-31",
        )

        assert response.status_code == 201
        body = response.json()
        assert body["kid_ids"] == sorted([str(lia.id), str(theo.id)])
        assert body["recurrence"] == "weekly"
        # 23:59 in Stockholm, UTC+1 in winter.
        assert body["due_at"] == "2026-12-31T22:59:00Z"
        assert body["created_by"] == str(mom.id)
        assert body["archived_at"] is None

    @pytest.mark.parametrize(
        "kid", ["parent", "other household", "unknown"], ids=lambda k: k
    )
    def test_kid_ids_must_be_kids_of_the_household(
        self, client, tasks_url, headers, kids, mom, make_user, make_household, kid
    ):
        if kid == "parent":
            kid_id = mom.id
        elif kid == "other household":
            other = make_user(role=UserRole.KID, username="sam", password="x" * 8)
            make_household(make_user(email="x@example.com"), other)
            kid_id = other.id
        else:
            kid_id = "0190a000-0000-7000-8000-000000000000"

        response = create(client, tasks_url, headers, [kids[0].id, kid_id])

        assert response.status_code == 422

    def test_needs_at_least_one_kid(self, client, tasks_url, headers):
        assert create(client, tasks_url, headers, []).status_code == 422

    def test_due_on_ends_at_23_59_in_the_household_timezone(
        self, client, tasks_url, headers, kids
    ):
        # Summer time: Stockholm is UTC+2.
        response = create(
            client,
            tasks_url,
            headers,
            [kids[0].id],
            starts_on="2026-07-01",
            due_on="2026-07-01",
        )

        assert response.json()["due_at"] == "2026-07-01T21:59:00Z"

    def test_due_on_can_be_the_start_day_but_not_before(
        self, client, tasks_url, headers, kids
    ):
        same_day = create(client, tasks_url, headers, [kids[0].id], due_on="2026-11-10")
        day_before = create(
            client, tasks_url, headers, [kids[0].id], due_on="2026-11-09"
        )

        assert same_day.status_code == 201
        assert day_before.status_code == 422

    def test_reward_must_be_positive(self, client, tasks_url, headers, kids):
        assert (
            create(client, tasks_url, headers, [kids[0].id], reward=0).status_code
            == 422
        )


class TestListTasks:
    def test_filters_by_kid_and_hides_archived(self, client, tasks_url, headers, kids):
        lia, theo = kids
        create(client, tasks_url, headers, [lia.id], title="Lia's")
        create(client, tasks_url, headers, [theo.id], title="Theo's")
        old = create(client, tasks_url, headers, [lia.id], title="Old").json()
        client.delete(f"{tasks_url}/{old['id']}", headers=headers)

        def titles(**params):
            body = client.get(tasks_url, headers=headers, params=params).json()
            return [task["title"] for task in body["items"]]

        assert titles() == ["Theo's", "Lia's"]
        assert titles(kid_id=str(lia.id)) == ["Lia's"]
        assert titles(archived="true") == ["Old"]

    def test_pages_newest_first(self, client, tasks_url, headers, kids):
        for title in ("one", "two", "three"):
            create(client, tasks_url, headers, [kids[0].id], title=title)

        first = client.get(tasks_url, headers=headers, params={"limit": 2}).json()
        second = client.get(
            tasks_url,
            headers=headers,
            params={"limit": 2, "before": first["next_before"]},
        ).json()

        assert [t["title"] for t in first["items"]] == ["three", "two"]
        assert first["next_before"] == first["items"][-1]["id"]
        assert [t["title"] for t in second["items"]] == ["one"]
        assert second["next_before"] is None

    def test_limit_is_capped(self, client, tasks_url, headers):
        response = client.get(tasks_url, headers=headers, params={"limit": 101})

        assert response.status_code == 422


class TestUpdateTask:
    def test_changes_fields_and_replaces_kids(self, client, tasks_url, headers, kids):
        lia, theo = kids
        task = create(
            client, tasks_url, headers, [lia.id], description="Plates too"
        ).json()

        response = client.patch(
            f"{tasks_url}/{task['id']}",
            headers=headers,
            json={"reward": 8, "description": None, "kid_ids": [str(theo.id)]},
        )

        body = response.json()
        assert response.status_code == 200
        assert (body["reward"], body["description"]) == (8, None)
        assert body["kid_ids"] == [str(theo.id)]
        assert body["title"] == "Dishes"

    def test_keeps_kids_that_stay_assigned(self, client, tasks_url, headers, kids):
        lia, theo = kids
        task = create(client, tasks_url, headers, [lia.id]).json()

        body = client.patch(
            f"{tasks_url}/{task['id']}",
            headers=headers,
            json={"kid_ids": [str(lia.id), str(theo.id)]},
        ).json()

        assert body["kid_ids"] == sorted([str(lia.id), str(theo.id)])

    @pytest.mark.parametrize("field", ["title", "reward", "starts_on", "kid_ids"])
    def test_required_fields_cannot_be_null(
        self, client, tasks_url, headers, kids, field
    ):
        task = create(client, tasks_url, headers, [kids[0].id]).json()

        response = client.patch(
            f"{tasks_url}/{task['id']}", headers=headers, json={field: None}
        )

        assert response.status_code == 422

    def test_invalid_change_leaves_the_task_untouched(
        self, client, tasks_url, headers, kids
    ):
        task = create(client, tasks_url, headers, [kids[0].id]).json()
        url = f"{tasks_url}/{task['id']}"

        response = client.patch(
            url,
            headers=headers,
            json={"title": "Changed", "due_on": "2026-11-01"},
        )

        assert response.status_code == 422
        assert client.get(url, headers=headers).json()["title"] == "Dishes"

    def test_sets_and_clears_due_on(self, client, tasks_url, headers, kids):
        task = create(client, tasks_url, headers, [kids[0].id]).json()
        url = f"{tasks_url}/{task['id']}"

        set_ = client.patch(url, headers=headers, json={"due_on": "2026-11-20"})
        cleared = client.patch(url, headers=headers, json={"due_on": None})

        assert set_.json()["due_at"] == "2026-11-20T22:59:00Z"
        assert cleared.json()["due_at"] is None

    def test_starts_on_cannot_move_past_the_due_day(
        self, client, tasks_url, headers, kids
    ):
        task = create(
            client, tasks_url, headers, [kids[0].id], due_on="2026-11-20"
        ).json()

        response = client.patch(
            f"{tasks_url}/{task['id']}",
            headers=headers,
            json={"starts_on": "2026-11-21"},
        )

        assert response.status_code == 422

    def test_archived_task_cannot_be_changed(self, client, tasks_url, headers, kids):
        task = create(client, tasks_url, headers, [kids[0].id]).json()
        url = f"{tasks_url}/{task['id']}"
        client.delete(url, headers=headers)

        response = client.patch(url, headers=headers, json={"reward": 8})

        assert response.status_code == 409


class TestArchiveTask:
    def test_archives_instead_of_deleting(self, client, tasks_url, headers, kids):
        task = create(client, tasks_url, headers, [kids[0].id]).json()
        url = f"{tasks_url}/{task['id']}"

        assert client.delete(url, headers=headers).status_code == 204
        archived_at = client.get(url, headers=headers).json()["archived_at"]
        assert archived_at is not None
        assert client.delete(url, headers=headers).status_code == 204
        assert client.get(url, headers=headers).json()["archived_at"] == archived_at
