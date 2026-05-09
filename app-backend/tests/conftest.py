import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.database import Base, get_db
from main import app

TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def parent_payload():
    return {"name": "Test Parent", "email": "parent@test.com", "password": "secret123"}


@pytest.fixture
def child_payload():
    return {"name": "Test Child", "email": "child@test.com", "password": "secret123"}


@pytest.fixture
def registered_parent(client, parent_payload):
    response = client.post("/auth/register/parent", json=parent_payload)
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def parent_token(client, registered_parent, parent_payload):
    response = client.post(
        "/auth/login",
        json={"email": parent_payload["email"], "password": parent_payload["password"]},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def registered_child(client, registered_parent, parent_token, child_payload):
    headers = {"Authorization": f"Bearer {parent_token}"}
    response = client.post("/auth/register/child", json=child_payload, headers=headers)
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def child_token(client, registered_child, child_payload):
    response = client.post(
        "/auth/login",
        json={"email": child_payload["email"], "password": child_payload["password"]},
    )
    assert response.status_code == 200
    return response.json()["access_token"]
