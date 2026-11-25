import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from models.enums import CreditTransactionKind


class AdjustmentCreate(BaseModel):
    amount: Annotated[int, Field(ge=-1_000_000, le=1_000_000)]
    note: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
    ]


class TransactionResponse(BaseModel):
    id: uuid.UUID
    amount: int
    kind: CreditTransactionKind
    note: str | None
    task_submission_id: uuid.UUID | None
    task_title: str | None
    prize_claim_id: uuid.UUID | None
    prize_name: str | None
    created_by: uuid.UUID | None
    # Read from users when fetched, so it shows the current name.
    created_by_name: str | None
    created_at: datetime


class HouseholdTransactionResponse(TransactionResponse):
    kid_id: uuid.UUID
    kid_display_name: str


class WeekTotals(BaseModel):
    # Monday of this week in the household's timezone.
    start: date
    # Task rewards and coins added.
    earned: int
    # Prizes paid for. Coins removed by a parent count as neither.
    spent: int


class WalletResponse(BaseModel):
    balance: int
    reserved: int
    available: int
    this_week: WeekTotals
