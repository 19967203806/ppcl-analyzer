from pathlib import Path
from fastapi import HTTPException

from ..models import SessionDep
from .file_repository import FileRepository


class QARepository:
    @staticmethod
    def ensure_owner(session: SessionDep, file_id: int, owner_id: int) -> None:
        record = FileRepository.get(session, file_id)
        if record.owner_id != owner_id:
            raise HTTPException(status_code=403, detail="not authorized for this file")

    @staticmethod
    def fetch_original_code_path(session: SessionDep, file_id: int) -> Path:
        # Return the stored original code path; downstream consumers handle file IO.
        return FileRepository.resolve_path(session, file_id, "original_code")