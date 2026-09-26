from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class UsageEvent(SQLModel, table=True):
    """One model-backed request (analysis or chat), used for daily quotas."""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    kind: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
