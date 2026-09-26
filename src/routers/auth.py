from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from ..models import UserPublic, SessionDep
from ..services.auth_service import AuthService

router = APIRouter(tags=["users"], prefix="/users")


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    status: str
    message: str
    user: UserPublic | None = None
    token: str | None = None


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    return authorization.split(" ", 1)[1].strip()


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, session: SessionDep):
    result = AuthService.login(session, payload.username, payload.password)
    return LoginResponse(**result)


@router.post("/logout")
def logout(session: SessionDep, authorization: str | None = Header(default=None)):
    return AuthService.logout(session, _bearer_token(authorization))
