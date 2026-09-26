import streamlit as st
from ..state.session_manager import SessionManager
from ..services.qa_service import QAService

DOC_OPTIONS = [
    ("Original Code", "original_code"),
    ("Cleaned Code", "cleaned_code"),
    ("Logic Blocks", "logic_blocks"),
    ("Data Points", "data_points"),
    ("Logic Doc", "logic_doc"),
    ("Flowchart Source", "flowchart_code"),
    ("Sequence Source", "sequence_chart_code"),
]


def _load_history(qa: QAService, conversation_id: str | None = None):
    file_id = SessionManager.get_current_file_id() or None
    data = qa.fetch_history(conversation_id=conversation_id, file_id=file_id)
    SessionManager.set_ai_history(data.get("history", []))
    SessionManager.set_conversation_id(data.get("conversation_id"))
    SessionManager.set_conversations(data.get("conversations", []))


def _render_sidebar_history(qa: QAService):
    with st.sidebar:
        # Style the "New Chat" button with a light green background and bold white text.
        st.subheader("Conversations List")
        conversations = SessionManager.get_conversations()
        current = SessionManager.get_conversation_id()

        if st.button("➕ New Chat", key="new_chat_top"):
            SessionManager.set_conversation_id("new")
            SessionManager.clear_ai_history()
            st.rerun()

        if not conversations:
            st.caption("No previous chats")
        else:
            for t in conversations:
                title = t.get("title") or t.get("id", "")[:16]
                is_active = current == t.get("id")
                select_col, del_col = st.columns([4, 1])
                with select_col:
                    if st.button(f"{'🟢' if is_active else '⚪'} {title}", key=f"thread_{t.get('id')}"):
                        SessionManager.set_conversation_id(t.get("id"))
                        SessionManager.clear_ai_history()
                        st.rerun()
                with del_col:
                    if st.button("🗑️", key=f"del_{t.get('id')}"):
                        qa.delete_conversation(t.get("id"))
                        if SessionManager.get_conversation_id() == t.get("id"):
                            SessionManager.set_conversation_id(None)
                        SessionManager.clear_ai_history()
                        SessionManager.clear_conversations()
                        st.rerun()


def _doc_selector():
    st.caption("Context to send (defaults to all available from the current file, if any)")
    selected = []
    cols = st.columns(3)
    for idx, (label, value) in enumerate(DOC_OPTIONS):
        with cols[idx % len(cols)]:
            if st.checkbox(label, value=True, key=f"doc_{value}"):
                selected.append(value)
    return selected


def _render_chat_messages():
    for msg in SessionManager.get_ai_history():
        role = msg.get("role", "assistant")
        content = msg.get("content", "")
        with st.chat_message("assistant" if role not in ["user", "assistant"] else role):
            st.markdown(content)


def render_ai_chat_page():
    st.title("🤖 AI Assistant")
    qa = QAService()
    conversation_id = SessionManager.get_conversation_id()
    if not SessionManager.get_ai_history() or not SessionManager.get_conversations():
        _load_history(qa, conversation_id)
    _render_sidebar_history(qa)

    st.markdown("---")
    _render_chat_messages()

    st.markdown("---")
    selected_docs = _doc_selector()

    user_input = st.chat_input("please enter your question here...")
    if user_input:
        if not SessionManager.has_ai_history():
            SessionManager.set_ai_history([])
        history = SessionManager.get_ai_history()
        history.append({"role": "user", "content": user_input})
        SessionManager.set_ai_history(history)
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            answer_parts: list[str] = []
            stream, new_thread_id = qa.chat_stream(
                question=user_input,
                selected_docs=selected_docs,
                conversation_id=SessionManager.get_conversation_id(),
                file_id=SessionManager.get_current_file_id() or None,
            )
            if not stream:
                st.error("response error, please try again later.")
                return
            for chunk in stream:
                if chunk:
                    answer_parts.append(chunk)
                    placeholder.markdown("".join(answer_parts))
            assistant_msg = "".join(answer_parts)
        history = SessionManager.get_ai_history()
        history.append({"role": "assistant", "content": assistant_msg})
        SessionManager.set_ai_history(history)
        if new_thread_id:
            SessionManager.set_conversation_id(new_thread_id)
        # refresh threads and history from backend to keep sidebar in sync
        _load_history(qa, SessionManager.get_conversation_id())
        st.rerun()
