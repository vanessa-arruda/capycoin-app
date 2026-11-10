"""otp code purpose

Revision ID: 9d4eda56b44e
Revises: cf6fe3aa6fb8
Create Date: 2026-11-10 15:06:08.089559

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "9d4eda56b44e"
down_revision: Union[str, Sequence[str], None] = "cf6fe3aa6fb8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Codes live for minutes, so existing ones can be dropped instead of migrated.
    op.execute("DELETE FROM otp_codes")
    op.add_column(
        "otp_codes", sa.Column("purpose", sa.String(length=32), nullable=False)
    )
    op.create_check_constraint(
        op.f("ck_otp_codes_otp_purpose"),
        "otp_codes",
        "purpose IN ('login', 'email_validation')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_otp_codes_otp_purpose"), "otp_codes", type_="check")
    op.drop_column("otp_codes", "purpose")
