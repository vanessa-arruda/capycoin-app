import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, CreatedAt, Timestamps, UUIDPrimaryKey, enum_column
from .enums import Recurrence, ReviewStatus

if TYPE_CHECKING:
    from .household import Household
    from .user import User


class Task(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "tasks"
    __table_args__ = (CheckConstraint("reward > 0", name="reward_positive"),)

    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    reward: Mapped[int]
    recurrence: Mapped[Recurrence] = mapped_column(
        enum_column(Recurrence, "recurrence"),
        default=Recurrence.NONE,
        server_default=Recurrence.NONE.value,
    )
    starts_on: Mapped[date]
    # One-off task: the deadline. Recurring task: when it stops repeating.
    due_at: Mapped[datetime | None]
    archived_at: Mapped[datetime | None]

    household: Mapped[Household] = relationship(back_populates="tasks")
    assignments: Mapped[list[TaskAssignment]] = relationship(
        back_populates="task", cascade="all, delete-orphan", passive_deletes=True
    )
    submissions: Mapped[list[TaskSubmission]] = relationship(
        back_populates="task", passive_deletes=True
    )


class TaskAssignment(CreatedAt, Base):
    __tablename__ = "task_assignments"

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
    )
    kid_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )

    task: Mapped[Task] = relationship(back_populates="assignments")
    kid: Mapped[User] = relationship()


class TaskSubmission(UUIDPrimaryKey, Base):
    __tablename__ = "task_submissions"
    __table_args__ = (
        # One active submission per kid per period; a denied one can be redone.
        Index(
            "uq_task_submissions_one_active_per_period",
            "task_id",
            "kid_id",
            "period_start",
            unique=True,
            postgresql_where=text("status <> 'denied'"),
        ),
    )

    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), index=True
    )
    kid_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Start of the day/week/month for recurring tasks, tasks.starts_on otherwise.
    period_start: Mapped[date]
    status: Mapped[ReviewStatus] = mapped_column(
        enum_column(ReviewStatus, "review_status"),
        default=ReviewStatus.PENDING,
        server_default=ReviewStatus.PENDING.value,
    )
    note: Mapped[str | None] = mapped_column(Text)
    # Path of the proof image in object storage.
    photo_path: Mapped[str | None] = mapped_column(String(500))
    submitted_at: Mapped[datetime] = mapped_column(server_default=func.now())
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None]
    review_note: Mapped[str | None] = mapped_column(Text)

    task: Mapped[Task] = relationship(back_populates="submissions")
    kid: Mapped[User] = relationship(foreign_keys=[kid_id])
    reviewer: Mapped[User | None] = relationship(foreign_keys=[reviewed_by])
