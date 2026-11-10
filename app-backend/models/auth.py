import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAt, UUIDPrimaryKey


class OtpCode(UUIDPrimaryKey, CreatedAt, Base):
    """One-time login code. Keyed by email so it also works for sign-up."""

    __tablename__ = "otp_codes"
    __table_args__ = (CheckConstraint("email = lower(email)", name="email_lowercase"),)

    email: Mapped[str] = mapped_column(String(320), index=True)
    code_hash: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime]
    consumed_at: Mapped[datetime | None]
    attempts: Mapped[int] = mapped_column(default=0, server_default="0")


class UserSession(UUIDPrimaryKey, CreatedAt, Base):
    """Login session. The client holds the token; only its SHA-256 is stored."""

    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime]
    last_used_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
