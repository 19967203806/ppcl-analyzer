from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
if TYPE_CHECKING:
    from .user import User

class FileBase(SQLModel):
    filename: str = Field(index=True)
    storage_path: str

class File(FileBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id")
    language: str = Field(default="en", index=True)
    status: str = Field(default="pending", index=True)
    input_hash: Optional[str] = Field(default=None, index=True)
    model_provider: Optional[str] = None
    error_message: Optional[str] = None
    original_code_path: Optional[str] = None
    cleaned_code_path: Optional[str] = None
    logic_blocks_path: Optional[str] = None
    data_points_path: Optional[str] = None
    logic_doc_path: Optional[str] = None
    flowchart_path: Optional[str] = None
    flowchart_code_path: Optional[str] = None
    sequence_chart_path: Optional[str] = None
    sequence_chart_code_path: Optional[str] = None
    prompt_tokens: Optional[int] = 0
    completion_tokens: Optional[int] = 0
    total_tokens: Optional[int] = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    owner: "User" = Relationship(back_populates="files")

class FilePublic(FileBase):
    id: int
    owner_id: int
    language: str
    status: str
