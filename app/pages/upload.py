import streamlit as st
from ..services.file_service import FileService
from ..state.session_manager import SessionManager
from ..config import SUPPORTED_FILE_TYPES

def render_upload_page():
    """render upload page"""
    file_service = FileService()

    if st.session_state.get("processing", False):
        with st.spinner("Analyzing code... Please wait 3-10 minutes"):
            uploaded_file = SessionManager.get_uploaded_file()
            language = SessionManager.get_language()
            
            upload_details = file_service.upload_file(uploaded_file, language, overwrite=True)

            if upload_details and upload_details.get("status") in {"completed", "completed_with_warnings"}:
                SessionManager.set_current_file(upload_details.get("file_id"), upload_details.get("file", upload_details))
                SessionManager.set_user_files(file_service.get_user_files())
                if upload_details.get("status") == "completed":
                    st.success("✅ Analysis completed!")
                else:
                    st.warning("Analysis completed with warnings. Check the result details.")
            else:
                error_msg = upload_details.get("message", "❌ Analysis failed") if upload_details else "❌ Analysis failed"
                st.error(error_msg)
            
            SessionManager.set_processing(False)
            # Clear uploaded file after processing  
            SessionManager.set_uploaded_file(None)
            st.rerun()

    # if not processing, show upload widget
    with st.container():
        st.header("📤 Upload PPCL Code File")
        
        uploaded_file = st.file_uploader(
            label="Select PPCL code file",
            type=SUPPORTED_FILE_TYPES,
            help="upload PPCL code file"
        )

        if uploaded_file:
            previous_upload_name = st.session_state.get("last_upload_widget_name")
            if previous_upload_name != uploaded_file.name and SessionManager.get_current_file_id():
                SessionManager.set_current_file(None, None)
            st.session_state["last_upload_widget_name"] = uploaded_file.name
            st.success(f"uploaded file successfully: {uploaded_file.name}")
            st.caption(
                "点击 Start Analysis 才会重新分析。若同名文件已存在，会替换旧结果。"
            )
            
            if st.button("🚀 Start Analysis", type="primary"):
                SessionManager.set_uploaded_file(uploaded_file)
                SessionManager.set_processing(True)
                st.rerun()
