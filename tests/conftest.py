import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from src.backend import app
from src.models import User
from src.models.deps import get_session
from src.utils.security import hash_password


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session):
    app.dependency_overrides[get_session] = lambda: session
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="users")
def users_fixture(session):
    alice = User(username="alice", password=hash_password("alice-pw"))
    bob = User(username="bob", password=hash_password("bob-pw"))
    session.add(alice)
    session.add(bob)
    session.commit()
    session.refresh(alice)
    session.refresh(bob)
    return {"alice": alice, "bob": bob}
