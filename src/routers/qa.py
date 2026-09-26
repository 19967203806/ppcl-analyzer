from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.encoders import jsonable_encoder

from ..models import SessionDep
from ..models.qa import ChatRequest, ChatHistoryResponse
from ..dependencies import CurrentUser, get_owned_file
from ..services.qa_service import QAService
from ..services.quota_service import QuotaService

router = APIRouter(tags=["qa"], prefix="/qa")


@router.post("/chat", response_class=StreamingResponse)
def chat(session: SessionDep, current_user: CurrentUser, payload: ChatRequest):
    if payload.file_id is not None:
        get_owned_file(session, payload.file_id, current_user)
    QuotaService.consume(session, current_user.id, "chat")
    stream, trace_id, conversation_id = QAService.chat_stream(
        session=session,
        owner_id=current_user.id,
        question=payload.question,
        language=payload.language,
        selected_docs=payload.selected_docs,
        conversation_id=payload.conversation_id,
        file_id=payload.file_id,
    )
    headers = {"Trace-Id": trace_id, "Conversation-Id": conversation_id or ""}
    return StreamingResponse(stream, media_type="text/plain", headers=headers)


@router.get("/history", response_model=ChatHistoryResponse)
def history(session: SessionDep, current_user: CurrentUser, conversation_id: str | None = None, file_id: int | None = None):
    history, trace_id, threads, active_conversation_id = QAService.load_history(
        session=session, owner_id=current_user.id,
        conversation_id=conversation_id, file_id=file_id,
    )
    payload = ChatHistoryResponse(
        history=history, trace_id=trace_id,
        conversation_id=active_conversation_id, conversations=threads,
    )
    return JSONResponse(content=jsonable_encoder(payload))


@router.delete("/conversation")
def delete_conversation(session: SessionDep, current_user: CurrentUser, conversation_id: str):
    result = QAService.delete_conversation(session=session, owner_id=current_user.id, conversation_id=conversation_id)
    return JSONResponse(content=result)
