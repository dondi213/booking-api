import os

os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-32-bytes-long"
os.environ["DATABASE_URL"] = "sqlite://"

from datetime import UTC, datetime, timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402

test_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def db():
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture()
def client():
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def register_and_login(client, email, password="secret123", admin=False):
    client.post("/auth/register", json={"email": email, "password": password})
    if admin:
        with TestingSessionLocal() as session:
            user = session.scalar(select(User).where(User.email == email))
            user.is_admin = True
            session.commit()
    token = client.post("/auth/login", data={"username": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def user_headers(client):
    return register_and_login(client, "ana@example.com")


@pytest.fixture()
def other_headers(client):
    return register_and_login(client, "luis@example.com")


@pytest.fixture()
def admin_headers(client):
    return register_and_login(client, "admin@example.com", admin=True)


@pytest.fixture()
def room(client, admin_headers):
    res = client.post("/resources", json={"name": "Room A", "capacity": 6}, headers=admin_headers)
    return res.json()


def slot(day_offset=1, hour=10, minutes=60):
    """A future time slot as ISO strings with timezone, e.g. tomorrow 10:00-11:00 UTC."""
    base = (datetime.now(UTC) + timedelta(days=day_offset)).replace(hour=hour, minute=0, second=0, microsecond=0)
    return base.isoformat(), (base + timedelta(minutes=minutes)).isoformat()
