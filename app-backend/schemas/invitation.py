import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from models.enums import InvitationStatus

from .common import Email


class InvitationCreate(BaseModel):
    email: Email


class InvitationAccept(BaseModel):
    token: str = Field(min_length=1, max_length=100)


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    status: InvitationStatus
    expires_at: datetime
    created_at: datetime
