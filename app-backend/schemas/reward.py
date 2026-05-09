from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class RewardCreate(BaseModel):
    name: str
    description: Optional[str] = None
    points_cost: int


class RewardRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    points_cost: int
    is_active: bool

    model_config = {"from_attributes": True}


class RedemptionRead(BaseModel):
    id: int
    reward_id: int
    status: str
    redeemed_at: datetime

    model_config = {"from_attributes": True}


class RedemptionReview(BaseModel):
    status: str  # APPROVED or REJECTED


class PendingRedemptionRead(BaseModel):
    id: int
    child_name: str
    reward_name: str
    points_cost: int
    redeemed_at: datetime
