from datetime import datetime
from sqlmodel import SQLModel, Field, Column

class Comment(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id")
    file_id: int = Field(foreign_key="file.id")
    file_type: str = Field(index=True)
    comment: str = Field(nullable=False)
    created_at: datetime = Field(default_factory=datetime.now)