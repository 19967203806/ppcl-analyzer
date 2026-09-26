from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel
from sqlmodel import Field, Relationship, SQLModel


# ---- SQLModel tables ----


class Conversation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: str = Field(default_factory=lambda: str(uuid4()), unique=True, index=True)
    owner_id: int = Field(index=True)
    file_id: Optional[int] = Field(default=None, index=True)
    title: str = Field(default="New chat")
    trace_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    messages: List["Message"] = Relationship(back_populates="conversation")


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: str = Field(foreign_key="conversation.conversation_id")
    role: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    conversation: Optional[Conversation] = Relationship(back_populates="messages")


# ---- API Schemas ----


class AskRequest(BaseModel):
    question: str
    language: str = "en"
    file_id: Optional[int] = None


class AskResponse(BaseModel):
    answer: str
    usage: dict | None = None


class ChatMessage(BaseModel):
    role: str
    content: str
    created_at: Optional[datetime] = None


class ChatRequest(BaseModel):
    question: str
    language: str = "en"
    selected_docs: List[str] = []
    history: List[ChatMessage] = []
    conversation_id: Optional[str] = None
    file_id: Optional[int] = None


class ConversationSummary(BaseModel):
    id: str
    title: str
    updated_at: datetime
    last_message: Optional[str] = None


class ChatHistoryResponse(BaseModel):
    history: List[ChatMessage] = []
    trace_id: Optional[str] = None
    conversation_id: Optional[str] = None
    conversations: List[ConversationSummary] = []
