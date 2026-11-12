"""The kid's side of the wallet: balance, history, the store and prize claims."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import clock
from core.errors import Conflict, NotFound
from models import HouseholdMember, Prize, PrizeClaim
from models.enums import NotificationType, ReviewStatus
from schemas.prize import StorePrizeResponse
from schemas.wallet import WalletResponse
from services import notifications, wallet
from services.prizes import PRIZE_NOT_FOUND


def get_wallet(db: Session, kid: HouseholdMember) -> WalletResponse:
    found = wallet.balances(db, kid.household_id, [kid.user_id])[kid.user_id]
    return WalletResponse(
        balance=found.balance, reserved=found.reserved, available=found.available
    )


def list_prizes(db: Session, kid: HouseholdMember) -> list[StorePrizeResponse]:
    prizes = db.scalars(
        select(Prize)
        .where(Prize.household_id == kid.household_id, Prize.archived_at.is_(None))
        .order_by(Prize.cost, Prize.name, Prize.id)
    ).all()
    pending = dict(
        db.execute(
            select(PrizeClaim.prize_id, PrizeClaim.id).where(
                PrizeClaim.kid_id == kid.user_id,
                PrizeClaim.status == ReviewStatus.PENDING,
                PrizeClaim.prize_id.in_([p.id for p in prizes]),
            )
        ).all()
    )
    return [
        StorePrizeResponse(
            id=prize.id,
            name=prize.name,
            description=prize.description,
            cost=prize.cost,
            pending_claim_id=pending.get(prize.id),
        )
        for prize in prizes
    ]


def claim_prize(db: Session, kid: HouseholdMember, prize_id: uuid.UUID) -> PrizeClaim:
    wallet.lock_kid(db, kid.household_id, kid.user_id)
    prize = db.scalar(
        select(Prize).where(
            Prize.id == prize_id,
            Prize.household_id == kid.household_id,
            Prize.archived_at.is_(None),
        )
    )
    if prize is None:
        db.rollback()
        raise NotFound(PRIZE_NOT_FOUND)
    pending = db.scalar(
        select(PrizeClaim.id).where(
            PrizeClaim.prize_id == prize.id,
            PrizeClaim.kid_id == kid.user_id,
            PrizeClaim.status == ReviewStatus.PENDING,
        )
    )
    if pending is not None:
        db.rollback()
        raise Conflict("You already asked for this prize")
    if get_wallet(db, kid).available < prize.cost:
        db.rollback()
        raise Conflict("Not enough credits")

    claim = PrizeClaim(
        prize_id=prize.id,
        kid_id=kid.user_id,
        cost=prize.cost,
        requested_at=clock.now(),
    )
    db.add(claim)
    db.flush()
    notifications.notify_parents(
        db, kid.household_id, NotificationType.PRIZE_CLAIMED, prize_claim_id=claim.id
    )
    db.commit()
    return claim
