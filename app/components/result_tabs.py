import streamlit as st
import re
from ..services.file_service import FileService
from ..state.session_manager import SessionManager
from .flowchart_viewer import render_flowchart, render_sequence_chart
from .render_comment_box import render_comment_box


_BROWSER_RENDERED_PDF_WARNINGS = {
    "flowchart PDF was not generated; DOT source is available",
    "sequence chart PDF was not generated; Mermaid source is available",
}


def _visible_analysis_warnings(error_message: str | None) -> list[str]:
    return [
        line
        for line in (error_message or "").splitlines()
        if line and line not in _BROWSER_RENDERED_PDF_WARNINGS
    ]


def _render_generated_markdown(content: str) -> None:
    safe_content = content.replace("\x00", "")
    code_span_re = re.compile(r"(```.*?```|`[^`\n]*`)", re.DOTALL)
    parts = code_span_re.split(safe_content)
    safe_content = "".join(
        part if code_span_re.fullmatch(part) else re.sub(r"(?<!\\)\$", r"\\$", part)
        for part in parts
    )
    st.markdown(safe_content)


def render_result_tabs():
    """render result tabs"""
    if not st.session_state.get(SessionManager.FILE_ID):
        return
    
    st.markdown("---")
    st.header("📋 Analysis Results")
    file_details = st.session_state.get(SessionManager.FILE_DETAILS) or {}
    if file_details:
        hash_value = file_details.get("input_hash") or ""
        visible_warnings = _visible_analysis_warnings(
            file_details.get("error_message")
        )
        display_status = file_details.get("status", "unknown")
        if display_status == "completed_with_warnings" and not visible_warnings:
            display_status = "completed"
        meta = [
            file_details.get("filename", "unknown"),
            f"status: {display_status}",
            f"language: {file_details.get('language', 'unknown')}",
            f"model: {file_details.get('model_provider', 'unknown')}",
            f"tokens: {file_details.get('total_tokens', 0)}",
        ]
        if hash_value:
            meta.append(f"hash: {hash_value[:12]}")
        st.caption(" · ".join(meta))
        if file_details.get("status") == "failed":
            st.error(file_details.get("error_message") or "Analysis failed")
            return
        if (
            file_details.get("status") == "completed_with_warnings"
            and visible_warnings
        ):
            st.warning("\n".join(visible_warnings))
    
    tab_names = [
        "🔄 Flowchart",
        "⛓️ Sequence Chart",
        "📝 Logic Blocks",
        "📊 Data Points",
        "📖 Logic Document",
    ]

    selected = st.radio(
        "视图",
        tab_names,
        horizontal=True,
        key="result_tab_selector",
        label_visibility="collapsed",
    )

    file_service = FileService()
    file_id = SessionManager.get_current_file_id()

    # Flowchart
    if selected == "🔄 Flowchart":
        st.subheader("Graphviz Flowchart")
        render_flowchart(file_service=file_service, file_id=file_id)
        render_comment_box(
            file_service=file_service,
            file_type="flowchart",
        )

    # Sequence Chart (Mermaid)
    elif selected == "⛓️ Sequence Chart":
        st.subheader("Mermaid Sequence Chart")
        render_sequence_chart(file_service=file_service, file_id=file_id)
        render_comment_box(
            file_service=file_service,
            file_type="sequence_chart",
        )

    else:
        name_to_meta = {
            "📝 Logic Blocks": ("logic_blocks", "Logic Blocks Analysis"),
            "📊 Data Points": ("data_points", "Data Points Document"),
            "📖 Logic Document": ("logic_doc", "Logic Document"),
        }
        file_type, subheader = name_to_meta[selected]
        st.subheader(subheader)
        content = file_service.get_file_content(file_id, file_type)
        if content:
            _render_generated_markdown(content)
        else:
            status = file_details.get("status", "unknown")
            st.warning(f"{subheader} was not generated for this analysis run. Status: {status}.")
            if file_details.get("error_message"):
                with st.expander("Show analysis details"):
                    st.text(file_details["error_message"])
        render_comment_box(
            file_service=file_service,
            file_type=file_type,
        )
