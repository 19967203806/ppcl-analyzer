from typing import Generator, Annotated
from sqlmodel import Session
from fastapi import Depends
from .database import engine

def get_session() -> Generator[Session, None, None]:
    # Generator[YieldType, SendType, ReturnType]
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]