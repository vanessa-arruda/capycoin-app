import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, Timestamps, UUIDPrimaryKey, enum_column
from .enums import ReviewStatus

if TYPE_CHECKING:
    from .household import Household
    from .user import User


class Prize(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "prizes"
    __table_args__ = (CheckConstraint("cost > 0", name="cost_positive"),)

    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    cost: Mapped[int]
    archived_at: Mapped[datetime | None]

    household: Mapped[Household] = relationship(back_populates="prizes")
    claims: Mapped[list[PrizeClaim]] = relationship(
        back_populates="prize", passive_deletes=True
    )


class PrizeClaim(UUIDPrimaryKey, Base):
    __tablename__ = "prize_claims"
    __table_args__ = (CheckConstraint("cost > 0", name="cost_positive"),)

    prize_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("prizes.id", ondelete="CASCADE"), index=True
    )
    kid_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Copied from the prize when claimed; reserved from the balance while pending.
    cost: Mapped[int]
    status: Mapped[ReviewStatus] = mapped_column(
        enum_column(ReviewStatus, "review_status"),
        default=ReviewStatus.PENDING,
        server_default=ReviewStatus.PENDING.value,
    )
    requested_at: Mapped[datetime] = mapped_column(server_default=func.now())
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None]
    review_note: Mapped[str | None] = mapped_column(Text)

    prize: Mapped[Prize] = relationship(back_populates="claims")
    kid: Mapped[User] = relationship(foreign_keys=[kid_id])
    reviewer: Mapped[User | None] = relationship(foreign_keys=[reviewed_by])
