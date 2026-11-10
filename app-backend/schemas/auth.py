from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from .common import Code, DisplayName, Email, Login
from .user import UserResponse


class OtpRequest(BaseModel):
    email: Email


class OtpVerify(BaseModel):
    email: Email
    code: Code
    display_name: DisplayName | None = None


class PasswordLogin(BaseModel):
    login: Login
    password: Annotated[str, Field(min_length=1, max_length=128)]


class SessionResponse(BaseModel):
    token: str
    expires_at: datetime
    user: UserResponse
