import uuid

from fastapi import status

from api.deps import Db, Pagination, ParentMembership, household_router
from schemas.common import Page
from schemas.prize import PrizeCreate, PrizeResponse, PrizeUpdate
from services import prizes

router = household_router("/prizes", tags=["prizes"])


@router.get("")
def list_prizes(
    membership: ParentMembership, db: Db, page: Pagination, archived: bool = False
) -> Page[PrizeResponse]:
    return prizes.list_prizes(db, membership.household_id, page, archived)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_prize(
    data: PrizeCreate, membership: ParentMembership, db: Db
) -> PrizeResponse:
    return PrizeResponse.model_validate(prizes.create_prize(db, membership, data))


@router.get("/{prize_id}")
def get_prize(
    prize_id: uuid.UUID, membership: ParentMembership, db: Db
) -> PrizeResponse:
    return PrizeResponse.model_validate(
        prizes.get_prize(db, membership.household_id, prize_id)
    )


@router.patch("/{prize_id}")
def update_prize(
    prize_id: uuid.UUID, changes: PrizeUpdate, membership: ParentMembership, db: Db
) -> PrizeResponse:
    return PrizeResponse.model_validate(
        prizes.update_prize(db, membership.household_id, prize_id, changes)
    )


@router.delete("/{prize_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_prize(prize_id: uuid.UUID, membership: ParentMembership, db: Db) -> None:
    prizes.archive_prize(db, membership.household_id, prize_id)
