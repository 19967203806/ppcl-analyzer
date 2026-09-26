from fastapi import HTTPException
from ..repositories.user_repository import UserRepository
from ..repositories.token_repository import TokenRepository
from ..models import UserPublic, SessionDep

class AuthService:
    @staticmethod
    def login(session: SessionDep, username: str, password: str) -> dict:
        user = UserRepository.get_by_credentials(session, username, password)
        if not user:
            return {"status": "error", "message": "username or password incorrect", "user": None, "token": None}
        token = TokenRepository.issue(session, user.id)
        return {
            "status": "success",
            "message": "login successful",
            "user": UserPublic(id=user.id, username=user.username),
            "token": token,
        }

    @staticmethod
    def logout(session: SessionDep, token: str) -> dict:
        TokenRepository.revoke(session, token)
        return {"status": "success"}
