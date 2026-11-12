import uuid
from datetime import date, datetime

from pydantic import BaseModel

from models.enums import Recurrence, ReviewStatus


class KidSubmissionResponse(BaseModel):
    id: uuid.UUID
    status: ReviewStatus
    note: str | None
    has_photo: bool
    submitted_at: datetime
    reviewed_at: datetime | None
    review_note: str | None
    reviewed_by_name: str | None


class KidTaskResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    reward: int
    recurrence: Recurrence
    starts_on: date
    due_at: datetime | None
    period_start: date
    # Last day of the current period; null for one-off tasks, which use due_at.
    period_end: date | None
    # The latest submission for the current period.
    submission: KidSubmissionResponse | None
