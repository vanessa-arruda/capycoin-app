"""Test data that several test modules share."""

from datetime import date

from sqlalchemy import func, select

from models import (
    CreditTransaction,
    Notification,
    Prize,
    PrizeClaim,
    Task,
    TaskAssignment,
    TaskSubmission,
)
from models.enums import CreditTransactionKind, NotificationType, ReviewStatus


def fill_wallet(db, household, kid, parent):
    """Give the kid a rewarded task, a paid prize, a pending claim and notifications.

    Balance 10 - 4 + 3 = 9, with 5 reserved by the pending claim.
    """
    task = Task(
        household_id=household.id, title="Dishes", reward=10, starts_on=date.today()
    )
    prize = Prize(household_id=household.id, name="Ice cream", cost=4)
    big_prize = Prize(household_id=household.id, name="Movie", cost=5)
    db.add_all([task, prize, big_prize])
    db.flush()
    submission = TaskSubmission(
        task_id=task.id,
        kid_id=kid.id,
        period_start=task.starts_on,
        status=ReviewStatus.APPROVED,
    )
    paid = PrizeClaim(
        prize_id=prize.id, kid_id=kid.id, cost=4, status=ReviewStatus.APPROVED
    )
    pending = PrizeClaim(prize_id=big_prize.id, kid_id=kid.id, cost=5)
    db.add_all([TaskAssignment(task_id=task.id, kid_id=kid.id), submission, paid])
    db.add(pending)
    db.flush()
    db.add_all(
        [
            CreditTransaction(
                household_id=household.id,
                kid_id=kid.id,
                amount=10,
                kind=CreditTransactionKind.TASK_REWARD,
                task_submission_id=submission.id,
            ),
            CreditTransaction(
                household_id=household.id,
                kid_id=kid.id,
                amount=-4,
                kind=CreditTransactionKind.PRIZE_CLAIM,
                prize_claim_id=paid.id,
            ),
            CreditTransaction(
                household_id=household.id,
                kid_id=kid.id,
                amount=3,
                kind=CreditTransactionKind.MANUAL_ADJUSTMENT,
            ),
            Notification(
                recipient_id=parent.id,
                household_id=household.id,
                type=NotificationType.TASK_SUBMITTED,
                task_submission_id=submission.id,
            ),
            Notification(
                recipient_id=kid.id,
                household_id=household.id,
                type=NotificationType.TASK_APPROVED,
                task_submission_id=submission.id,
            ),
        ]
    )
    db.commit()


def count(db, model, **filters):
    return db.scalar(select(func.count()).select_from(model).filter_by(**filters))
