import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from core import clock
from core.errors import Conflict, NotFound
from core.storage import PhotoStore
from models import (
    CreditTransaction,
    HouseholdMember,
    Prize,
    PrizeClaim,
    Task,
    TaskSubmission,
)
from models.enums import CreditTransactionKind, NotificationType, ReviewStatus
from schemas.approval import ClaimResponse, SubmissionResponse
from schemas.common import Page, PageParams
from services import notifications, wallet
from services.pagination import paginate

SUBMISSION_NOT_FOUND = "Task submission not found"
CLAIM_NOT_FOUND = "Prize claim not found"
NOT_PENDING = "This request was already reviewed"
NO_PHOTO = "This submission has no photo"


def submission_response(submission: TaskSubmission) -> SubmissionResponse:
    return SubmissionResponse(
        id=submission.id,
        task_id=submission.task_id,
        task_title=submission.task.title,
        reward=submission.task.reward,
        kid_id=submission.kid_id,
        kid_display_name=submission.kid.display_name,
        period_start=submission.period_start,
        status=submission.status,
        note=submission.note,
        has_photo=submission.photo_path is not None,
        submitted_at=submission.submitted_at,
        reviewed_by=submission.reviewed_by,
        reviewed_at=submission.reviewed_at,
        review_note=submission.review_note,
    )


def claim_response(claim: PrizeClaim) -> ClaimResponse:
    return ClaimResponse(
        id=claim.id,
        prize_id=claim.prize_id,
        prize_name=claim.prize.name,
        cost=claim.cost,
        kid_id=claim.kid_id,
        kid_display_name=claim.kid.display_name,
        status=claim.status,
        requested_at=claim.requested_at,
        reviewed_by=claim.reviewed_by,
        reviewed_at=claim.reviewed_at,
        review_note=claim.review_note,
    )


def _submissions(household_id: uuid.UUID):
    return (
        select(TaskSubmission)
        .join(Task)
        .where(Task.household_id == household_id)
        .options(joinedload(TaskSubmission.task), joinedload(TaskSubmission.kid))
    )


def _claims(household_id: uuid.UUID):
    return (
        select(PrizeClaim)
        .join(Prize)
        .where(Prize.household_id == household_id)
        .options(joinedload(PrizeClaim.prize), joinedload(PrizeClaim.kid))
    )


def list_submissions(
    db: Session,
    household_id: uuid.UUID,
    page: PageParams,
    status: ReviewStatus,
    kid_id: uuid.UUID | None,
) -> Page[SubmissionResponse]:
    query = _submissions(household_id).where(TaskSubmission.status == status)
    if kid_id is not None:
        query = query.where(TaskSubmission.kid_id == kid_id)
    rows, next_before = paginate(db, query, TaskSubmission.id, page)
    return Page(items=[submission_response(r) for r in rows], next_before=next_before)


def list_claims(
    db: Session,
    household_id: uuid.UUID,
    page: PageParams,
    status: ReviewStatus,
    kid_id: uuid.UUID | None,
) -> Page[ClaimResponse]:
    query = _claims(household_id).where(PrizeClaim.status == status)
    if kid_id is not None:
        query = query.where(PrizeClaim.kid_id == kid_id)
    rows, next_before = paginate(db, query, PrizeClaim.id, page)
    return Page(items=[claim_response(r) for r in rows], next_before=next_before)


def get_submission(
    db: Session, household_id: uuid.UUID, submission_id: uuid.UUID
) -> TaskSubmission:
    submission = db.scalar(
        _submissions(household_id).where(TaskSubmission.id == submission_id)
    )
    if submission is None:
        raise NotFound(SUBMISSION_NOT_FOUND)
    return submission


def get_photo(
    db: Session, household_id: uuid.UUID, submission_id: uuid.UUID, store: PhotoStore
) -> bytes:
    submission = get_submission(db, household_id, submission_id)
    photo = store.read(submission.photo_path) if submission.photo_path else None
    if photo is None:
        raise NotFound(NO_PHOTO)
    return photo


def get_claim(db: Session, household_id: uuid.UUID, claim_id: uuid.UUID) -> PrizeClaim:
    claim = db.scalar(_claims(household_id).where(PrizeClaim.id == claim_id))
    if claim is None:
        raise NotFound(CLAIM_NOT_FOUND)
    return claim


def _lock_pending(
    db: Session, parent: HouseholdMember, request: TaskSubmission | PrizeClaim
) -> None:
    """Lock the kid and check the request is still pending."""
    wallet.lock_kid(db, parent.household_id, request.kid_id)
    # Read the status again now that concurrent reviews of this kid must wait.
    db.refresh(request, ["status"])
    if request.status != ReviewStatus.PENDING:
        db.rollback()
        raise Conflict(NOT_PENDING)


def _record_review(
    parent: HouseholdMember,
    request: TaskSubmission | PrizeClaim,
    status: ReviewStatus,
    note: str | None,
) -> None:
    request.status = status
    request.reviewed_by = parent.user_id
    request.reviewed_at = clock.now()
    request.review_note = note or None


def review_submission(
    db: Session,
    parent: HouseholdMember,
    submission_id: uuid.UUID,
    approve: bool,
    note: str | None,
) -> TaskSubmission:
    submission = get_submission(db, parent.household_id, submission_id)
    _lock_pending(db, parent, submission)
    status = ReviewStatus.APPROVED if approve else ReviewStatus.DENIED
    _record_review(parent, submission, status, note)
    if approve:
        db.add(
            CreditTransaction(
                household_id=parent.household_id,
                kid_id=submission.kid_id,
                amount=submission.task.reward,
                kind=CreditTransactionKind.TASK_REWARD,
                task_submission_id=submission.id,
                created_by=parent.user_id,
            )
        )
    notifications.notify(
        db,
        submission.kid_id,
        parent.household_id,
        NotificationType.TASK_APPROVED if approve else NotificationType.TASK_DENIED,
        task_submission_id=submission.id,
    )
    db.commit()
    return submission


def review_claim(
    db: Session,
    parent: HouseholdMember,
    claim_id: uuid.UUID,
    approve: bool,
    note: str | None,
) -> PrizeClaim:
    claim = get_claim(db, parent.household_id, claim_id)
    _lock_pending(db, parent, claim)
    if approve:
        # The claim is still pending here, so it counts as reserved: its cost is
        # covered when the available balance (balance minus every pending
        # claim) is not negative.
        balance = wallet.balances(db, parent.household_id, [claim.kid_id])
        if balance[claim.kid_id].available < 0:
            db.rollback()
            raise Conflict("The kid does not have enough credits for this prize")
    status = ReviewStatus.APPROVED if approve else ReviewStatus.DENIED
    _record_review(parent, claim, status, note)
    if approve:
        db.add(
            CreditTransaction(
                household_id=parent.household_id,
                kid_id=claim.kid_id,
                amount=-claim.cost,
                kind=CreditTransactionKind.PRIZE_CLAIM,
                prize_claim_id=claim.id,
                created_by=parent.user_id,
            )
        )
    notifications.notify(
        db,
        claim.kid_id,
        parent.household_id,
        (
            NotificationType.PRIZE_CLAIM_APPROVED
            if approve
            else NotificationType.PRIZE_CLAIM_DENIED
        ),
        prize_claim_id=claim.id,
    )
    db.commit()
    return claim
