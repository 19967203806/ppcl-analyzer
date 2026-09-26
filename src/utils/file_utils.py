from pathlib import Path
from fastapi import HTTPException, UploadFile

ALLOWED_SUFFIXES = {".ppcl", ".txt", ".pcl"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_extension(filename: str) -> None:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="please upload .ppcl file")

async def read_and_validate_size(upload_file: UploadFile) -> bytes:
    data = await upload_file.read()
    if not data:
        raise HTTPException(status_code=400, detail="uploaded file is empty")
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="file too large, max 10MB")
    return data

def prepare_output_dir(base: Path) -> Path:
    if base.exists():
        raise HTTPException(status_code=409, detail="directory already exists, upload prohibited")
    base.mkdir(parents=True, exist_ok=False)
    return base

def write_original_file(output_dir: Path, content: bytes) -> Path:
    original_path = output_dir / "original_code.ppcl"
    original_path.write_bytes(content)
    return original_path
