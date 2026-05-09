from pydantic import BaseModel, EmailStr


class ParentCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class ParentRead(BaseModel):
    id: int
    name: str
    email: str
    household_id: int | None = None

    model_config = {"from_attributes": True}
