from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from sqlmodel import select

from src.models.qa import Conversation, Message
from src.qa.qa import QAChat


def test_build_messages_orders_context_history_then_question():
    messages = QAChat.build_messages(
        question="current",
        language="en",
        docs={"logic_doc": "DOC"},
        history=[
            {"role": "user", "content": "old question"},
            {"role": "assistant", "content": "old answer"},
        ],
    )

    assert [type(item) for item in messages] == [
        SystemMessage,
        SystemMessage,
        HumanMessage,
        AIMessage,
        HumanMessage,
    ]
    assert messages[-1].content == "current"
    assert "[logic_doc]\nDOC" in messages[1].content


def test_chat_graph_streams_only_answer_and_persists_once(session, users):
    model = FakeListChatModel(responses=["answer", "short title"])
    chat = QAChat(model=model)

    stream, trace_id, conversation_id = chat.chat_stream(
        session=session,
        owner_id=users["alice"].id,
        question="question",
        language="en",
        selected_docs=[],
        conversation_id="new",
        file_id=None,
    )

    assert "".join(stream) == "answer"
    messages = session.exec(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    ).all()
    conversation = session.exec(
        select(Conversation).where(
            Conversation.conversation_id == conversation_id
        )
    ).one()
    assert [(item.role, item.content) for item in messages] == [
        ("user", "question"),
        ("assistant", "answer"),
    ]
    assert conversation.title == "short title"
    assert conversation.trace_id == trace_id
