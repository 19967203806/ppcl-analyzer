from datetime import datetime
from pathlib import Path
from fastapi import HTTPException, UploadFile
import asyncio
import hashlib
import os
import shutil
from loguru import logger
from ..repositories.user_repository import UserRepository
from ..repositories.file_repository import FILE_TYPE_MAP, FileRepository
from ..utils.file_utils import (
    validate_extension,
    read_and_validate_size,
    prepare_output_dir,
    write_original_file,
)
from ..pipeline import PipelineRunner
from ..models import SessionDep, Comment


class FileService:
    @staticmethod
    def _serialize_file(record) -> dict:
        return {
            "id": record.id,
            "owner_id": record.owner_id,
            "filename": record.filename,
            "storage_path": record.storage_path,
            "language": record.language,
            "status": record.status,
            "input_hash": record.input_hash,
            "model_provider": record.model_provider,
            "error_message": record.error_message,
            "original_code_path": record.original_code_path,
            "cleaned_code_path": record.cleaned_code_path,
            "logic_blocks_path": record.logic_blocks_path,
            "data_points_path": record.data_points_path,
            "logic_doc_path": record.logic_doc_path,
            "flowchart_path": record.flowchart_path,
            "flowchart_code_path": record.flowchart_code_path,
            "sequence_chart_path": record.sequence_chart_path,
            "sequence_chart_code_path": record.sequence_chart_code_path,
            "prompt_tokens": record.prompt_tokens,
            "completion_tokens": record.completion_tokens,
            "total_tokens": record.total_tokens,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }

    @staticmethod
    async def upload(
        session: SessionDep,
        upload_file: UploadFile,
        language: str,
        owner_id: int,
        overwrite: bool = False,
    ) -> dict:
        # user validation
        user = UserRepository.get_by_id(session, owner_id)

        # extension & size validation
        validate_extension(upload_file.filename)
        file_bytes = await read_and_validate_size(upload_file)
        input_hash = hashlib.sha256(file_bytes).hexdigest()
        language = language if language in {"en", "zh"} else "en"
        model_provider = os.getenv("MODEL_PROVIDER", "azure").lower()

        duplicate = FileRepository.find_duplicate(session, user.id, upload_file.filename)
        if duplicate:
            if not overwrite:
                raise HTTPException(status_code=409, detail="already uploaded this file name")

        run_id = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        output_dir_name = f"{Path(upload_file.filename).stem}_{run_id}_{input_hash[:8]}"
        output_dir = Path("output") / str(user.id) / output_dir_name

        # prepare directory & write original file
        prepare_output_dir(output_dir)
        original_path = write_original_file(output_dir, file_bytes)

        # create DB record
        record = FileRepository.create(
            session=session,
            filename=upload_file.filename,
            storage_path=output_dir,
            owner_id=user.id,
            language=language,
            input_hash=input_hash,
            model_provider=model_provider,
        )

        # run pipeline
        try:
            runner = PipelineRunner(
                input_file=original_path,
                output_base_dir=output_dir,
                language=language,
            )
            result = await asyncio.to_thread(runner.run_parallel)
            # update DB record with pipeline results
            record = FileRepository.update_pipeline_paths(session, record, result)
        except Exception as exc:
            FileRepository.mark_failed(session, record, str(exc))
            raise HTTPException(status_code=500, detail=f"analysis failed: {exc}") from exc

        if duplicate:
            try:
                old_storage_path = Path(duplicate.storage_path)
                if old_storage_path.exists() and old_storage_path.is_dir():
                    shutil.rmtree(old_storage_path)
                FileRepository.delete(session, duplicate)
            except Exception as exc:
                logger.warning(f"analysis completed but old result cleanup failed: {exc}")

        return {
            "file_id": record.id,
            "status": record.status,
            "message": "analysis completed successfully" if record.status == "completed" else "analysis completed with warnings",
            "file": FileService._serialize_file(record),
        }

    @staticmethod
    def list_my_files(session: SessionDep, user_id: int) -> list[dict]:
        records = FileRepository.list_by_user(session, user_id)
        return [FileService._serialize_file(r) for r in records]

    @staticmethod
    def resolve_path(session: SessionDep, file_id: int, file_type: str, owner_id: int | None = None):
        return FileRepository.resolve_path(session, file_id, file_type, owner_id)

    @staticmethod
    def delete(session: SessionDep, file_id: int, owner_id: int) -> dict:
        record = FileRepository.get(session, file_id)
        if record.owner_id != owner_id:
            raise HTTPException(status_code=404, detail="file not found")
        file_name = record.filename
        storage_path = Path(record.storage_path)
        if storage_path.exists() and storage_path.is_dir():
            try:
                shutil.rmtree(storage_path)
                msg = "file and storage directory deleted"
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"failed to delete storage directory: {e}")
        else:
            msg = "storage directory missing"

        legacy_comment_path = Path("comments") / str(owner_id) / str(file_id)
        if legacy_comment_path.exists() and legacy_comment_path.is_dir():
            try:
                shutil.rmtree(legacy_comment_path)
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"failed to delete legacy comment directory: {e}",
                )

        FileRepository.delete(session, record)
        return {"status": "success", "message": f"file '{file_name}' deleted successfully. {msg}", "file_id": file_id, "file_name": file_name}

    @staticmethod
    def add_comment(session: SessionDep, file_id: int, file_type: str, comment: str, owner_id: int) -> Comment:
        if file_type not in FILE_TYPE_MAP:
            raise HTTPException(status_code=400, detail="file_type not legal")
        if not comment.strip():
            raise HTTPException(status_code=400, detail="comment cannot be empty")

        return FileRepository.add_comment(session, file_id=file_id, file_type=file_type, comment=comment, owner_id=owner_id)
