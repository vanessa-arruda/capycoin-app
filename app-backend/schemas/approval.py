import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, StringConstraints

from models.enums import ReviewStatus


class ReviewDecision(BaseModel):
    note: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None
    ) = None


class SubmissionResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    task_title: str
    # The task's current reward; an approval credits this amount.
    reward: int
    kid_id: uuid.UUID
    kid_display_name: str
    period_start: date
    status: ReviewStatus
    note: str | None
    submitted_at: datetime
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    review_note: str | None


class ClaimResponse(BaseModel):
    id: uuid.UUID
    prize_id: uuid.UUID
    prize_name: str
    # Fixed when the kid claimed the prize.
    cost: int
    kid_id: uuid.UUID
    kid_display_name: str
    status: ReviewStatus
    requested_at: datetime
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    review_note: str | None
