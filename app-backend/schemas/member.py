import uuid
from datetime import datetime

from pydantic import BaseModel

from models.enums import UserRole


class MemberResponse(BaseModel):
    user_id: uuid.UUID
    role: UserRole
    display_name: str
    username: str | None
    email: str | None
    is_admin: bool
    joined_at: datetime
