from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    # Avoid circular import issues by only importing for type checking
    from .file import File

class UserBase(SQLModel):
    username: str = Field(unique=True, index=True)

class User(UserBase, table=True):     
    id: int | None = Field(default=None, primary_key=True)
    password: str
    files: List["File"] = Relationship(back_populates="owner")

class UserPublic(UserBase):
    id: int