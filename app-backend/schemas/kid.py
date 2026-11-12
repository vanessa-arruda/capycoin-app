import uuid
from typing import Self

from pydantic import BaseModel, model_validator

from .common import Code, DisplayName, Email, Password, Username


class KidEmailCode(BaseModel):
    email: Email


class KidCreate(BaseModel):
    display_name: DisplayName
    email: Email | None = None
    code: Code | None = None
    username: Username | None = None
    password: Password | None = None

    @model_validator(mode="after")
    def check_login(self) -> Self:
        if self.email is not None and self.code is None:
            raise ValueError("code is required with email")
        if self.email is None and (self.username is None or self.password is None):
            raise ValueError("a kid needs an email, or a username and a password")
        return self


class KidUpdate(BaseModel):
    display_name: DisplayName | None = None
    username: Username | None = None
    password: Password | None = None
    email: Email | None = None
    code: Code | None = None

    @model_validator(mode="after")
    def check_code(self) -> Self:
        if self.email is not None and self.code is None:
            raise ValueError("code is required with email")
        return self


class KidResponse(BaseModel):
    id: uuid.UUID
    display_name: str
    username: str | None
    email: str | None
    balance: int
    reserved: int
    available: int
