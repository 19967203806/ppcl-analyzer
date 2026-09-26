from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, Response
from datetime import datetime
from pathlib import Path
from typing import List
from pydantic import BaseModel

from ..models import SessionDep
from ..dependencies import CurrentUser, get_owned_file
from ..repositories.file_repository import FILE_TYPE_MAP
from ..services.file_service import FileService
from ..utils.mermaid_utils import normalize_sequence_mermaid
from ..utils.pdf_utils import md_to_pdf_bytes

router = APIRouter(tags=["files"], prefix="/files")


class FileDetail(BaseModel):
    id: int
    owner_id: int
    filename: str
    storage_path: str
    language: str | None = None
    status: str | None = None
    input_hash: str | None = None
    model_provider: str | None = None
    error_message: str | None = None
    original_code_path: str | None = None
    cleaned_code_path: str | None = None
    logic_blocks_path: str | None = None
    data_points_path: str | None = None
    logic_doc_path: str | None = None
    flowchart_path: str | None = None
    flowchart_code_path: str | None = None
    sequence_chart_path: str | None = None
    sequence_chart_code_path: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UploadResponse(BaseModel):
    file_id: int
    status: str
    message: str
    file: FileDetail


class DeleteResponse(BaseModel):
    status: str
    message: str
    file_id: int
    file_name: str


class CommentRequest(BaseModel):
    file_type: str
    comment: str


def _typed_path(record, file_type: str):
    if file_type not in FILE_TYPE_MAP:
        raise HTTPException(status_code=400, detail="file_type not legal")
    path_str = getattr(record, FILE_TYPE_MAP[file_type], None)
    if not path_str:
        raise HTTPException(status_code=404, detail="file not found")
    p = Path(path_str)
    if not p.exists():
        raise HTTPException(status_code=404, detail="physical file not found")
    return p


@router.post("/upload", response_model=UploadResponse)
async def upload_code(
    session: SessionDep,
    current_user: CurrentUser,
    upload_file: UploadFile = File(...),
    language: str = Form("en"),
    overwrite: bool = Form(False),
):
    result = await FileService.upload(session, upload_file, language, current_user.id, overwrite=overwrite)
    return UploadResponse(
        file_id=result["file_id"], status=result["status"],
        message=result["message"], file=FileDetail(**result["file"]),
    )


@router.get("/me", response_model=List[FileDetail])
def list_my_files(session: SessionDep, current_user: CurrentUser):
    return [FileDetail(**r) for r in FileService.list_my_files(session, current_user.id)]


@router.get("/{file_id}/preview/{file_type}")
def preview_file(file_id: int, file_type: str, session: SessionDep, current_user: CurrentUser):
    record = get_owned_file(session, file_id, current_user)
    p = _typed_path(record, file_type)
    if file_type == "sequence_chart_code":
        return Response(content=normalize_sequence_mermaid(p.read_text(encoding="utf-8", errors="replace")), media_type="text/plain")
    if file_type == "flowchart_code":
        return FileResponse(p, filename=p.name, media_type="text/plain")
    return {"content": p.read_text(encoding="utf-8", errors="replace")}


@router.get("/{file_id}/download/{file_type}")
def download_file(file_id: int, file_type: str, session: SessionDep, current_user: CurrentUser):
    record = get_owned_file(session, file_id, current_user)
    if file_type.endswith("_pdf"):
        base_type = file_type[:-4]
        if base_type not in {"logic_blocks", "data_points", "logic_doc"}:
            raise HTTPException(status_code=400, detail="pdf not supported for this file_type")
        md_path = _typed_path(record, base_type)
        try:
            return Response(content=md_to_pdf_bytes(md_path), media_type="application/pdf")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"failed to generate pdf: {e}")
    p = _typed_path(record, file_type)
    if file_type == "sequence_chart_code":
        return Response(
            content=normalize_sequence_mermaid(p.read_text(encoding="utf-8", errors="replace")),
            media_type="text/plain",
            headers={"Content-Disposition": f'attachment; filename="{p.name}"'},
        )
    media_type = "application/pdf" if p.suffix.lower() == ".pdf" else "application/octet-stream"
    return FileResponse(p, filename=p.name, media_type=media_type)


@router.delete("/{file_id}", response_model=DeleteResponse)
def delete_file(file_id: int, session: SessionDep, current_user: CurrentUser):
    get_owned_file(session, file_id, current_user)
    return DeleteResponse(**FileService.delete(session, file_id, current_user.id))


@router.post("/{file_id}/comments")
def add_comment(file_id: int, payload: CommentRequest, session: SessionDep, current_user: CurrentUser):
    get_owned_file(session, file_id, current_user)
    return FileService.add_comment(
        session, file_id=file_id, file_type=payload.file_type,
        comment=payload.comment, owner_id=current_user.id,
    )
