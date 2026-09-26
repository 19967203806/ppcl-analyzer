from sqlmodel import select
from fastapi import HTTPException
from ..models import User, SessionDep
from ..utils.security import hash_password, verify_password

class UserRepository:
    @staticmethod
    def get_by_id(session: SessionDep, user_id: int) -> User:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="user not found")
        return user

    @staticmethod
    def get_by_credentials(session: SessionDep, username: str, password: str) -> User | None:
        user = session.exec(select(User).where(User.username == username)).first()
        if not user or not verify_password(password, user.password):
            return None
        if not user.password.startswith("pbkdf2_sha256$"):
            user.password = hash_password(password)
            session.add(user)
            session.commit()
            session.refresh(user)
        return user
