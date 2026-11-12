import pytest

from models import (
    CreditTransaction,
    HouseholdMember,
    Notification,
    PrizeClaim,
    Task,
    TaskAssignment,
    TaskSubmission,
    User,
)
from tests.factories import count, fill_wallet


@pytest.fixture
def mom(make_user):
    return make_user(email="mom@example.com")


@pytest.fixture
def household(mom, make_household):
    return make_household(mom)


@pytest.fixture
def headers(mom, auth_headers):
    return auth_headers(mom)


class TestCreateKid:
    def test_creates_a_kid_who_can_log_in(self, client, household, headers):
        response = client.post(
            f"/households/{household.id}/kids",
            headers=headers,
            json={"display_name": "Lia", "username": "Lia", "password": "kid-password"},
        )

        assert response.status_code == 201
        assert response.json() | {"id": None} == {
            "id": None,
            "display_name": "Lia",
            "username": "lia",
            "email": None,
            "balance": 0,
            "reserved": 0,
            "available": 0,
        }
        login = client.post(
            "/auth/login", json={"login": "lia", "password": "kid-password"}
        )
        assert login.json()["user"]["role"] == "kid"

    def test_username_taken(self, client, household, headers, make_user):
        make_user(email="someone@example.com", username="lia")

        response = client.post(
            f"/households/{household.id}/kids",
            headers=headers,
            json={"display_name": "Lia", "username": "lia", "password": "kid-password"},
        )

        assert response.status_code == 409

    def test_needs_username_and_password(self, client, household, headers):
        response = client.post(
            f"/households/{household.id}/kids",
            headers=headers,
            json={"display_name": "Lia", "username": "lia"},
        )

        assert response.status_code == 422


