import os

# Tests use the local container from `make be-db-up`, never the database in .env.
# Must run before core.config is imported.
os.environ.update(
    username="postgres",
    password="postgres",
    host="localhost",
    port=os.environ.get("TEST_DB_PORT", "5432"),
    dbname="capycoin_test",
)

from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from api.deps import get_db  # noqa: E402
from core.config import settings  # noqa: E402
from core.database import engine  # noqa: E402
from main import app  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _create_test_database() -> None:
    admin = create_engine(
        settings.database_url.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    with admin.connect() as connection:
        exists = connection.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": settings.dbname},
        )
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{settings.dbname}"'))
    admin.dispose()


@pytest.fixture(scope="session", autouse=True)
def database() -> None:
    # The schema is rebuilt from scratch, so never point this at a real database.
    assert settings.host in ("localhost", "127.0.0.1")
    assert settings.dbname.endswith("_test")

    _create_test_database()
    config = Config(BACKEND_DIR / "alembic.ini")
    command.downgrade(config, "base")
    command.upgrade(config, "head")


@pytest.fixture
def db():
    """Session whose changes are rolled back after each test."""
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        yield session
        session.close()
        transaction.rollback()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
