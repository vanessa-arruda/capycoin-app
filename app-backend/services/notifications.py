import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Notification, NotificationPreference
from models.enums import NotificationChannel, NotificationType

# Used when the user has no preference row for a type and channel.
CHANNEL_DEFAULTS = {NotificationChannel.IN_APP: True, NotificationChannel.EMAIL: False}


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
