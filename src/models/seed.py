import os

from loguru import logger
from sqlmodel import select

from .user import User
from .deps import SessionDep
from ..utils.security import hash_password


def _bootstrap_credentials() -> tuple[str, str] | None:
    username = os.getenv("BOOTSTRAP_USERNAME", "").strip()
    password = os.getenv("BOOTSTRAP_PASSWORD", "")

    if not username and not password:
        return None
    if not username or not password:
        raise RuntimeError(
            "BOOTSTRAP_USERNAME and BOOTSTRAP_PASSWORD must be set together"
        )
    if len(password) < 12:
        raise RuntimeError("BOOTSTRAP_PASSWORD must contain at least 12 characters")
    return username, password


def init_users(session: SessionDep) -> None:
    credentials = _bootstrap_credentials()
    if credentials is None:
        if session.exec(select(User)).first() is None:
            logger.warning(
                "No user exists. Set BOOTSTRAP_USERNAME and BOOTSTRAP_PASSWORD, "
                "then restart the API to create the first local account."
            )
        return

    username, password = credentials
    existing = session.exec(select(User).where(User.username == username)).first()
    if existing:
        return

    session.add(User(username=username, password=hash_password(password)))
    session.commit()
    logger.warning(
        "Created bootstrap user '{}'. Replace the local demo credentials before "
        "any network-accessible deployment.",
        username,
    )
