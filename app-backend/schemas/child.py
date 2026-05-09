from pydantic import BaseModel, EmailStr


class ChildCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class ChildRead(BaseModel):
    id: int
    name: str
    email: str
    avatar: str
    household_id: int | None = None
    points_total: int = 0
    level: int = 1

    model_config = {"from_attributes": True}


class ChildSummary(BaseModel):
    id: int
    name: str
    avatar: str
    points_total: int
    level: int

    model_config = {"from_attributes": True}
