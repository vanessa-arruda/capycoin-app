import uuid

from fastapi import status

from api.deps import Db, Pagination, ParentMembership, household_router
from models.enums import CreditTransactionKind
from schemas.common import Page
from schemas.wallet import (
    AdjustmentCreate,
    HouseholdTransactionResponse,
    TransactionResponse,
)
from services import kids, wallet

router = household_router("/kids/{kid_id}", tags=["wallet"])
household = household_router("/transactions", tags=["wallet"])


@household.get("")
def list_household_transactions(
    membership: ParentMembership,
    db: Db,
    page: Pagination,
    kid_id: uuid.UUID | None = None,
    kind: CreditTransactionKind | None = None,
) -> Page[HouseholdTransactionResponse]:
    return wallet.list_household_transactions(
        db, membership.household_id, page, kid_id, kind
    )


@router.get("/transactions")
def list_transactions(
    kid_id: uuid.UUID, membership: ParentMembership, db: Db, page: Pagination
) -> Page[TransactionResponse]:
    kids.get_kid(db, membership.household_id, kid_id)
    return wallet.list_transactions(db, membership.household_id, kid_id, page)


@router.post("/adjustments", status_code=status.HTTP_201_CREATED)
def add_adjustment(
    kid_id: uuid.UUID,
    payload: AdjustmentCreate,
    membership: ParentMembership,
    db: Db,
) -> TransactionResponse:
    kids.get_kid(db, membership.household_id, kid_id)
    entry = wallet.adjust(db, membership, kid_id, payload.amount, payload.note)
    return wallet.transaction_response(entry)
