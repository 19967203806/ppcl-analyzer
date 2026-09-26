import uuid
from typing import Iterable, List

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from sqlmodel import Session

from ..repositories.file_repository import FILE_TYPE_MAP, FileRepository
from ..utils.model_factory import create_chat_model, message_text
from . import titlesummary
from .conversation_store import ConversationStore
from .graph import build_qa_graph

class QAChat:
    """LangGraph chat orchestrator with DB-backed product history."""

    def __init__(self, model: BaseChatModel | None = None) -> None:
        self.model = model or create_chat_model()
        self.title_summarizer = titlesummary.TitleSummarizer(self.model)
        self.graph = build_qa_graph(self.model, self.title_summarizer)

    @staticmethod
    def collect_docs(session: Session, file_id: int | None, selected_docs: List[str]) -> dict:
        if not file_id:
            return {}
        if not selected_docs:
            return {}
        doc_keys = selected_docs
        doc_keys = [k for k in doc_keys if k in FILE_TYPE_MAP]
        docs: dict = {}
        for key in doc_keys:
            try:
                path = FileRepository.resolve_path(session, file_id, key)
                docs[key] = path.read_text(encoding="utf-8")
            except Exception:
                continue
        return docs

    @staticmethod
    def build_messages(question: str, language: str, docs: dict, history: List[dict]):
        system_prompt = "你是一位资深PPCL代码专家，基于用户提供的完整上下文回答，不要编造。"
        if language == "en":
            system_prompt = "You are a senior PPCL expert. Answer strictly based on provided artifacts; do not fabricate."

        ordered_keys = [
            "original_code",
            "cleaned_code",
            "logic_blocks",
            "data_points",
            "logic_doc",
            "flowchart_code",
            "sequence_chart_code",
        ]
        doc_blobs = []
        for key in ordered_keys:
            if key in docs:
                doc_blobs.append(f"[{key}]\n{docs[key]}")
        context_blob = "\n\n".join(doc_blobs)

        messages = [SystemMessage(content=system_prompt)]
        if context_blob:
            context_label = "Context" if language == "en" else "上下文"
            messages.append(SystemMessage(content=f"{context_label}:\n{context_blob}"))
        for item in history or []:
            if item["role"] == "assistant":
                messages.append(AIMessage(content=item["content"]))
            elif item["role"] == "user":
                messages.append(HumanMessage(content=item["content"]))
        messages.append(HumanMessage(content=question))
        return messages

    def chat_stream(
        self,
        session: Session,
        owner_id: int,
        question: str,
        language: str,
        selected_docs: List[str],
        conversation_id: str | None,
        file_id: int | None,
    ) -> tuple[Iterable[str], str, str]:
        store = ConversationStore(session=session, owner_id=owner_id)
        conversation = store.get_latest_or_create(conversation_id=conversation_id, file_id=file_id)

        history = store.get_history(conversation.conversation_id)
        docs = self.collect_docs(session, file_id, selected_docs)
        messages = self.build_messages(question, language, docs, history)
        trace_id = conversation.trace_id or str(uuid.uuid4())
        needs_title = (
            conversation.title in (None, "", "New chat")
            or len(history) + 2 <= 4
        )

        def streamer():
            answer_accum: list[str] = []
            final_state = None
            config = {
                "run_name": "qa_chat",
                "tags": ["qa", language],
                "metadata": {
                    "trace_id": trace_id,
                    "conversation_id": conversation.conversation_id,
                    "owner_id": owner_id,
                    "file_id": file_id,
                },
            }
            for part in self.graph.stream(
                {
                    "messages": messages,
                    "needs_title": needs_title,
                    "title": conversation.title or "",
                },
                config=config,
                stream_mode=["messages", "values"],
                version="v2",
            ):
                if part["type"] == "messages":
                    chunk, metadata = part["data"]
                    if metadata.get("langgraph_node") != "answer":
                        continue
                    text = message_text(chunk)
                    if text:
                        answer_accum.append(text)
                        yield text
                elif part["type"] == "values":
                    final_state = part["data"]

            answer = "".join(answer_accum)
            if not answer and final_state:
                generated = final_state["messages"][-1]
                answer = message_text(generated)

            title = (
                final_state.get("title")
                if final_state
                else conversation.title
            )
            title = title or question[:30] or "Chat"

            store.append_messages(
                conversation_id=conversation.conversation_id,
                messages=[
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": answer},
                ],
                title=title,
                trace_id=trace_id,
            )

        return streamer(), trace_id, conversation.conversation_id
