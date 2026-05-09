from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ActivityCreate(BaseModel):
    name: str
    description: Optional[str] = None
    default_points: int = 0
    category: str = "chore"


class ActivityRead(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    default_points: int
    category: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ParentActivityConfig(BaseModel):
    points_override: Optional[int] = None
    max_per_day: Optional[int] = None
    max_per_week: Optional[int] = None
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None


class ParentActivityRead(BaseModel):
    id: int
    activity_id: int
    points_override: Optional[int] = None
    max_per_day: Optional[int] = None
    max_per_week: Optional[int] = None
    is_active: bool

    model_config = {"from_attributes": True}


class ChildActivityCreate(BaseModel):
    activity_id: int


class ChildActivityRead(BaseModel):
    id: int
    activity_id: int
    status: str
    picked_at: datetime
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ReviewRequest(BaseModel):
    status: str  # APPROVED or REJECTED
