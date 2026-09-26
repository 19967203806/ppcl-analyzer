import streamlit as st
from ..state.session_manager import SessionManager
from ..services.file_service import FileService

def render_comment_box(file_service: FileService, file_type: str):
    """Render a comment box below the flowchart."""
    st.markdown("### 💬 Comments")
    st.subheader("Feedback & Comments")
    file_id = SessionManager.get_current_file_id()
    user_id = SessionManager.get_user_id()

    comment = st.text_area(f"Leave your comment if anything you think it's wrong or could be improved.", key=f"comment_{file_type}")
    if st.button(f"Submit Comment for {file_type}", key=f"submit_comment_{file_type}"):
        if comment.strip():
            FileService().save_comment(file_id=file_id, file_type=file_type, comment=comment.strip())
            st.success("Comment submitted successfully!")
        else:
            st.error("Comment cannot be empty.")