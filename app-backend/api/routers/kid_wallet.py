import uuid

from fastapi import status

from api.deps import Db, KidMembership, Pagination, household_router
from models.enums import ReviewStatus
from schemas.approval import ClaimResponse
from schemas.common import Page
from schemas.prize import StorePrizeResponse
from schemas.wallet import TransactionResponse, WalletResponse
from services import approvals, kid_wallet, wallet

router = household_router("/me", tags=["kid app"])


@router.get("/wallet")
def get_wallet(membership: KidMembership, db: Db) -> WalletResponse:
    return kid_wallet.get_wallet(db, membership)


@router.get("/transactions")
def list_transactions(
    membership: KidMembership, db: Db, page: Pagination
) -> Page[TransactionResponse]:
    return wallet.list_transactions(
        db, membership.household_id, membership.user_id, page
    )


@router.get("/prizes")
def list_prizes(membership: KidMembership, db: Db) -> list[StorePrizeResponse]:
    return kid_wallet.list_prizes(db, membership)


@router.post("/prizes/{prize_id}/claims", status_code=status.HTTP_201_CREATED)
def claim_prize(
    prize_id: uuid.UUID, membership: KidMembership, db: Db
) -> ClaimResponse:
    return approvals.claim_response(kid_wallet.claim_prize(db, membership, prize_id))


@router.get("/prize-claims")
def list_claims(
    membership: KidMembership,
    db: Db,
    page: Pagination,
    status: ReviewStatus = ReviewStatus.PENDING,
) -> Page[ClaimResponse]:
    return approvals.list_claims(
        db, membership.household_id, page, status, membership.user_id
    )
