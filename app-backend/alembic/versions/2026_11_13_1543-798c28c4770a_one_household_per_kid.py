"""one household per kid

Revision ID: 798c28c4770a
Revises: 55c2c40dc7c7
Create Date: 2026-11-13 15:43:01.639915

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "798c28c4770a"
down_revision: Union[str, Sequence[str], None] = "55c2c40dc7c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Kids belong to one household for now. The role lives on users, so a unique
# index on household_members cannot express this; a trigger checks it instead.
FUNCTION = """
CREATE FUNCTION one_household_per_kid() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF (SELECT role FROM users WHERE id = NEW.user_id) <> 'kid' THEN
        RETURN NEW;
    END IF;
    -- Lock the kid so two memberships added at the same time are checked
    -- one after the other.
    PERFORM 1 FROM users WHERE id = NEW.user_id FOR UPDATE;
    IF EXISTS (
        SELECT 1 FROM household_members m
        WHERE m.user_id = NEW.user_id
          AND m.household_id <> NEW.household_id
          AND (TG_OP = 'INSERT' OR m.household_id <> OLD.household_id)
    ) THEN
        RAISE EXCEPTION 'A kid can belong to only one household'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$
"""


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(FUNCTION)
    op.execute(
        "CREATE TRIGGER one_household_per_kid"
        " BEFORE INSERT OR UPDATE OF household_id, user_id ON household_members"
        " FOR EACH ROW EXECUTE FUNCTION one_household_per_kid()"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER one_household_per_kid ON household_members")
    op.execute("DROP FUNCTION one_household_per_kid()")
