import os
from datetime import datetime, timedelta

from sqlmodel import select

from ..models import SessionDep
from ..models.auth_token import AuthToken
from ..utils.security import generate_token, hash_token


def _ttl_hours() -> int:
    try:
        return int(os.getenv("AUTH_TOKEN_TTL_HOURS", "168"))
    except ValueError:
        return 168


class TokenRepository:
    @staticmethod
    def issue(session: SessionDep, user_id: int) -> str:
        token = generate_token()
        record = AuthToken(
            token_hash=hash_token(token),
            user_id=user_id,
            expires_at=datetime.utcnow() + timedelta(hours=_ttl_hours()),
        )
        session.add(record)
        session.commit()
        return token

    @staticmethod
    def get_valid_user_id(session: SessionDep, token: str) -> int | None:
        record = session.exec(
            select(AuthToken).where(AuthToken.token_hash == hash_token(token))
        ).first()
        if not record or record.expires_at < datetime.utcnow():
            return None
        return record.user_id

    @staticmethod
    def revoke(session: SessionDep, token: str) -> None:
        record = session.exec(
            select(AuthToken).where(AuthToken.token_hash == hash_token(token))
        ).first()
        if record:
            session.delete(record)
            session.commit()
