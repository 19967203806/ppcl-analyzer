import asyncio

import pytest
from fastapi import HTTPException

from src.utils.file_utils import read_and_validate_size


class DummyUpload:
    def __init__(self, data: bytes):
        self.data = data

    async def read(self) -> bytes:
        return self.data


def test_read_and_validate_size_rejects_empty_upload():
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(read_and_validate_size(DummyUpload(b"")))

    assert exc_info.value.status_code == 400
    assert "empty" in exc_info.value.detail


def test_read_and_validate_size_accepts_non_empty_upload():
    data = asyncio.run(read_and_validate_size(DummyUpload(b"00010 SET X=1\n")))

    assert data == b"00010 SET X=1\n"
