import pytest
from fastapi import HTTPException

from src.dependencies import get_current_user, get_owned_file
from src.models import File
from src.repositories.token_repository import TokenRepository


def test_get_current_user_resolves_token(session, users):
    token = TokenRepository.issue(session, users["alice"].id)
    user = get_current_user(session=session, authorization=f"Bearer {token}")
    assert user.id == users["alice"].id


def test_get_current_user_rejects_missing_and_bad(session, users):
    with pytest.raises(HTTPException) as e1:
        get_current_user(session=session, authorization=None)
    assert e1.value.status_code == 401
    with pytest.raises(HTTPException) as e2:
        get_current_user(session=session, authorization="Bearer nope")
    assert e2.value.status_code == 401


def test_get_owned_file_enforces_ownership(session, users):
    f = File(filename="a.ppcl", storage_path="output/x", owner_id=users["alice"].id)
    session.add(f)
    session.commit()
    session.refresh(f)
    assert get_owned_file(session, f.id, users["alice"]).id == f.id
    with pytest.raises(HTTPException) as e:
        get_owned_file(session, f.id, users["bob"])
    assert e.value.status_code == 404


def test_get_owned_file_missing_file_returns_404(session, users):
    with pytest.raises(HTTPException) as e:
        get_owned_file(session, 999999, users["alice"])
    assert e.value.status_code == 404
