import asyncio
from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile
from sqlmodel import select

from src.models import File
from src.services.file_service import FileService


def test_model_initialization_failure_marks_upload_failed(
    session, users, tmp_path, monkeypatch
):
    source = tmp_path / "original_code.ppcl"
    source.write_text("10 ON(X)", encoding="utf-8")
    monkeypatch.setattr(
        "src.services.file_service.prepare_output_dir", lambda _: None
    )
    monkeypatch.setattr(
        "src.services.file_service.write_original_file",
        lambda *_: source,
    )

    class BrokenRunner:
        def __init__(self, **kwargs):
            raise RuntimeError("missing model configuration")

    monkeypatch.setattr("src.services.file_service.PipelineRunner", BrokenRunner)
    upload = UploadFile(filename="failure.ppcl", file=BytesIO(b"10 ON(X)"))

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            FileService.upload(
                session,
                upload,
                "en",
                users["alice"].id,
            )
        )

    record = session.exec(
        select(File).where(File.filename == "failure.ppcl")
    ).one()
    assert exc.value.status_code == 500
    assert record.status == "failed"
    assert "missing model configuration" in record.error_message


def test_analysis_runs_outside_event_loop(session, users, tmp_path, monkeypatch):
    source = tmp_path / "original_code.ppcl"
    source.write_text("10 ON(X)", encoding="utf-8")
    monkeypatch.setattr(
        "src.services.file_service.prepare_output_dir", lambda _: None
    )
    monkeypatch.setattr(
        "src.services.file_service.write_original_file",
        lambda *_: source,
    )

    class Runner:
        def __init__(self, **kwargs):
            pass

        def run_parallel(self):
            return {
                "original_code": source,
                "cleaned_code": source,
                "logic_blocks": None,
                "data_points": None,
                "logic_doc": None,
                "flowchart": None,
                "flowchart_code": None,
                "sequence_chart": None,
                "sequence_chart_code": None,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "warnings": [],
            }

    calls = []

    async def fake_to_thread(function):
        calls.append(function)
        return function()

    monkeypatch.setattr("src.services.file_service.PipelineRunner", Runner)
    monkeypatch.setattr(
        "src.services.file_service.asyncio.to_thread", fake_to_thread
    )
    upload = UploadFile(filename="threaded.ppcl", file=BytesIO(b"10 ON(X)"))

    result = asyncio.run(
        FileService.upload(
            session,
            upload,
            "en",
            users["alice"].id,
        )
    )

    assert len(calls) == 1
    assert result["status"] == "completed"
