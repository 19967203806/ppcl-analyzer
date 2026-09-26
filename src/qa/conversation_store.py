from ..models.qa import Conversation, Message
from ..models.database import create_db_and_tables
from sqlmodel import Session, select, delete
import uuid
from datetime import datetime


class ConversationStore:
    """DB-backed conversation store scoped by owner."""

    def __init__(self, session: Session, owner_id: int):
        create_db_and_tables()
        self.session = session
        self.owner_id = owner_id

    def _base_query(self):
        return select(Conversation).where(Conversation.owner_id == self.owner_id)

    def list_conversations(self, limit: int = 20) -> list[Conversation]:
        stmt = self._base_query().order_by(Conversation.updated_at.desc()).limit(limit)
        return list(self.session.exec(stmt).all())

    def get(self, conversation_id: str | None) -> Conversation | None:
        if not conversation_id:
            return None
        stmt = self._base_query().where(Conversation.conversation_id == conversation_id)
        return self.session.exec(stmt).first()

    def _create(self, file_id: int | None) -> Conversation:
        new_conv = Conversation(
            conversation_id=str(uuid.uuid4()),
            owner_id=self.owner_id,
            file_id=file_id,
            title="New chat",
            trace_id=str(uuid.uuid4()),
        )
        self.session.add(new_conv)
        self.session.commit()
        self.session.refresh(new_conv)
        return new_conv

    def get_latest_or_create(self, conversation_id: str | None, file_id: int | None) -> Conversation:
        if conversation_id == "new":
            return self._create(file_id)

        convo = self.get(conversation_id)
        if convo:
            return convo

        # when delete conversation_id leading to conversation_id is None, get latest conversation
        latest = self.session.exec(
            self._base_query().order_by(Conversation.updated_at.desc())
        ).first()
        if latest:
            return latest

        return self._create(file_id)

    def get_history(self, conversation_id: str) -> list[dict]:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        messages = self.session.exec(stmt).all()
        return [
            {"role": m.role, "content": m.content, "created_at": m.created_at}
            for m in messages
        ]

    def get_last_message(self, conversation_id: str) -> str | None:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        msg = self.session.exec(stmt).first()
        return msg.content if msg else None

    def append_messages(
        self,
        conversation_id: str,
        messages: list[dict],
        title: str | None = None,
        trace_id: str | None = None,
    ) -> Conversation:
        convo = self.get(conversation_id)
        if not convo:
            raise ValueError("Conversation not found")

        for msg in messages:
            self.session.add(
                Message(
                    conversation_id=conversation_id,
                    role=msg["role"],
                    content=msg["content"],
                )
            )

        convo.updated_at = datetime.utcnow()
        if title:
            convo.title = title
        if trace_id:
            convo.trace_id = trace_id

        self.session.commit()
        self.session.refresh(convo)
        return convo

    def archive(self, conversation_id: str) -> bool:
        convo = self.get(conversation_id)
        if not convo:
            return False
        # Hard delete: remove messages first, then conversation to satisfy FK.
        self.session.exec(delete(Message).where(Message.conversation_id == conversation_id))
        self.session.exec(delete(Conversation).where(Conversation.conversation_id == conversation_id))
        self.session.commit()
        return True