class TestKidEmail:
    def send_code(self, client, household, headers, email="lia@example.com"):
        return client.post(
            f"/households/{household.id}/kids/email-code",
            headers=headers,
            json={"email": email},
        )

    def create(self, client, household, headers, **fields):
        return client.post(
            f"/households/{household.id}/kids",
            headers=headers,
            json={"display_name": "Lia", **fields},
        )

    def test_kid_with_a_validated_email_logs_in_with_a_code(
        self, client, outbox, household, headers
    ):
        assert self.send_code(client, household, headers).status_code == 202
        assert outbox.messages[-1].to == "lia@example.com"

        response = self.create(
            client, household, headers, email="Lia@Example.com", code=outbox.last_code()
        )

        assert response.status_code == 201
        assert response.json()["email"] == "lia@example.com"
        assert response.json()["username"] is None
        client.post("/auth/otp/request", json={"email": "lia@example.com"})
        login = client.post(
            "/auth/otp/verify",
            json={"email": "lia@example.com", "code": outbox.last_code()},
        )
        assert login.json()["user"]["role"] == "kid"

    def test_wrong_code_is_422_not_401(self, client, outbox, household, headers):
        self.send_code(client, household, headers)
        wrong = f"{(int(outbox.last_code()) + 1) % 1_000_000:06d}"

        response = self.create(
            client, household, headers, email="lia@example.com", code=wrong
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "Invalid or expired code"

    def test_email_needs_a_code(self, client, household, headers):
        response = self.create(client, household, headers, email="lia@example.com")

        assert response.status_code == 422

    def test_needs_an_email_or_a_username_and_password(
        self, client, household, headers
    ):
        response = self.create(client, household, headers, username="lia")

        assert response.status_code == 422

    def test_email_in_use_is_reported_only_with_a_valid_code(
        self, client, outbox, household, headers, make_user
    ):
        make_user(email="taken@example.com")

        guessed = self.create(
            client, household, headers, email="taken@example.com", code="123456"
        )
        self.send_code(client, household, headers, "taken@example.com")
        proven = self.create(
            client,
            household,
            headers,
            email="taken@example.com",
            code=outbox.last_code(),
        )

        assert guessed.status_code == 422
        assert proven.status_code == 409

    def test_add_and_remove_an_email_later(
        self, client, outbox, household, headers, make_kid
    ):
        lia = make_kid(household)
        url = f"/households/{household.id}/kids/{lia.id}"
        self.send_code(client, household, headers)

        added = client.patch(
            url,
            headers=headers,
            json={"email": "lia@example.com", "code": outbox.last_code()},
        )
        removed = client.patch(url, headers=headers, json={"email": None})

        assert added.json()["email"] == "lia@example.com"
        assert removed.json()["email"] is None

    def test_cannot_remove_the_only_way_to_log_in(
        self, client, outbox, household, headers
    ):
        self.send_code(client, household, headers)
        lia = self.create(
            client, household, headers, email="lia@example.com", code=outbox.last_code()
        ).json()

        response = client.patch(
            f"/households/{household.id}/kids/{lia['id']}",
            headers=headers,
            json={"email": None},
        )

        assert response.status_code == 422


class TestViewKids:
    def test_lists_kids_with_their_balance(
        self, client, db, household, headers, mom, make_kid
    ):
        lia = make_kid(household)
        make_kid(household, username="theo", display_name="Theo")
        fill_wallet(db, household, lia, mom)

        body = client.get(f"/households/{household.id}/kids", headers=headers).json()

        assert [
            (k["display_name"], k["balance"], k["reserved"], k["available"])
            for k in body
        ] == [("Lia", 9, 5, 4), ("Theo", 0, 0, 0)]

    def test_balance_counts_only_this_household(
        self, client, db, household, headers, mom, make_kid, make_user, make_household
    ):
        lia = make_kid(household)
        dad = make_user(email="dad@example.com")
        fill_wallet(db, make_household(dad, lia, name="Dad's"), lia, dad)

        body = client.get(
            f"/households/{household.id}/kids/{lia.id}", headers=headers
        ).json()

        assert (body["balance"], body["reserved"]) == (0, 0)

    def test_a_parent_is_not_a_kid(self, client, household, headers, mom):
        response = client.get(
            f"/households/{household.id}/kids/{mom.id}", headers=headers
        )

        assert response.status_code == 404


class TestUpdateKid:
    def test_changes_name_and_username(self, client, household, headers, make_kid):
        lia = make_kid(household)

        body = client.patch(
            f"/households/{household.id}/kids/{lia.id}",
            headers=headers,
            json={"display_name": "Lia M", "username": "LiaM"},
        ).json()

        assert (body["display_name"], body["username"]) == ("Lia M", "liam")

    def test_new_password_logs_the_kid_out(
        self, client, household, headers, make_kid, auth_headers
    ):
        lia = make_kid(household)
        kid_headers = auth_headers(lia)

        response = client.patch(
            f"/households/{household.id}/kids/{lia.id}",
            headers=headers,
            json={"password": "new-password"},
        )

        assert response.status_code == 200
        assert client.get("/me", headers=kid_headers).status_code == 401
        login = client.post(
            "/auth/login", json={"login": "lia", "password": "new-password"}
        )
        assert login.status_code == 200

    @pytest.mark.parametrize("field", ["display_name", "username", "password"])
    def test_fields_cannot_be_null(self, client, household, headers, make_kid, field):
        lia = make_kid(household)

        response = client.patch(
            f"/households/{household.id}/kids/{lia.id}",
            headers=headers,
            json={field: None},
        )

        assert response.status_code == 422


class TestRemoveKid:
    def test_deletes_the_kid_and_their_data(
        self, client, db, household, headers, mom, make_kid
    ):
        lia = make_kid(household)
        theo = make_kid(household, username="theo", display_name="Theo")
        fill_wallet(db, household, lia, mom)
        fill_wallet(db, household, theo, mom)
        lia_id = lia.id

        response = client.delete(
            f"/households/{household.id}/kids/{lia_id}", headers=headers
        )

        assert response.status_code == 204
        db.expire_all()
        assert db.get(User, lia_id) is None
        for model in (CreditTransaction, PrizeClaim, TaskSubmission, TaskAssignment):
            assert count(db, model, kid_id=lia_id) == 0
            assert count(db, model, kid_id=theo.id) > 0
        # The parent's notification about Lia's submission goes too.
        assert count(db, Notification, recipient_id=mom.id) == 1
        assert count(db, Task) == 2

    def test_keeps_the_account_and_other_household(
        self, client, db, household, headers, mom, make_kid, make_user, make_household
    ):
        lia = make_kid(household)
        dad = make_user(email="dad@example.com")
        dads = make_household(dad, lia, name="Dad's")
        fill_wallet(db, household, lia, mom)
        fill_wallet(db, dads, lia, dad)

        client.delete(f"/households/{household.id}/kids/{lia.id}", headers=headers)

        db.expire_all()
        assert db.get(User, lia.id) is not None
        assert count(db, HouseholdMember, user_id=lia.id) == 1
        assert count(db, CreditTransaction, kid_id=lia.id) == 3
        assert count(db, CreditTransaction, household_id=household.id) == 0
