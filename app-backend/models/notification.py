import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, CreatedAt, UUIDPrimaryKey, enum_column
from .enums import NotificationChannel, NotificationType

if TYPE_CHECKING:
    from .store import PrizeClaim
    from .task import TaskSubmission
    from .wallet import CreditTransaction


class Notification(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_recipient_id_created_at", "recipient_id", "created_at"),
    )

    recipient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[NotificationType] = mapped_column(
        enum_column(NotificationType, "notification_type")
    )
    task_submission_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("task_submissions.id", ondelete="CASCADE")
    )
    prize_claim_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("prize_claims.id", ondelete="CASCADE")
    )
    credit_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("credit_transactions.id", ondelete="CASCADE")
    )
    read_at: Mapped[datetime | None]

    task_submission: Mapped[TaskSubmission | None] = relationship()
    prize_claim: Mapped[PrizeClaim | None] = relationship()
    credit_transaction: Mapped[CreditTransaction | None] = relationship()


class NotificationPreference(Base):
    """A missing row means the channel's default applies."""

    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    type: Mapped[NotificationType] = mapped_column(
        enum_column(NotificationType, "notification_type"),
        primary_key=True,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        enum_column(NotificationChannel, "notification_channel"), primary_key=True
    )
    enabled: Mapped[bool]
