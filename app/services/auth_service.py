import streamlit as st
import time
from .api_client import APIClient
from ..state.session_manager import SessionManager
from ..config import API_TIMEOUTS

class AuthService:
    """user authentication service"""
    
    def __init__(self):
        self.client = APIClient()
    
    def login(self, username: str, password: str) -> bool:
        """login"""
        response = self.client.post(
            "/users/login",
            json={"username": username, "password": password},
            timeout=API_TIMEOUTS["default"]
        )
        
        if response and response.status_code == 200:
            data = response.json()
            token = data.get("token")
            if data.get("status") == "success" and data.get("user") and token:
                user = data["user"]

                SessionManager.set_token(token)
                SessionManager.set_user(user["id"], username)
                st.success("Login successful")
                time.sleep(0.6)
                return True
        
        error_message = "Login failed"
        if response is not None:
            try:
                error_message = response.json().get("message", error_message)
            except Exception:
                pass
        st.error(error_message)
        return False
    
    def logout(self):
        self.client.post("/users/logout", timeout=API_TIMEOUTS["default"])
        SessionManager.clear_user()
