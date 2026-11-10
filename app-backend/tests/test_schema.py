from datetime import UTC, datetime, timedelta

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import text
from sqlalchemy.exc import StatementError

from models import Base, UserSession


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


class TestTimestamps:
    def test_read_back_in_utc_whatever_the_session_timezone(self, db, make_user):
        user = make_user(email="mom@example.com")
        db.execute(text("SET LOCAL TIME ZONE 'America/Sao_Paulo'"))
        db.expire(user)

        assert user.created_at.utcoffset() == timedelta(0)
        assert user.created_at.tzinfo is UTC

    def test_rejects_datetimes_without_a_timezone(self, db, make_user):
        session = UserSession(
            user=make_user(email="mom@example.com"),
            token_hash="x" * 64,
            expires_at=datetime(2030, 1, 1),
            last_used_at=datetime.now(UTC),
        )
        db.add(session)

        with pytest.raises(StatementError, match="without a timezone"):
            db.flush()
