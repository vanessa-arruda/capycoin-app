import uuid

from pydantic import BaseModel, ConfigDict

from models.enums import UserRole

from .common import DisplayName, Password, Username


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: UserRole
    display_name: str
    username: str | None
    email: str | None


class UserUpdate(BaseModel):
    display_name: DisplayName | None = None
    username: Username | None = None


class PasswordChange(BaseModel):
    current_password: str | None = None
    new_password: Password
