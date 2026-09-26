from pathlib import Path
from datetime import datetime
from sqlmodel import select
from fastapi import HTTPException
from ..models import File, SessionDep, Comment
from ..models.qa import Conversation, Message

FILE_TYPE_MAP = {
    "original_code": "original_code_path",
    "cleaned_code": "cleaned_code_path",
    "logic_blocks": "logic_blocks_path",
    "data_points": "data_points_path",
    "logic_doc": "logic_doc_path",
    "flowchart": "flowchart_path",
    "flowchart_code": "flowchart_code_path",
    "sequence_chart": "sequence_chart_path",
    "sequence_chart_code": "sequence_chart_code_path",
}

class FileRepository:
    @staticmethod
    def find_duplicate(session: SessionDep, owner_id: int, filename: str) -> File | None:
        return session.exec(
            select(File).where(File.owner_id == owner_id, File.filename == filename)
        ).first()

    @staticmethod
    def create(
        session: SessionDep,
        filename: str,
        storage_path: Path,
        owner_id: int,
        language: str,
        input_hash: str,
        model_provider: str,
    ) -> File:
        record = File(
            filename=filename,
            storage_path=str(storage_path),
            owner_id=owner_id,
            language=language,
            input_hash=input_hash,
            model_provider=model_provider,
            status="running",
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record

    @staticmethod
    def update_pipeline_paths(session: SessionDep, record: File, result: dict) -> File:
        warnings = result.get("warnings") or []
        record.status = "completed_with_warnings" if warnings else "completed"
        record.error_message = "\n".join(warnings)[:2000] if warnings else None
        record.original_code_path = str(result["original_code"]) if result.get("original_code") is not None else None
        record.cleaned_code_path = str(result["cleaned_code"]) if result.get("cleaned_code") is not None else None
        record.logic_blocks_path = str(result["logic_blocks"]) if result.get("logic_blocks") is not None else None
        record.data_points_path = str(result["data_points"]) if result.get("data_points") is not None else None
        record.logic_doc_path = str(result["logic_doc"]) if result.get("logic_doc") is not None else None
        record.flowchart_path = str(result["flowchart"]) if result.get("flowchart") is not None else None
        record.flowchart_code_path = str(result["flowchart_code"]) if result.get("flowchart_code") is not None else None
        record.sequence_chart_path = str(result.get("sequence_chart")) if result.get("sequence_chart") is not None else None
        record.sequence_chart_code_path = str(result.get("sequence_chart_code")) if result.get("sequence_chart_code") is not None else None
        record.prompt_tokens = int(result.get("prompt_tokens", 0))
        record.completion_tokens = int(result.get("completion_tokens", 0))
        record.total_tokens = int(result.get("total_tokens", 0))
        record.updated_at = datetime.utcnow()
        session.add(record)
        session.commit()
        session.refresh(record)
        return record

    @staticmethod
    def mark_failed(session: SessionDep, record: File, error_message: str) -> File:
        record.status = "failed"
        record.error_message = error_message[:2000]
        record.updated_at = datetime.utcnow()
        session.add(record)
        session.commit()
        session.refresh(record)
        return record

    @staticmethod
    def list_by_user(session: SessionDep, user_id: int) -> list[File]:
        stmt = select(File).where(File.owner_id == user_id).order_by(File.id.desc())
        return session.exec(stmt).all()

    @staticmethod
    def get(session: SessionDep, file_id: int) -> File:
        record = session.get(File, file_id)
        if not record:
            raise HTTPException(status_code=404, detail="file record not found")
        return record

    @staticmethod
    def resolve_path(session: SessionDep, file_id: int, file_type: str, owner_id: int | None = None) -> Path:
        if file_type not in FILE_TYPE_MAP:
            raise HTTPException(status_code=400, detail="file_type not legal")
        record = FileRepository.get(session, file_id)
        if owner_id is not None and record.owner_id != owner_id:
            raise HTTPException(status_code=403, detail="not authorized for this file")
        path_str = getattr(record, FILE_TYPE_MAP[file_type], None)
        if not path_str:
            raise HTTPException(status_code=404, detail="file not found")
        p = Path(path_str)
        if not p.exists():
            raise HTTPException(status_code=404, detail="physical file not found")
        return p

    @staticmethod
    def delete(session: SessionDep, record: File) -> None:
        if record.id is not None:
            comments = session.exec(
                select(Comment).where(Comment.file_id == record.id)
            ).all()
            for comment in comments:
                session.delete(comment)

            conversations = session.exec(
                select(Conversation).where(Conversation.file_id == record.id)
            ).all()
            for conversation in conversations:
                messages = session.exec(
                    select(Message).where(
                        Message.conversation_id == conversation.conversation_id
                    )
                ).all()
                for message in messages:
                    session.delete(message)
                session.delete(conversation)
        session.delete(record)
        session.commit()

    @staticmethod
    def add_comment(session: SessionDep, file_id: int, file_type: str, comment: str, owner_id: int) -> Comment:
        new_comment = Comment(file_id=file_id, file_type=file_type, comment=comment, owner_id=owner_id)
        session.add(new_comment)
        session.commit()
        session.refresh(new_comment)
        return new_comment
