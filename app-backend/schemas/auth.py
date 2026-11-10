from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from .common import DisplayName, Email, Login
from .user import UserResponse


class OtpRequest(BaseModel):
    email: Email


class OtpVerify(BaseModel):
    email: Email
    code: Annotated[str, StringConstraints(pattern=r"^\d{6}$")]
    display_name: DisplayName | None = None


class PasswordLogin(BaseModel):
    login: Login
    password: Annotated[str, Field(min_length=1, max_length=128)]


class SessionResponse(BaseModel):
    token: str
    expires_at: datetime
    user: UserResponse
