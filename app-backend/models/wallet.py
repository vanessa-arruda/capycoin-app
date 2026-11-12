import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, CreatedAt, UUIDPrimaryKey, enum_column
from .enums import CreditTransactionKind

if TYPE_CHECKING:
    from .store import PrizeClaim
    from .task import TaskSubmission
    from .user import User


class CreditTransaction(UUIDPrimaryKey, CreatedAt, Base):
    """Append-only wallet log. A kid's balance in a household is SUM(amount)."""

    __tablename__ = "credit_transactions"
    __table_args__ = (
        CheckConstraint("amount <> 0", name="amount_not_zero"),
        CheckConstraint(
            "(kind = 'task_reward') = (task_submission_id IS NOT NULL)"
            " AND (kind = 'prize_claim') = (prize_claim_id IS NOT NULL)",
            name="source_matches_kind",
        ),
        CheckConstraint(
            "kind <> 'task_reward' OR amount > 0", name="task_reward_positive"
        ),
        CheckConstraint(
            "kind <> 'prize_claim' OR amount < 0", name="prize_claim_negative"
        ),
        Index("ix_credit_transactions_household_id_kid_id", "household_id", "kid_id"),
    )

    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE")
    )
    kid_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    amount: Mapped[int]
    kind: Mapped[CreditTransactionKind] = mapped_column(
        enum_column(CreditTransactionKind, "credit_transaction_kind")
    )
    task_submission_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("task_submissions.id"), unique=True
    )
    prize_claim_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("prize_claims.id"), unique=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    note: Mapped[str | None] = mapped_column(Text)

    kid: Mapped[User] = relationship(foreign_keys=[kid_id])
    creator: Mapped[User | None] = relationship(foreign_keys=[created_by])
    task_submission: Mapped[TaskSubmission | None] = relationship()
    prize_claim: Mapped[PrizeClaim | None] = relationship()
