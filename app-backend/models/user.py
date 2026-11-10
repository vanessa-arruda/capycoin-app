from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, Timestamps, UUIDPrimaryKey, enum_column
from .enums import UserRole

if TYPE_CHECKING:
    from .household import HouseholdMember


class User(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role <> 'parent' OR email IS NOT NULL", name="parent_has_email"
        ),
        CheckConstraint(
            "email IS NOT NULL OR (username IS NOT NULL AND password_hash IS NOT NULL)",
            name="can_log_in",
        ),
        CheckConstraint("email = lower(email)", name="email_lowercase"),
        CheckConstraint("username = lower(username)", name="username_lowercase"),
    )

    role: Mapped[UserRole] = mapped_column(enum_column(UserRole, "user_role"))
    display_name: Mapped[str] = mapped_column(String(100))
    username: Mapped[str | None] = mapped_column(String(50), unique=True)
    email: Mapped[str | None] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))

    memberships: Mapped[list[HouseholdMember]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
