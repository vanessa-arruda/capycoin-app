import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from models.enums import NotificationChannel, NotificationType, ReviewStatus


class NotificationSubject(BaseModel):
    """What a notification is about, enough to show it without another request."""

    kind: Literal["task_submission", "prize_claim", "credit_transaction"]
    id: uuid.UUID
    kid_id: uuid.UUID
    kid_display_name: str
    # Task title or prize name.
    title: str | None
    status: ReviewStatus | None
    # Task reward, claim cost, or credits added (positive) or removed (negative).
    amount: int
    # The parent's review note, or the adjustment note.
    note: str | None


class NotificationResponse(BaseModel):
    id: uuid.UUID
    household_id: uuid.UUID
    type: NotificationType
    read_at: datetime | None
    created_at: datetime
    subject: NotificationSubject


class ReadAll(BaseModel):
    household_id: uuid.UUID | None = None


class Preference(BaseModel):
    type: NotificationType
    channel: NotificationChannel
    enabled: bool


class PreferencesUpdate(BaseModel):
    preferences: list[Preference] = Field(max_length=50)
