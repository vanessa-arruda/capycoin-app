import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

PrizeName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
Cost = Annotated[int, Field(gt=0, le=1_000_000)]


class PrizeCreate(BaseModel):
    name: PrizeName
    description: Description | None = None
    cost: Cost


class PrizeUpdate(BaseModel):
    name: PrizeName | None = None
    description: Description | None = None
    cost: Cost | None = None


class PrizeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    cost: int
    archived_at: datetime | None
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
