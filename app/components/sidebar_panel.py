import streamlit as st
from ..services.file_service import FileService
from ..state.session_manager import SessionManager
from ..config import LANGUAGES, OUTPUT_TYPES
from .flowchart_viewer import render_browser_downloads

_BROWSER_RENDERED_PDF_WARNINGS = {
    "flowchart PDF was not generated; DOT source is available",
    "sequence chart PDF was not generated; Mermaid source is available",
}


def _display_status(file_details: dict) -> str:
    status = file_details.get("status", "unknown")
    remaining_warnings = [
        line
        for line in (file_details.get("error_message") or "").splitlines()
        if line and line not in _BROWSER_RENDERED_PDF_WARNINGS
    ]
    if status == "completed_with_warnings" and not remaining_warnings:
        return "completed"
    return status


def render_sidebar_panel() -> None:
    """render sidebar panel"""
    with st.sidebar:
        st.header("⚙️ Output file language")

        language = st.selectbox(
            label="select output language",
            options=list(LANGUAGES.keys()),
            format_func=lambda x: LANGUAGES[x],
            help="select the language of the output",
            index=list(LANGUAGES.keys()).index(SessionManager.get_language()),
            key="output_language_select",
        )

        if SessionManager.get_language() != language:
            SessionManager.set_language(language)
            SessionManager.set_current_file(None, None)
        
        render_file_manager()
        
        st.markdown("---")
        render_usage_instructions()
        
        return language


def render_file_manager():
    """render file manager panel"""
    file_service = FileService()

    # Fetch files if not in session state
    if not SessionManager.get_user_files():
        # here return list of filedetails
        SessionManager.set_user_files(file_service.get_user_files())
    
    if SessionManager.get_user_files():
        st.markdown("### 📁 My Files")
        files = SessionManager.get_user_files()
        options = {f["id"]: f for f in files}
        current_file_id = SessionManager.get_current_file_id()
        option_ids = [None] + list(options)
        selected_index = (
            option_ids.index(current_file_id)
            if current_file_id in options
            else 0
        )
        selected_file_id = st.selectbox(
            "history upload file",
            option_ids,
            index=selected_index,
            format_func=lambda file_id: (
                "Select a file"
                if file_id is None
                else (
                    f"{options[file_id]['filename']} · "
                    f"{options[file_id].get('language', 'en')} · "
                    f"{_display_status(options[file_id])} · #{file_id}"
                )
            ),
            key=f"history_upload_file_{current_file_id or 'none'}",
        )

        if selected_file_id is not None and selected_file_id != current_file_id:
            chosen_file = options[selected_file_id]
            SessionManager.set_current_file(chosen_file["id"], chosen_file)
            st.rerun()

        if SessionManager.get_current_file_id():
            current = st.session_state.get(SessionManager.FILE_DETAILS) or {}
            status = _display_status(current)
            st.caption(f"Current file id: {SessionManager.get_current_file_id()} · {status}")
            render_download_panel(file_service)
            render_delete_panel(file_service)


def render_download_panel(file_service: FileService):
    """render download panel"""
    st.markdown("### 📥 Download")
    file_id = SessionManager.get_current_file_id()
    file_details = st.session_state.get(SessionManager.FILE_DETAILS) or {}

    # File type selection: logic_blocks, logic_doc, data_points, flowchart
    type_labels = {
        "logic_blocks": "📝 Logic Blocks",
        "logic_doc": "📖 Logic Document",
        "data_points": "📊 Data Points",
        "flowchart": "🔄 Flowchart",
        "sequence_chart": "⛓️ Sequence Chart",
    }
    selected_type = st.selectbox(
        "Select a file type",
        options=list(type_labels.keys()),
        format_func=lambda k: type_labels[k],
        key="download_type_select",
    )

    st.markdown("#### Available downloads")

    if selected_type in {"logic_blocks", "data_points", "logic_doc"}:
        if not file_details.get(f"{selected_type}_path"):
            st.caption("This artifact is not available for the current analysis run.")
            return
        col_md, col_pdf = st.columns(2)
        with col_md:
            md_bytes = file_service.download_file(file_id, selected_type)
            if md_bytes:
                st.download_button(
                    label=f"Download Markdown (.md)",
                    data=md_bytes,
                    file_name=f"{selected_type}.md",
                    mime="text/markdown",
                    key=f"sidebar_dl_btn_{selected_type}_md_{file_id}",
                )
        with col_pdf:
            pdf_bytes = file_service.download_file(file_id, f"{selected_type}_pdf")
            if pdf_bytes:
                st.download_button(
                    label=f"Download PDF (.pdf)",
                    data=pdf_bytes,
                    file_name=f"{selected_type}.pdf",
                    mime="application/pdf",
                    key=f"sidebar_dl_btn_{selected_type}_pdf_{file_id}",
                )
    elif selected_type in {"flowchart", "sequence_chart"}:
        is_sequence = selected_type == "sequence_chart"
        source_type = "sequence_chart_code" if is_sequence else "flowchart_code"
        source_ext = "mmd" if is_sequence else "dot"
        has_server_pdf = bool(file_details.get(f"{selected_type}_path"))
        has_source = bool(file_details.get(f"{source_type}_path"))
        if has_server_pdf:
            col_pdf, col_source = st.columns(2)
            with col_pdf:
                content_pdf = file_service.download_file(file_id, selected_type)
                if content_pdf:
                    st.download_button(
                        label=f"Download {'Sequence Chart' if is_sequence else 'Flowchart'} PDF",
                        data=content_pdf,
                        file_name=f"{selected_type}.pdf",
                        mime="application/pdf",
                        key=f"sidebar_dl_btn_{selected_type}_pdf_{file_id}",
                    )
            with col_source:
                content_source = file_service.download_file(file_id, source_type)
                if content_source:
                    st.download_button(
                        label=f"Download Source (.{source_ext})",
                        data=content_source,
                        file_name=f"{selected_type}.{source_ext}",
                        mime="text/plain",
                        key=f"sidebar_dl_btn_{source_type}_{file_id}",
                    )
        elif has_source:
            code = (
                file_service.get_sequence_chart_code(file_id)
                if is_sequence
                else file_service.get_flowchart_code(file_id)
            )
            if code:
                render_browser_downloads(code, selected_type)
            content_source = file_service.download_file(file_id, source_type)
            if content_source:
                st.download_button(
                    label=f"Download Source (.{source_ext})",
                    data=content_source,
                    file_name=f"{selected_type}.{source_ext}",
                    mime="text/plain",
                    key=f"sidebar_dl_btn_{source_type}_{file_id}",
                    use_container_width=True,
                )
        else:
            st.caption("Source is not available.")


def render_delete_panel(file_service: FileService):
    """render delete panel"""
    st.markdown("### 🗑️ Delete File")
    with st.expander("Delete the selected file and all its analysis results"):
        st.warning("⚠️ Warning: This action is irreversible.")
        if st.button("Delete File", type="primary"):
            if file_service.delete_file(SessionManager.get_current_file_id()):
                # Reset file state and rerun
                SessionManager.set_user_files([])
                SessionManager.set_current_file(None, None)
                st.rerun()


def render_usage_instructions():
    st.markdown("### 💡 Usage Instructions")
    st.info("""
    1. Upload PPCL code file
    2. The system automatically analyzes the code structure
    3. View the generated flowchart and documents
    4. (Optional) Download the required analysis results
    """)
