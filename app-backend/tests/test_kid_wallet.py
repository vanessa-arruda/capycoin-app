import pytest
from sqlalchemy.exc import IntegrityError

from core import clock
from models import CreditTransaction, Notification, Prize, PrizeClaim
from models.enums import CreditTransactionKind, NotificationType, ReviewStatus
from tests.factories import count, fill_wallet


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
def headers(lia, auth_headers):
    return auth_headers(lia)


@pytest.fixture
def url(household):
    return f"/households/{household.id}/me"


def give(db, household, kid, amount, created_by=None):
    db.add(
        CreditTransaction(
            household_id=household.id,
            kid_id=kid.id,
            amount=amount,
            kind=CreditTransactionKind.MANUAL_ADJUSTMENT,
            created_by=created_by.id if created_by else None,
        )
    )
    db.commit()


def add_prize(db, household, name="Ice cream", cost=5, **fields):
    prize = Prize(household_id=household.id, name=name, cost=cost, **fields)
    db.add(prize)
    db.commit()
    return prize


def test_wallet(client, db, url, headers, household, lia, mom):
    fill_wallet(db, household, lia, mom)

    response = client.get(f"{url}/wallet", headers=headers)

    assert response.json() == {"balance": 9, "reserved": 5, "available": 4}


def test_transactions_are_the_kid_own_in_this_household(
    client, db, url, headers, household, lia, theo, mom, make_household
):
    give(db, household, lia, 3)
    give(db, household, theo, 7)
    other = make_household(mom, lia, name="Grandma's")
    give(db, other, lia, 11)

    response = client.get(f"{url}/transactions", headers=headers)

    assert [t["amount"] for t in response.json()["items"]] == [3]


def test_transactions_show_the_current_name_of_who_made_them(
    client, db, url, headers, household, lia, mom
):
    give(db, household, lia, 3, created_by=mom)
    give(db, household, lia, 2)
    mom.display_name = "Mommy"
    db.commit()

    items = client.get(f"{url}/transactions", headers=headers).json()["items"]

    assert [t["created_by_name"] for t in items] == [None, "Mommy"]


def test_store_lists_active_prizes_by_cost_then_name(
    client, db, url, headers, household, mom, make_household
):
    add_prize(db, household, "Movie", 20)
    add_prize(db, household, "Sticker", 5)
    add_prize(db, household, "Candy", 5)
    add_prize(db, household, "Old", 1, archived_at=clock.now())
    add_prize(db, make_household(mom, name="Other"), "Elsewhere", 1)

    response = client.get(f"{url}/prizes", headers=headers)

    assert [p["name"] for p in response.json()] == ["Candy", "Sticker", "Movie"]


def test_store_shows_the_kid_pending_claim(
    client, db, url, headers, household, lia, theo
):
    prize = add_prize(db, household)
    give(db, household, lia, 10)
    give(db, household, theo, 10)
    claim = client.post(f"{url}/prizes/{prize.id}/claims", headers=headers).json()
    db.add(PrizeClaim(prize_id=prize.id, kid_id=theo.id, cost=5))
    db.commit()

    [item] = client.get(f"{url}/prizes", headers=headers).json()

    assert item["pending_claim_id"] == claim["id"]


def test_claim_reserves_the_cost_and_notifies_parents(
    client, db, url, headers, household, lia, mom, dad
):
    prize = add_prize(db, household, cost=5)
    give(db, household, lia, 5)

    response = client.post(f"{url}/prizes/{prize.id}/claims", headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["cost"] == 5
    assert body["prize_name"] == "Ice cream"
    wallet = client.get(f"{url}/wallet", headers=headers).json()
    assert wallet == {"balance": 5, "reserved": 5, "available": 0}
    for parent in (mom, dad):
        assert (
            count(
                db,
                Notification,
                recipient_id=parent.id,
                type=NotificationType.PRIZE_CLAIMED,
                prize_claim_id=body["id"],
            )
            == 1
        )


def test_claim_copies_the_cost(client, db, url, headers, household, lia):
    prize = add_prize(db, household, cost=5)
    give(db, household, lia, 10)
    claim_id = client.post(f"{url}/prizes/{prize.id}/claims", headers=headers).json()[
        "id"
    ]
    prize.cost = 8
    db.commit()

    assert db.get(PrizeClaim, claim_id).cost == 5


def test_second_pending_claim_gives_409(client, db, url, headers, household, lia):
    prize = add_prize(db, household)
    give(db, household, lia, 20)
    client.post(f"{url}/prizes/{prize.id}/claims", headers=headers)

    response = client.post(f"{url}/prizes/{prize.id}/claims", headers=headers)

    assert response.status_code == 409
    assert response.json()["detail"] == "You already asked for this prize"


def test_claim_again_after_a_review(client, db, url, headers, household, lia):
    prize = add_prize(db, household)
    give(db, household, lia, 20)
    db.add(
        PrizeClaim(prize_id=prize.id, kid_id=lia.id, cost=5, status=ReviewStatus.DENIED)
    )
    db.commit()

    response = client.post(f"{url}/prizes/{prize.id}/claims", headers=headers)

    assert response.status_code == 201


def test_claim_counts_reserved_credits(client, db, url, headers, household, lia):
    first, second = add_prize(db, household), add_prize(db, household, "Toy")
    give(db, household, lia, 8)
    client.post(f"{url}/prizes/{first.id}/claims", headers=headers)

    response = client.post(f"{url}/prizes/{second.id}/claims", headers=headers)

    assert response.status_code == 409
    assert response.json()["detail"] == "Not enough credits"


def test_archived_prize_gives_404(client, db, url, headers, household, lia):
    prize = add_prize(db, household, archived_at=clock.now())
    give(db, household, lia, 20)

    response = client.post(f"{url}/prizes/{prize.id}/claims", headers=headers)

    assert response.status_code == 404


def test_database_allows_one_pending_claim_per_prize(db, household, lia):
    prize = add_prize(db, household)
    db.add_all(
        [
            PrizeClaim(prize_id=prize.id, kid_id=lia.id, cost=5),
            PrizeClaim(prize_id=prize.id, kid_id=lia.id, cost=5),
        ]
    )

    with pytest.raises(IntegrityError):
        db.flush()


def test_prize_claims_lists_the_kid_own_by_status(
    client, db, url, headers, household, lia, theo
):
    prize = add_prize(db, household)
    db.add_all(
        [
            PrizeClaim(prize_id=prize.id, kid_id=lia.id, cost=5),
            PrizeClaim(
                prize_id=prize.id, kid_id=lia.id, cost=4, status=ReviewStatus.APPROVED
            ),
            PrizeClaim(prize_id=prize.id, kid_id=theo.id, cost=3),
        ]
    )
    db.commit()

    pending = client.get(f"{url}/prize-claims", headers=headers).json()["items"]
    approved = client.get(
        f"{url}/prize-claims", params={"status": "approved"}, headers=headers
    ).json()["items"]

    assert [c["cost"] for c in pending] == [5]
    assert [c["cost"] for c in approved] == [4]
