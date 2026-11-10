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

import re  # noqa: E402
from datetime import UTC, datetime, timedelta  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pwdlib import PasswordHash  # noqa: E402
from pwdlib.hashers.argon2 import Argon2Hasher  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from api.deps import get_db  # noqa: E402
from core import clock, security  # noqa: E402
from core.config import settings  # noqa: E402
from core.database import engine  # noqa: E402
from core.email import get_email_sender  # noqa: E402
from core.security import hash_secret  # noqa: E402
from main import app  # noqa: E402
from models import Household, HouseholdMember, User  # noqa: E402
from models.enums import UserRole  # noqa: E402
from services.auth import create_session  # noqa: E402

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
def fast_hashing():
    """Cheap Argon2 settings; the real ones take about 40 ms per hash."""
    original = security._hasher
    security._hasher = PasswordHash((Argon2Hasher(time_cost=1, memory_cost=1024),))
    yield
    security._hasher = original


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


class Outbox:
    """Email sender that keeps messages instead of sending them."""

    def __init__(self):
        self.messages = []

    def send(self, message) -> None:
        self.messages.append(message)

    def last_code(self) -> str:
        return re.search(r"\b(\d{6})\b", self.messages[-1].body).group(1)


@pytest.fixture
def outbox():
    outbox = Outbox()
    app.dependency_overrides[get_email_sender] = lambda: outbox
    yield outbox
    app.dependency_overrides.pop(get_email_sender, None)


class FakeClock:
    def __init__(self, start: datetime):
        self.current = start

    def now(self) -> datetime:
        return self.current

    def advance(self, **delta) -> None:
        self.current += timedelta(**delta)


@pytest.fixture
def frozen_clock(monkeypatch):
    fake = FakeClock(datetime.now(UTC))
    monkeypatch.setattr(clock, "now", fake.now)
    return fake


@pytest.fixture
def make_user(db):
    def make(role=UserRole.PARENT, password=None, **fields) -> User:
        user = User(
            role=role,
            display_name=fields.pop("display_name", "Someone"),
            password_hash=hash_secret(password) if password else None,
            **fields,
        )
        db.add(user)
        db.commit()
        return user

    return make


@pytest.fixture
def auth_headers(db):
    def headers(user: User) -> dict[str, str]:
        new_session = create_session(db, user)
        db.commit()
        return {"Authorization": f"Bearer {new_session.token}"}

    return headers


@pytest.fixture
def make_household(db):
    def make(admin: User, *members: User, name="Home") -> Household:
        household = Household(name=name, timezone="Europe/Stockholm")
        household.members.append(HouseholdMember(user=admin, is_admin=True))
        household.members.extend(HouseholdMember(user=member) for member in members)
        db.add(household)
        db.commit()
        return household

    return make
