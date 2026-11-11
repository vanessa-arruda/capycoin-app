from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAt, UUIDPrimaryKey


class RateLimitEvent(UUIDPrimaryKey, CreatedAt, Base):
    """One counted action, such as a failed login. Old rows are deleted.

    `key` is the kind of limit plus a SHA-256 of the login, IP address or
    household it counts, so no personal data is stored.
    """

    __tablename__ = "rate_limit_events"
    __table_args__ = (
        Index("ix_rate_limit_events_key_created_at", "key", "created_at"),
        Index("ix_rate_limit_events_created_at", "created_at"),
    )

    key: Mapped[str] = mapped_column(String(100))
