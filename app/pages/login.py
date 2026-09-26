import streamlit as st
from ..services.auth_service import AuthService

def render_login_page():
    """render login page"""
    auth_service = AuthService()
    
    _, center, _ = st.columns([1, 2, 1])
    with center:
        st.title("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            if auth_service.login(username, password):
                st.rerun()
    st.stop()
