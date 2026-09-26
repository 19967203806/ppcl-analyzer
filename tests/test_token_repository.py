from datetime import datetime, timedelta

from src.models.auth_token import AuthToken
from src.repositories.token_repository import TokenRepository
from src.utils.security import hash_token


def test_issue_stores_hash_not_plaintext(session, users):
    token = TokenRepository.issue(session, users["alice"].id)
    stored = session.get(AuthToken, 1)
    assert stored.token_hash == hash_token(token)
    assert stored.token_hash != token


def test_get_valid_user_id_returns_owner(session, users):
    token = TokenRepository.issue(session, users["alice"].id)
    assert TokenRepository.get_valid_user_id(session, token) == users["alice"].id


def test_get_valid_user_id_rejects_unknown_and_expired(session, users):
    assert TokenRepository.get_valid_user_id(session, "nope") is None
    expired = AuthToken(
        token_hash=hash_token("old"),
        user_id=users["alice"].id,
        expires_at=datetime.utcnow() - timedelta(hours=1),
    )
    session.add(expired)
    session.commit()
    assert TokenRepository.get_valid_user_id(session, "old") is None


def test_revoke_removes_token(session, users):
    token = TokenRepository.issue(session, users["alice"].id)
    TokenRepository.revoke(session, token)
    assert TokenRepository.get_valid_user_id(session, token) is None
