"""auth sessions and email otp codes

Revision ID: 1a85b1449357
Revises: 53bfd72b0405
Create Date: 2026-11-10 10:45:00.425080

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "1a85b1449357"
down_revision: Union[str, Sequence[str], None] = "53bfd72b0405"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_sessions_token_hash")),
    )
    op.create_index(op.f("ix_sessions_user_id"), "sessions", ["user_id"], unique=False)

    # Codes live for minutes, so existing ones can be dropped instead of migrated.
    op.execute("DELETE FROM otp_codes")
    op.drop_index(op.f("ix_otp_codes_user_id"), table_name="otp_codes")
    op.drop_constraint(
        op.f("fk_otp_codes_user_id_users"), "otp_codes", type_="foreignkey"
    )
    op.drop_column("otp_codes", "user_id")
    op.add_column(
        "otp_codes", sa.Column("email", sa.String(length=320), nullable=False)
    )
    op.create_index(op.f("ix_otp_codes_email"), "otp_codes", ["email"], unique=False)
    op.create_check_constraint(
        op.f("ck_otp_codes_email_lowercase"), "otp_codes", "email = lower(email)"
    )


def downgrade() -> None:
    op.execute("DELETE FROM otp_codes")
    op.drop_constraint(op.f("ck_otp_codes_email_lowercase"), "otp_codes", type_="check")
    op.drop_index(op.f("ix_otp_codes_email"), table_name="otp_codes")
    op.drop_column("otp_codes", "email")
    op.add_column("otp_codes", sa.Column("user_id", sa.Uuid(), nullable=False))
    op.create_foreign_key(
        op.f("fk_otp_codes_user_id_users"),
        "otp_codes",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_otp_codes_user_id"), "otp_codes", ["user_id"], unique=False
    )
    op.drop_index(op.f("ix_sessions_user_id"), table_name="sessions")
    op.drop_table("sessions")
