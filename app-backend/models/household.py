import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, CreatedAt, Timestamps, UUIDPrimaryKey, enum_column
from .enums import InvitationStatus

if TYPE_CHECKING:
    from .store import Prize
    from .task import Task
    from .user import User


class Household(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "households"

    name: Mapped[str] = mapped_column(String(100))
    # IANA name, e.g. "Europe/Stockholm". Defines when recurring tasks reset.
    timezone: Mapped[str] = mapped_column(String(64))

    members: Mapped[list[HouseholdMember]] = relationship(
        back_populates="household", cascade="all, delete-orphan", passive_deletes=True
    )
    invitations: Mapped[list[HouseholdInvitation]] = relationship(
        back_populates="household", cascade="all, delete-orphan", passive_deletes=True
    )
    tasks: Mapped[list[Task]] = relationship(
        back_populates="household", cascade="all, delete-orphan", passive_deletes=True
    )
    prizes: Mapped[list[Prize]] = relationship(
        back_populates="household", cascade="all, delete-orphan", passive_deletes=True
    )


class HouseholdMember(CreatedAt, Base):
    __tablename__ = "household_members"
    __table_args__ = (
        Index(
            "uq_household_members_one_admin",
            "household_id",
            unique=True,
            postgresql_where=text("is_admin"),
        ),
    )

    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    # Only parents can be admin; enforced in the application.
    is_admin: Mapped[bool] = mapped_column(default=False, server_default="false")

    household: Mapped[Household] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="memberships")


class HouseholdInvitation(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "household_invitations"
    __table_args__ = (
        CheckConstraint("email = lower(email)", name="email_lowercase"),
        Index(
            "uq_household_invitations_one_pending",
            "household_id",
            "email",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )

    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String(320))
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True)
    status: Mapped[InvitationStatus] = mapped_column(
        enum_column(InvitationStatus, "invitation_status"),
        default=InvitationStatus.PENDING,
        server_default=InvitationStatus.PENDING.value,
    )
    expires_at: Mapped[datetime]
    responded_at: Mapped[datetime | None]

    household: Mapped[Household] = relationship(back_populates="invitations")
