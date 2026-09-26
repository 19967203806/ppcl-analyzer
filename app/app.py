import streamlit as st
import streamlit.components.v1 as components
from .config import STREAMLIT_CONFIG
from .state.session_manager import SessionManager
from .pages.login import render_login_page
from .pages.upload import render_upload_page
from .pages.ai_chat import render_ai_chat_page
from .components.sidebar_panel import render_sidebar_panel
from .components.result_tabs import render_result_tabs


def _disable_browser_translation() -> None:
    """Keep browser translators from mutating Streamlit's React-managed DOM."""
    components.html(
        """
        <script>
          try {
            const parentDocument = window.parent.document;
            parentDocument.documentElement.setAttribute("translate", "no");
            parentDocument.body?.setAttribute("translate", "no");
            parentDocument.body?.classList.add("notranslate");

            let meta = parentDocument.head.querySelector('meta[name="google"]');
            if (!meta) {
              meta = parentDocument.createElement("meta");
              meta.name = "google";
              parentDocument.head.appendChild(meta);
            }
            meta.content = "notranslate";
          } catch (_) {
            // The app still works if a browser blocks iframe access to its parent.
          }
        </script>
        """,
        height=0,
        width=0,
    )


def main():
    """main app"""
    # set Streamlit page
    st.set_page_config(**STREAMLIT_CONFIG)
    _disable_browser_translation()
    
    # initialize session state
    SessionManager.init()

    # if not logged in, show login page
    if not SessionManager.is_logged_in():
        render_login_page()
        return
    
    st.title("PPCL Code Analysis System")
    st.markdown("---")
    
    with st.sidebar:
        view = st.radio("Page", ["Analysis", "AI Assistant"])

    if view == "AI Assistant":
        render_ai_chat_page()
    if view == "Analysis":
        render_sidebar_panel()
        render_upload_page()
        render_result_tabs()

if __name__ == "__main__":
    main()
