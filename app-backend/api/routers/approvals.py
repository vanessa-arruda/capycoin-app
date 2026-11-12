import uuid
from typing import Annotated

from fastapi import Depends, Response

from api.deps import Db, Pagination, ParentMembership, household_router
from core.storage import PhotoStore, get_photo_store
from models.enums import ReviewStatus
from schemas.approval import ClaimResponse, ReviewDecision, SubmissionResponse
from schemas.common import Page
from services import approvals

submissions = household_router("/task-submissions", tags=["approvals"])
claims = household_router("/prize-claims", tags=["approvals"])

PHOTO_SCHEMA = {"type": "string", "format": "binary"}


@submissions.get("")
def list_submissions(
    membership: ParentMembership,
    db: Db,
    page: Pagination,
    status: ReviewStatus = ReviewStatus.PENDING,
    kid_id: uuid.UUID | None = None,
) -> Page[SubmissionResponse]:
    return approvals.list_submissions(db, membership.household_id, page, status, kid_id)


@submissions.get("/{submission_id}")
def get_submission(
    submission_id: uuid.UUID, membership: ParentMembership, db: Db
) -> SubmissionResponse:
    return approvals.submission_response(
        approvals.get_submission(db, membership.household_id, submission_id)
    )


@submissions.get(
    "/{submission_id}/photo",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {"schema": PHOTO_SCHEMA}}}},
)
def get_submission_photo(
    submission_id: uuid.UUID,
    membership: ParentMembership,
    db: Db,
    store: Annotated[PhotoStore, Depends(get_photo_store)],
) -> Response:
    photo = approvals.get_photo(db, membership.household_id, submission_id, store)
    return Response(photo, media_type="image/jpeg")


@submissions.post("/{submission_id}/approve")
def approve_submission(
    submission_id: uuid.UUID,
    membership: ParentMembership,
    db: Db,
    decision: ReviewDecision | None = None,
) -> SubmissionResponse:
    note = decision.note if decision else None
    return approvals.submission_response(
        approvals.review_submission(db, membership, submission_id, True, note)
    )


@submissions.post("/{submission_id}/deny")
def deny_submission(
    submission_id: uuid.UUID,
    membership: ParentMembership,
    db: Db,
    decision: ReviewDecision | None = None,
) -> SubmissionResponse:
    note = decision.note if decision else None
    return approvals.submission_response(
        approvals.review_submission(db, membership, submission_id, False, note)
    )


@claims.get("")
def list_claims(
    membership: ParentMembership,
    db: Db,
    page: Pagination,
    status: ReviewStatus = ReviewStatus.PENDING,
    kid_id: uuid.UUID | None = None,
) -> Page[ClaimResponse]:
    return approvals.list_claims(db, membership.household_id, page, status, kid_id)


@claims.get("/{claim_id}")
def get_claim(
    claim_id: uuid.UUID, membership: ParentMembership, db: Db
) -> ClaimResponse:
    return approvals.claim_response(
        approvals.get_claim(db, membership.household_id, claim_id)
    )


@claims.post("/{claim_id}/approve")
def approve_claim(
    claim_id: uuid.UUID,
    membership: ParentMembership,
    db: Db,
    decision: ReviewDecision | None = None,
) -> ClaimResponse:
    note = decision.note if decision else None
    return approvals.claim_response(
        approvals.review_claim(db, membership, claim_id, True, note)
    )


@claims.post("/{claim_id}/deny")
def deny_claim(
    claim_id: uuid.UUID,
    membership: ParentMembership,
    db: Db,
    decision: ReviewDecision | None = None,
) -> ClaimResponse:
    note = decision.note if decision else None
    return approvals.claim_response(
        approvals.review_claim(db, membership, claim_id, False, note)
    )
