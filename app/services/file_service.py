from typing import Optional, List, Dict
from .api_client import APIClient
from ..state.session_manager import SessionManager
from ..config import API_TIMEOUTS
import streamlit as st

class FileService:
    def __init__(self):
        self.client = APIClient()
    
    def upload_file(self, file, language: str = "en", overwrite: bool = False) -> Optional[Dict]:
        "upload file"
        if hasattr(file, "seek"):
            file.seek(0)
        files = {"upload_file": (file.name, file, file.type)}
        data = {
            "language": language,
            "overwrite": str(overwrite).lower(),
        }
        
        response = self.client.post(
            "/files/upload",
            files=files,
            data=data,
            timeout=API_TIMEOUTS["upload"]
        )
        if response is None:
            return None

        if response.status_code == 200:
            return response.json()

        if response.status_code == 409:
            warn_msg = "don't upload duplicate filename"
            st.warning(warn_msg)
            return {"status": "duplicate", "message": warn_msg}

        try:
            err = response.json()
            message = err.get("detail") or err.get("message") or f"Upload failed (HTTP {response.status_code})"
        except Exception:
            message = f"Upload failed (HTTP {response.status_code})"
        st.error(message)
        return {"status": "error", "message": message}
    
    def get_user_files(self) -> List[Dict]:
        """get user files"""
        response = self.client.get("/files/me", timeout=API_TIMEOUTS["preview"])
        if response and response.status_code == 200:
            return response.json()
        return []
    
    def delete_file(self, file_id: int) -> bool:
        """delete file"""
        response = self.client.delete(
            f"/files/{file_id}",
            timeout=API_TIMEOUTS["preview"]
        )
        
        if response and response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                st.success(data.get("message", "File deleted successfully!"))
                return True
        
        error_message = "Delete failed"
        if response is not None:
            try:
                error_message = response.json().get("message", error_message)
            except Exception:
                pass
        st.error(error_message)
        return False
    
    def get_file_content(self, file_id: int, file_type: str) -> Optional[str]:
        """get file content"""
        response = self.client.get(
            f"/files/{file_id}/preview/{file_type}",
            timeout=API_TIMEOUTS["preview"]
        )
        if response and response.status_code == 200:
            return response.json().get("content")
        return None

    def get_flowchart_code(self, file_id: int) -> Optional[str]:
        """get flowchart Mermaid code"""
        response = self.client.get(
            f"/files/{file_id}/preview/flowchart_code",
            timeout=API_TIMEOUTS["preview"]
        )
        if response and response.status_code == 200:
            return response.content.decode("utf-8", errors="replace")
        return None

    def get_sequence_chart_code(self, file_id: int) -> Optional[str]:
        """get sequence chart Mermaid code"""
        response = self.client.get(
            f"/files/{file_id}/preview/sequence_chart_code",
            timeout=API_TIMEOUTS["preview"]
        )
        if response and response.status_code == 200:
            return response.content.decode("utf-8", errors="replace")
        return None

    def download_file(self, file_id: int, file_type: str) -> Optional[bytes]:
        """download file"""
        response = self.client.get(
            f"/files/{file_id}/download/{file_type}",
            timeout=API_TIMEOUTS["download"]
        )
        if response and response.status_code == 200:
            return response.content
        st.error(f"Download failed for {file_type}")
        return None

    def save_comment(self, file_id: int, file_type: str, comment: str) -> bool:
        """save comment"""
        response = self.client.post(
            f"/files/{file_id}/comments",
            json={"file_id": file_id, "file_type": file_type, "comment": comment},
            timeout=API_TIMEOUTS["preview"]
        )
        if response and response.status_code == 200:
            return True
        return False
