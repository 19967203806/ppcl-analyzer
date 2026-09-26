import streamlit as st
from typing import Optional, List

class SessionManager:
    """Streamlit session state"""
    
    # user
    USER_LOGGED_IN = "logged_in"
    USERNAME = "username"
    USER_ID = "user_id"
    USER_FILES = "user_files"
    
    # file
    FILE_ID = "file_id"
    FILE_DETAILS = "file_details"
    UPLOADED_FILE = "uploaded_file"
    
    # processing state
    PROCESSING = "processing"

    #language
    LANGUAGE = "language"

    # auth token
    AUTH_TOKEN = "auth_token"

    # ai chat
    AI_CHAT_HISTORY = "ai_chat_history"
    CONVERSATION_ID = "conversation_id"
    CONVERSATIONS = "conversations"
    
    @staticmethod
    def init():
        """initialize all session state"""
        defaults = {
            SessionManager.USER_LOGGED_IN: False,
            SessionManager.USERNAME: "",
            SessionManager.USER_ID: None,
            SessionManager.USER_FILES: [],
            SessionManager.FILE_ID: None,
            SessionManager.FILE_DETAILS: None,
            SessionManager.UPLOADED_FILE: None,
            SessionManager.PROCESSING: False,
            SessionManager.LANGUAGE: "en",
            SessionManager.AUTH_TOKEN: None,
            SessionManager.AI_CHAT_HISTORY: [],
            SessionManager.CONVERSATION_ID: None,
            SessionManager.CONVERSATIONS: [],
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    @staticmethod
    def set_user(user_id: int, username: str):
        """set user info"""
        st.session_state[SessionManager.USER_ID] = user_id
        st.session_state[SessionManager.USERNAME] = username
        st.session_state[SessionManager.USER_LOGGED_IN] = True

    @staticmethod
    def get_user_id() -> Optional[int]:
        """get user id"""
        return st.session_state.get(SessionManager.USER_ID)
    
    @staticmethod
    def set_token(token: str) -> None:
        st.session_state[SessionManager.AUTH_TOKEN] = token

    @staticmethod
    def get_token() -> Optional[str]:
        return st.session_state.get(SessionManager.AUTH_TOKEN)

    @staticmethod
    def clear_user():
        """clear user info"""
        st.session_state[SessionManager.USER_LOGGED_IN] = False
        st.session_state[SessionManager.USERNAME] = ""
        st.session_state[SessionManager.USER_ID] = None
        st.session_state[SessionManager.AUTH_TOKEN] = None
    
    @staticmethod
    def is_logged_in() -> bool:
        """check if logged in"""
        return st.session_state.get(SessionManager.USER_LOGGED_IN, False)

    @staticmethod
    def set_current_file(file_id: int, file_details: dict):
        """set current file"""
        st.session_state[SessionManager.FILE_ID] = file_id
        st.session_state[SessionManager.FILE_DETAILS] = file_details
    
    @staticmethod
    def get_current_file_id() -> Optional[int]:
        """get currently selected file id (if any)"""
        return st.session_state.get(SessionManager.FILE_ID)
    
    @staticmethod
    def set_user_files(files: List[dict]):
        """set user files"""
        st.session_state[SessionManager.USER_FILES] = files
    
    @staticmethod
    def get_user_files() -> List[dict]:
        """get user files"""
        return st.session_state.get(SessionManager.USER_FILES, [])

    @staticmethod
    def set_processing(status: bool) -> None:
        """set processing status"""
        st.session_state[SessionManager.PROCESSING] = status

    @staticmethod
    def check_processing() -> bool:
        """check if processing"""
        return st.session_state.get(SessionManager.PROCESSING, False)

    @staticmethod
    def get_uploaded_file():
        """get uploaded file"""
        return st.session_state.get(SessionManager.UPLOADED_FILE)
    
    @staticmethod
    def set_uploaded_file(uploaded_file) -> None:
        """set uploaded file"""
        st.session_state[SessionManager.UPLOADED_FILE] = uploaded_file

    @staticmethod
    def set_language(language: str) -> None:
        """set language"""
        st.session_state[SessionManager.LANGUAGE] = language

    @staticmethod
    def get_language() -> str:
        """get language"""
        return st.session_state.get(SessionManager.LANGUAGE, "en")

    # ----- AI Chat state -----
    @staticmethod
    def has_ai_history() -> bool:
        """check if AI chat history is initialized"""
        return SessionManager.AI_CHAT_HISTORY in st.session_state

    @staticmethod
    def get_ai_history() -> List[dict]:
        """get AI chat history"""
        return st.session_state.get(SessionManager.AI_CHAT_HISTORY, [])

    @staticmethod
    def set_ai_history(history: List[dict]):
        """set AI chat history"""
        st.session_state[SessionManager.AI_CHAT_HISTORY] = history

    @staticmethod
    def clear_ai_history():
        """clear AI chat history"""
        st.session_state.pop(SessionManager.AI_CHAT_HISTORY, None)

    @staticmethod
    def get_conversation_id() -> Optional[str]:
        """get current conversation id"""
        return st.session_state.get(SessionManager.CONVERSATION_ID)

    @staticmethod
    def set_conversation_id(conversation_id: Optional[str]):
        """set current conversation id"""
        st.session_state[SessionManager.CONVERSATION_ID] = conversation_id

    @staticmethod
    def get_conversations() -> List[dict]:
        """get conversation list"""
        return st.session_state.get(SessionManager.CONVERSATIONS, [])

    @staticmethod
    def set_conversations(threads: List[dict]):
        """set conversation list"""
        st.session_state[SessionManager.CONVERSATIONS] = threads

    @staticmethod
    def clear_conversations():
        """clear conversation list"""
        st.session_state.pop(SessionManager.CONVERSATIONS, None)
