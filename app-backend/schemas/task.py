import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, Field, StringConstraints

from models.enums import Recurrence

Title = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
Reward = Annotated[int, Field(gt=0, le=1_000_000)]
KidIds = Annotated[list[uuid.UUID], Field(min_length=1, max_length=50)]


class TaskCreate(BaseModel):
    title: Title
    description: Description | None = None
    reward: Reward
    recurrence: Recurrence = Recurrence.NONE
    starts_on: date
    due_at: AwareDatetime | None = None
    kid_ids: KidIds


class TaskUpdate(BaseModel):
    title: Title | None = None
    description: Description | None = None
    reward: Reward | None = None
    recurrence: Recurrence | None = None
    starts_on: date | None = None
    due_at: AwareDatetime | None = None
    kid_ids: KidIds | None = None


class TaskResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    reward: int
    recurrence: Recurrence
    starts_on: date
    due_at: datetime | None
    archived_at: datetime | None
    kid_ids: list[uuid.UUID]
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
