import requests
from typing import Optional
import streamlit as st
from ..config import BACKEND_URL, API_TIMEOUTS

class APIClient:    
    def __init__(self, base_url: str = BACKEND_URL):
        self.base_url = base_url
    
    def _make_request(self, method, endpoint, timeout=API_TIMEOUTS["default"], **kwargs):
        from ..state.session_manager import SessionManager
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.pop("headers", {}) or {}
        token = SessionManager.get_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            response = requests.request(method, url, timeout=timeout, headers=headers, **kwargs)
        except requests.exceptions.RequestException as e:
            st.error(f"API request failed: {str(e)}")
            return None
        if response.status_code == 401:
            SessionManager.clear_user()
            st.error("登录已过期,请重新登录")
            return None
        return response
    
    def get(self, endpoint: str, **kwargs) -> Optional[requests.Response]:
        return self._make_request("GET", endpoint, **kwargs)
    
    def post(self, endpoint: str, **kwargs) -> Optional[requests.Response]:
        return self._make_request("POST", endpoint, **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> Optional[requests.Response]:
        return self._make_request("DELETE", endpoint, **kwargs)
