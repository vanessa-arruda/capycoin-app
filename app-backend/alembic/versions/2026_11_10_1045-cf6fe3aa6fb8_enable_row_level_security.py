"""enable row level security

Supabase exposes tables in the public schema through its REST API to the
`anon` and `authenticated` roles. The backend is the only client of this
database, so turn RLS on with no policies and remove those roles' access.
The backend connects as the tables' owner, which RLS does not apply to.

Tables added by later migrations must enable RLS too; tests check this.

Revision ID: cf6fe3aa6fb8
Revises: 1a85b1449357
Create Date: 2026-11-10 10:45:44.919542

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cf6fe3aa6fb8"
down_revision: Union[str, Sequence[str], None] = "1a85b1449357"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        DO $$
        DECLARE
            t text;
            r text;
        BEGIN
            FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
                EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
            END LOOP;

            FOREACH r IN ARRAY ARRAY['anon', 'authenticated'] LOOP
                IF EXISTS (SELECT FROM pg_roles WHERE rolname = r) THEN
                    EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA public FROM %I', r);
                    EXECUTE format(
                        'ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM %I',
                        r
                    );
                END IF;
            END LOOP;
        END $$;
        """)


def downgrade() -> None:
    # Grants are not restored: reopening the REST API is never wanted.
    op.execute("""
        DO $$
        DECLARE t text;
        BEGIN
            FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
                EXECUTE format('ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY', t);
            END LOOP;
        END $$;
        """)
