import uuid
from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from core.errors import InvalidInput
from models import (
    CreditTransaction,
    HouseholdMember,
    Prize,
    PrizeClaim,
    TaskSubmission,
)
from models.enums import CreditTransactionKind, NotificationType, ReviewStatus
from schemas.common import Page, PageParams
from schemas.wallet import TransactionResponse
from services import notifications
from services.pagination import paginate


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


def lock_kid(db: Session, household_id: uuid.UUID, kid_id: uuid.UUID) -> None:
    """Lock the kid's membership row until commit.

    Every change to a kid's credits or reserved credits takes this lock first,
    so two requests cannot spend the same credits.
    """
    db.execute(
        select(HouseholdMember.user_id)
        .where(
            HouseholdMember.household_id == household_id,
            HouseholdMember.user_id == kid_id,
        )
        .with_for_update()
    )


def transaction_response(entry: CreditTransaction) -> TransactionResponse:
    submission, claim = entry.task_submission, entry.prize_claim
    return TransactionResponse(
        id=entry.id,
        amount=entry.amount,
        kind=entry.kind,
        note=entry.note,
        task_submission_id=entry.task_submission_id,
        task_title=submission.task.title if submission else None,
        prize_claim_id=entry.prize_claim_id,
        prize_name=claim.prize.name if claim else None,
        created_by=entry.created_by,
        created_by_name=entry.creator.display_name if entry.creator else None,
        created_at=entry.created_at,
    )


def list_transactions(
    db: Session, household_id: uuid.UUID, kid_id: uuid.UUID, page: PageParams
) -> Page[TransactionResponse]:
    query = (
        select(CreditTransaction)
        .where(
            CreditTransaction.household_id == household_id,
            CreditTransaction.kid_id == kid_id,
        )
        .options(
            joinedload(CreditTransaction.task_submission).joinedload(
                TaskSubmission.task
            ),
            joinedload(CreditTransaction.prize_claim).joinedload(PrizeClaim.prize),
            joinedload(CreditTransaction.creator),
        )
    )
    entries, next_before = paginate(db, query, CreditTransaction.id, page)
    return Page(
        items=[transaction_response(e) for e in entries], next_before=next_before
    )


def adjust(
    db: Session,
    parent: HouseholdMember,
    kid_id: uuid.UUID,
    amount: int,
    note: str,
) -> CreditTransaction:
    """Add (positive) or remove (negative) credits. Balances may go negative."""
    if amount == 0:
        raise InvalidInput("amount must not be zero")
    lock_kid(db, parent.household_id, kid_id)
    entry = CreditTransaction(
        household_id=parent.household_id,
        kid_id=kid_id,
        amount=amount,
        kind=CreditTransactionKind.MANUAL_ADJUSTMENT,
        created_by=parent.user_id,
        note=note,
    )
    db.add(entry)
    db.flush()
    notifications.notify(
        db,
        kid_id,
        parent.household_id,
        NotificationType.CREDITS_ADJUSTED,
        credit_transaction_id=entry.id,
    )
    db.commit()
    return entry
