from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import text

from models import Base


def test_migrations_match_models(db):
    context = MigrationContext.configure(db.connection())

    assert compare_metadata(context, Base.metadata) == []


def test_every_table_has_row_level_security(db):
    """New tables must enable RLS, or Supabase's REST API can read them."""
    tables_without_rls = db.scalars(text("""
            SELECT c.relname FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = 'r' AND NOT c.relrowsecurity
            """)).all()

    assert tables_without_rls == []
