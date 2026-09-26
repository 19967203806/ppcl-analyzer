from typing import Annotated

from fastapi import Depends, Header, HTTPException

from .models import File, SessionDep, User
from .repositories.file_repository import FileRepository
from .repositories.token_repository import TokenRepository
from .repositories.user_repository import UserRepository


def get_current_user(
    session: SessionDep,
    authorization: str | None = Header(default=None),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="not authenticated")
    token = authorization.split(" ", 1)[1].strip()
    user_id = TokenRepository.get_valid_user_id(session, token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="invalid or expired token")
    return UserRepository.get_by_id(session, user_id)


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_owned_file(session: SessionDep, file_id: int, current_user: User) -> File:
    try:
        record = FileRepository.get(session, file_id)
    except HTTPException as exc:
        if exc.status_code == 404:
            raise HTTPException(status_code=404, detail="file not found")
        raise
    if record.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="file not found")
    return record
