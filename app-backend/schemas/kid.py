import uuid

from pydantic import BaseModel

from .common import DisplayName, Password, Username


class KidCreate(BaseModel):
    display_name: DisplayName
    username: Username
    password: Password


class KidUpdate(BaseModel):
    display_name: DisplayName | None = None
    username: Username | None = None
    password: Password | None = None


class KidResponse(BaseModel):
    id: uuid.UUID
    display_name: str
    username: str | None
    balance: int
    reserved: int
    available: int
