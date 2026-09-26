from typing import Iterable, List, Tuple

from fastapi import HTTPException

from ..models import SessionDep
from ..models.qa import ChatMessage
from ..qa.qa import ConversationStore, QAChat
from ..repositories.qa_repository import QARepository



class QAService:
    @staticmethod
    def delete_conversation(session: SessionDep, owner_id: int, conversation_id: str) -> dict:
        store = ConversationStore(session=session, owner_id=owner_id)
        deleted = store.archive(conversation_id)
        return {"deleted": deleted}

    @staticmethod
    def load_history(session: SessionDep, owner_id: int, conversation_id: str | None = None, file_id: int | None = None):
        store = ConversationStore(session=session, owner_id=owner_id)
        conversation = store.get_latest_or_create(conversation_id=conversation_id, file_id=file_id)
        raw_history = store.get_history(conversation.conversation_id)
        history = [
            {
                "role": item["role"],
                "content": item["content"],
                "created_at": item.get("created_at").isoformat() if item.get("created_at") else None,
            }
            for item in raw_history
        ]
        conversations = store.list_conversations()
        summaries = [
            {
                "id": c.conversation_id,
                "title": c.title or "Chat",
                "last_message": store.get_last_message(c.conversation_id),
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in conversations
        ]
        return history, conversation.trace_id, summaries, conversation.conversation_id

    @staticmethod
    def chat_stream(
        session: SessionDep,
        owner_id: int,
        question: str,
        language: str,
        selected_docs: List[str],
        conversation_id: str | None,
        file_id: int | None,
    ) -> Tuple[Iterable[str], str, str]:
        if not question.strip():
            raise HTTPException(status_code=400, detail="question is empty")
        if file_id:
            QARepository.ensure_owner(session, file_id, owner_id)

        qa_chat = QAChat()
        return qa_chat.chat_stream(
            session=session,
            owner_id=owner_id,
            question=question,
            language=language,
            selected_docs=selected_docs,
            conversation_id=conversation_id,
            file_id=file_id,
        )