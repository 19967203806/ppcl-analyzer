import pytest
from sqlmodel import select

from src.models import User
from src.models.seed import init_users
from src.utils.security import verify_password


def _clear_bootstrap_environment(monkeypatch):
    monkeypatch.delenv("BOOTSTRAP_USERNAME", raising=False)
    monkeypatch.delenv("BOOTSTRAP_PASSWORD", raising=False)


def test_init_users_does_not_create_hardcoded_accounts(session, monkeypatch):
    _clear_bootstrap_environment(monkeypatch)

    init_users(session)

    assert session.exec(select(User)).all() == []


def test_init_users_creates_configured_bootstrap_account(session, monkeypatch):
    monkeypatch.setenv("BOOTSTRAP_USERNAME", "local-admin")
    monkeypatch.setenv("BOOTSTRAP_PASSWORD", "example-password-123")

    init_users(session)

    users = session.exec(select(User)).all()
    assert len(users) == 1
    assert users[0].username == "local-admin"
    assert verify_password("example-password-123", users[0].password)


def test_init_users_adds_bootstrap_account_when_other_users_exist(
    session, monkeypatch
):
    session.add(User(username="existing-user", password="existing-password"))
    session.commit()
    monkeypatch.setenv("BOOTSTRAP_USERNAME", "local-admin")
    monkeypatch.setenv("BOOTSTRAP_PASSWORD", "example-password-123")

    init_users(session)

    usernames = {user.username for user in session.exec(select(User)).all()}
    assert usernames == {"existing-user", "local-admin"}


def test_init_users_does_not_replace_existing_password(session, monkeypatch):
    session.add(User(username="local-admin", password="original-password"))
    session.commit()
    monkeypatch.setenv("BOOTSTRAP_USERNAME", "local-admin")
    monkeypatch.setenv("BOOTSTRAP_PASSWORD", "different-password-123")

    init_users(session)

    user = session.exec(select(User).where(User.username == "local-admin")).one()
    assert user.password == "original-password"


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("local-admin", ""),
        ("", "example-password-123"),
        ("local-admin", "too-short"),
    ],
)
def test_init_users_rejects_incomplete_or_weak_credentials(
    session, monkeypatch, username, password
):
    monkeypatch.setenv("BOOTSTRAP_USERNAME", username)
    monkeypatch.setenv("BOOTSTRAP_PASSWORD", password)

    with pytest.raises(RuntimeError):
        init_users(session)

    assert session.exec(select(User)).all() == []
