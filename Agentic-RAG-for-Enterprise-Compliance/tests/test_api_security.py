import asyncio
import io

import pytest

from src.api import main


class _FakeUploadFile:
    def __init__(self, data: bytes):
        self._buf = io.BytesIO(data)

    async def read(self, size: int) -> bytes:
        return self._buf.read(size)


def test_api_key_disabled_by_default(monkeypatch):
    monkeypatch.setattr(main.settings, "API_KEY", "")
    asyncio.run(main.require_api_key(x_api_key=None))  # must not raise


def test_api_key_rejects_missing_or_wrong_key(monkeypatch):
    monkeypatch.setattr(main.settings, "API_KEY", "secret123")

    with pytest.raises(main.HTTPException) as exc_info:
        asyncio.run(main.require_api_key(x_api_key=None))
    assert exc_info.value.status_code == 401

    with pytest.raises(main.HTTPException):
        asyncio.run(main.require_api_key(x_api_key="wrong"))


def test_api_key_accepts_correct_key(monkeypatch):
    monkeypatch.setattr(main.settings, "API_KEY", "secret123")
    asyncio.run(main.require_api_key(x_api_key="secret123"))  # must not raise


def test_upload_size_limit_rejects_oversized_file(monkeypatch, tmp_path):
    monkeypatch.setattr(main.settings, "MAX_UPLOAD_SIZE_MB", 1)
    fake_file = _FakeUploadFile(b"x" * (2 * 1024 * 1024))  # 2MB, over the 1MB cap
    tmp_file_path = tmp_path / "upload.pdf"

    with pytest.raises(main.HTTPException) as exc_info:
        with open(tmp_file_path, "wb") as tmp:
            asyncio.run(main._save_upload_with_limit(fake_file, tmp))
    assert exc_info.value.status_code == 413


def test_upload_size_limit_allows_file_within_limit(monkeypatch, tmp_path):
    monkeypatch.setattr(main.settings, "MAX_UPLOAD_SIZE_MB", 1)
    fake_file = _FakeUploadFile(b"x" * (512 * 1024))  # 512KB, under the 1MB cap
    tmp_file_path = tmp_path / "upload.pdf"

    with open(tmp_file_path, "wb") as tmp:
        asyncio.run(main._save_upload_with_limit(fake_file, tmp))

    assert tmp_file_path.stat().st_size == 512 * 1024
