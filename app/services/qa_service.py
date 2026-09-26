from typing import Optional, Dict, Iterable, List

from .api_client import APIClient
from ..state.session_manager import SessionManager
from ..config import API_TIMEOUTS


class QAService:
    def __init__(self):
        self.client = APIClient()

    def chat_stream(
        self,
        question: str,
        selected_docs: Optional[List[str]] = None,
        conversation_id: Optional[str] = None,
        file_id: Optional[int] = None,
    ) -> tuple[Iterable[str], Optional[str]]:
        language = SessionManager.get_language()
        payload = {
            "question": question,
            "language": language,
            "selected_docs": selected_docs or [],
            "conversation_id": conversation_id,
            "file_id": file_id,
        }
        response = self.client.post(
            "/qa/chat",
            json=payload,
            timeout=API_TIMEOUTS.get("long", 600),
            stream=True,
        )
        if response is not None and response.status_code == 429:
            try:
                detail = response.json().get("detail")
            except Exception:
                detail = None
            return iter([f"⚠️ {detail or 'Daily chat limit reached.'}"]), None
        if not response or response.status_code != 200:
            return [], None
        
        # backend returns Conversation-Id when it creates or reuses a conversation
        conv_id = response.headers.get("Conversation-Id") if response.headers else None
        return response.iter_content(chunk_size=None, decode_unicode=True), conv_id

    def fetch_history(self, conversation_id: Optional[str] = None, file_id: Optional[int] = None) -> Dict:
        resp = self.client.get(
            "/qa/history",
            params={"conversation_id": conversation_id, "file_id": file_id},
            timeout=API_TIMEOUTS.get("default", 60),
        )
        if resp and resp.status_code == 200:
            data = resp.json()
            return data
        return {}

    def delete_conversation(self, conversation_id: str) -> bool:
        resp = self.client.delete(
            "/qa/conversation",
            params={"conversation_id": conversation_id},
            timeout=API_TIMEOUTS.get("default", 60),
        )
        return bool(resp and resp.status_code == 200 and resp.json().get("deleted"))
