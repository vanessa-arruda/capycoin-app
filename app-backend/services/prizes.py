import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import clock
from core.errors import Conflict, InvalidInput, NotFound
from models import HouseholdMember, Prize
from schemas.common import Page, PageParams
from schemas.prize import PrizeCreate, PrizeResponse, PrizeUpdate
from services.pagination import paginate

PRIZE_NOT_FOUND = "Prize not found"


def list_prizes(
    db: Session, household_id: uuid.UUID, page: PageParams, archived: bool = False
) -> Page[PrizeResponse]:
    query = select(Prize).where(
        Prize.household_id == household_id,
        Prize.archived_at.is_not(None) if archived else Prize.archived_at.is_(None),
    )
    prizes, next_before = paginate(db, query, Prize.id, page)
    return Page(
        items=[PrizeResponse.model_validate(p) for p in prizes],
        next_before=next_before,
    )


def get_prize(db: Session, household_id: uuid.UUID, prize_id: uuid.UUID) -> Prize:
    prize = db.scalar(
        select(Prize).where(Prize.id == prize_id, Prize.household_id == household_id)
    )
    if prize is None:
        raise NotFound(PRIZE_NOT_FOUND)
    return prize


def create_prize(db: Session, parent: HouseholdMember, data: PrizeCreate) -> Prize:
    prize = Prize(
        household_id=parent.household_id,
        created_by=parent.user_id,
        name=data.name,
        description=data.description or None,
        cost=data.cost,
    )
    db.add(prize)
    db.commit()
    return prize


def update_prize(
    db: Session, household_id: uuid.UUID, prize_id: uuid.UUID, changes: PrizeUpdate
) -> Prize:
    prize = get_prize(db, household_id, prize_id)
    if prize.archived_at is not None:
        raise Conflict("Archived prizes cannot be changed")
    values = changes.model_dump(include=changes.model_fields_set)
    for field in ("name", "cost"):
        if field in values and values[field] is None:
            raise InvalidInput(f"{field} cannot be empty")
    if "description" in values:
        values["description"] = values["description"] or None

    # Pending claims keep the cost they were made with.
    for field, value in values.items():
        setattr(prize, field, value)
    db.commit()
    return prize


def archive_prize(db: Session, household_id: uuid.UUID, prize_id: uuid.UUID) -> None:
    prize = get_prize(db, household_id, prize_id)
    if prize.archived_at is None:
        prize.archived_at = clock.now()
        db.commit()
