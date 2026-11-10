import uuid
from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import CreditTransaction, Prize, PrizeClaim
from models.enums import ReviewStatus


@dataclass(frozen=True)
class Balance:
    balance: int = 0
    # Cost of pending prize claims, held until a parent reviews them.
    reserved: int = 0

    @property
    def available(self) -> int:
        return self.balance - self.reserved


def balances(
    db: Session, household_id: uuid.UUID, kid_ids: Iterable[uuid.UUID]
) -> dict[uuid.UUID, Balance]:
    kid_ids = list(kid_ids)
    totals = dict(
        db.execute(
            select(CreditTransaction.kid_id, func.sum(CreditTransaction.amount))
            .where(
                CreditTransaction.household_id == household_id,
                CreditTransaction.kid_id.in_(kid_ids),
            )
            .group_by(CreditTransaction.kid_id)
        ).all()
    )
    reserved = dict(
        db.execute(
            select(PrizeClaim.kid_id, func.sum(PrizeClaim.cost))
            .join(Prize)
            .where(
                Prize.household_id == household_id,
                PrizeClaim.kid_id.in_(kid_ids),
                PrizeClaim.status == ReviewStatus.PENDING,
            )
            .group_by(PrizeClaim.kid_id)
        ).all()
    )
    return {
        kid_id: Balance(totals.get(kid_id, 0), reserved.get(kid_id, 0))
        for kid_id in kid_ids
    }
