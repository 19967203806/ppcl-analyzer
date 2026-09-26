from datetime import datetime, timedelta

from src.models.usage import UsageEvent
from src.repositories.token_repository import TokenRepository
from src.services import file_service as file_service_module
from src.services.qa_service import QAService


def _auth(session, user):
    return {"Authorization": f"Bearer {TokenRepository.issue(session, user.id)}"}


class _FakeRunner:
    def __init__(self, **_):
        pass

    def run_parallel(self):
        raise RuntimeError("model unavailable")


def _upload(client, headers, name="demo.ppcl"):
    return client.post(
        "/files/upload",
        files={"upload_file": (name, b"00010 SET $A=1\n", "text/plain")},
        data={"language": "en", "overwrite": "true"},
        headers=headers,
    )


def _stub_chat(monkeypatch):
    monkeypatch.setattr(
        QAService, "chat_stream",
        staticmethod(lambda **_: (iter(["ok"]), "trace", "conv")),
    )


def test_chat_limit_blocks_after_quota(client, session, users, monkeypatch):
    monkeypatch.setenv("DAILY_CHAT_LIMIT", "2")
    _stub_chat(monkeypatch)
    headers = _auth(session, users["alice"])

    for _ in range(2):
        assert client.post("/qa/chat", json={"question": "hi"}, headers=headers).status_code == 200
    r = client.post("/qa/chat", json={"question": "hi"}, headers=headers)
    assert r.status_code == 429
    assert "limit" in r.json()["detail"]


def test_chat_limit_is_per_user(client, session, users, monkeypatch):
    monkeypatch.setenv("DAILY_CHAT_LIMIT", "1")
    _stub_chat(monkeypatch)
    assert client.post("/qa/chat", json={"question": "hi"}, headers=_auth(session, users["alice"])).status_code == 200
    assert client.post("/qa/chat", json={"question": "hi"}, headers=_auth(session, users["bob"])).status_code == 200


def test_usage_from_previous_day_is_ignored(client, session, users, monkeypatch):
    monkeypatch.setenv("DAILY_CHAT_LIMIT", "1")
    _stub_chat(monkeypatch)
    session.add(UsageEvent(
        user_id=users["alice"].id, kind="chat",
        created_at=datetime.utcnow() - timedelta(days=1, hours=1),
    ))
    session.commit()
    assert client.post("/qa/chat", json={"question": "hi"}, headers=_auth(session, users["alice"])).status_code == 200


def test_no_limit_when_unset(client, session, users, monkeypatch):
    monkeypatch.delenv("DAILY_CHAT_LIMIT", raising=False)
    _stub_chat(monkeypatch)
    headers = _auth(session, users["alice"])
    for _ in range(5):
        assert client.post("/qa/chat", json={"question": "hi"}, headers=headers).status_code == 200


def test_failed_analysis_still_counts(client, session, users, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DAILY_ANALYSIS_LIMIT", "1")
    monkeypatch.setattr(file_service_module, "PipelineRunner", _FakeRunner)
    headers = _auth(session, users["alice"])

    assert _upload(client, headers).status_code == 500
    r = _upload(client, headers, name="other.ppcl")
    assert r.status_code == 429
    assert "analysis limit" in r.json()["detail"]
