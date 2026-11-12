import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from core import clock
from core.errors import InvalidInput, NotFound
from models import (
    CreditTransaction,
    HouseholdMember,
    Notification,
    NotificationPreference,
    PrizeClaim,
    TaskSubmission,
    User,
)
from models.enums import NotificationChannel, NotificationType, UserRole
from schemas.common import Page, PageParams
from schemas.notification import (
    NotificationResponse,
    NotificationSubject,
    Preference,
)
from services.pagination import paginate

NOTIFICATION_NOT_FOUND = "Notification not found"

# Used when the user has no preference row for a type and channel.
CHANNEL_DEFAULTS = {NotificationChannel.IN_APP: True, NotificationChannel.EMAIL: False}

TYPES_BY_ROLE = {
    UserRole.PARENT: (NotificationType.TASK_SUBMITTED, NotificationType.PRIZE_CLAIMED),
    UserRole.KID: (
        NotificationType.TASK_APPROVED,
        NotificationType.TASK_DENIED,
        NotificationType.PRIZE_CLAIM_APPROVED,
        NotificationType.PRIZE_CLAIM_DENIED,
        NotificationType.CREDITS_ADJUSTED,
    ),
}


def is_enabled(
    db: Session,
    user_id: uuid.UUID,
    type: NotificationType,
    channel: NotificationChannel,
) -> bool:
    enabled = db.scalar(
        select(NotificationPreference.enabled).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.type == type,
            NotificationPreference.channel == channel,
        )
    )
    return CHANNEL_DEFAULTS[channel] if enabled is None else enabled


def notify(
    db: Session,
    recipient_id: uuid.UUID,
    household_id: uuid.UUID,
    type: NotificationType,
    **subject: uuid.UUID,
) -> None:
    """Add an in-app notification unless the recipient turned that type off.

    `subject` is one of task_submission_id, prize_claim_id or
    credit_transaction_id. The caller commits.
    """
    if not is_enabled(db, recipient_id, type, NotificationChannel.IN_APP):
        return
    db.add(
        Notification(
            recipient_id=recipient_id,
            household_id=household_id,
            type=type,
            **subject,
        )
    )


def notify_parents(
    db: Session,
    household_id: uuid.UUID,
    type: NotificationType,
    **subject: uuid.UUID,
) -> None:
    """Notify every parent of the household. The caller commits."""
    parent_ids = db.scalars(
        select(HouseholdMember.user_id)
        .join(User)
        .where(
            HouseholdMember.household_id == household_id,
            User.role == UserRole.PARENT,
        )
    ).all()
    for parent_id in parent_ids:
        notify(db, parent_id, household_id, type, **subject)


def _own_notifications(user: User):
    """The user's notifications from households they still belong to."""
    return (
        select(Notification)
        .join(
            HouseholdMember,
            (HouseholdMember.household_id == Notification.household_id)
            & (HouseholdMember.user_id == user.id),
        )
        .where(Notification.recipient_id == user.id)
        .options(
            joinedload(Notification.task_submission).options(
                joinedload(TaskSubmission.task), joinedload(TaskSubmission.kid)
            ),
            joinedload(Notification.prize_claim).options(
                joinedload(PrizeClaim.prize), joinedload(PrizeClaim.kid)
            ),
            joinedload(Notification.credit_transaction).joinedload(
                CreditTransaction.kid
            ),
        )
    )


def _subject(notification: Notification) -> NotificationSubject:
    if (submission := notification.task_submission) is not None:
        return NotificationSubject(
            kind="task_submission",
            id=submission.id,
            kid_id=submission.kid_id,
            kid_display_name=submission.kid.display_name,
            title=submission.task.title,
            status=submission.status,
            amount=submission.task.reward,
            note=submission.review_note,
        )
    if (claim := notification.prize_claim) is not None:
        return NotificationSubject(
            kind="prize_claim",
            id=claim.id,
            kid_id=claim.kid_id,
            kid_display_name=claim.kid.display_name,
            title=claim.prize.name,
            status=claim.status,
            amount=claim.cost,
            note=claim.review_note,
        )
    entry = notification.credit_transaction
    return NotificationSubject(
        kind="credit_transaction",
        id=entry.id,
        kid_id=entry.kid_id,
        kid_display_name=entry.kid.display_name,
        title=None,
        status=None,
        amount=entry.amount,
        note=entry.note,
    )


def notification_response(notification: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=notification.id,
        household_id=notification.household_id,
        type=notification.type,
        read_at=notification.read_at,
        created_at=notification.created_at,
        subject=_subject(notification),
    )


def list_notifications(
    db: Session,
    user: User,
    page: PageParams,
    household_id: uuid.UUID | None = None,
    unread: bool = False,
) -> Page[NotificationResponse]:
    query = _own_notifications(user)
    if household_id is not None:
        query = query.where(Notification.household_id == household_id)
    if unread:
        query = query.where(Notification.read_at.is_(None))
    rows, next_before = paginate(db, query, Notification.id, page)
    return Page(items=[notification_response(n) for n in rows], next_before=next_before)


def get_notification(
    db: Session, user: User, notification_id: uuid.UUID
) -> Notification:
    notification = db.scalar(
        _own_notifications(user).where(Notification.id == notification_id)
    )
    if notification is None:
        raise NotFound(NOTIFICATION_NOT_FOUND)
    return notification


def mark_read(db: Session, user: User, notification_id: uuid.UUID) -> None:
    notification = get_notification(db, user, notification_id)
    if notification.read_at is None:
        notification.read_at = clock.now()
        db.commit()


def mark_all_read(
    db: Session, user: User, household_id: uuid.UUID | None = None
) -> None:
    query = update(Notification).where(
        Notification.recipient_id == user.id, Notification.read_at.is_(None)
    )
    if household_id is not None:
        query = query.where(Notification.household_id == household_id)
    db.execute(query.values(read_at=clock.now()))
    db.commit()


def list_preferences(db: Session, user: User) -> list[Preference]:
    saved = {
        (row.type, row.channel): row.enabled
        for row in db.scalars(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user.id
            )
        )
    }
    return [
        Preference(
            type=type,
            channel=channel,
            enabled=saved.get((type, channel), default),
        )
        for type in TYPES_BY_ROLE[user.role]
        for channel, default in CHANNEL_DEFAULTS.items()
    ]


def update_preferences(
    db: Session, user: User, preferences: list[Preference]
) -> list[Preference]:
    """Save the given choices. Only choices that differ from the default are stored."""
    allowed = TYPES_BY_ROLE[user.role]
    for preference in preferences:
        if preference.type not in allowed:
            raise InvalidInput(f"{preference.type} is not sent to {user.role} accounts")

    for preference in preferences:
        key = (user.id, preference.type, preference.channel)
        row = db.get(NotificationPreference, key)
        if preference.enabled == CHANNEL_DEFAULTS[preference.channel]:
            if row is not None:
                db.delete(row)
        elif row is None:
            db.add(
                NotificationPreference(
                    user_id=user.id,
                    type=preference.type,
                    channel=preference.channel,
                    enabled=preference.enabled,
                )
            )
        else:
            row.enabled = preference.enabled
        db.flush()
    db.commit()
    return list_preferences(db, user)
