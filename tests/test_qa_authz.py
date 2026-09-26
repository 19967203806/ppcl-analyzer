from src.models import File
from src.repositories.token_repository import TokenRepository
from src.services.qa_service import QAService


def _auth(session, user):
    return {"Authorization": f"Bearer {TokenRepository.issue(session, user.id)}"}


def test_history_requires_token(client):
    assert client.get("/qa/history").status_code == 401


def test_chat_blocks_other_users_file(client, session, users, tmp_path):
    f = File(filename="a.ppcl", storage_path=str(tmp_path), owner_id=users["alice"].id)
    session.add(f)
    session.commit()
    session.refresh(f)
    r = client.post(
        "/qa/chat",
        json={"question": "hi", "file_id": f.id},
        headers=_auth(session, users["bob"]),
    )
    assert r.status_code == 404


def test_history_scoped_to_caller(client, session, users):
    r = client.get("/qa/history", headers=_auth(session, users["alice"]))
    assert r.status_code == 200


def test_chat_stream_contract_is_unchanged(
    client, session, users, monkeypatch
):
    monkeypatch.setattr(
        QAService,
        "chat_stream",
        staticmethod(lambda **_: (iter(["hello", " world"]), "trace-1", "conv-1")),
    )

    response = client.post(
        "/qa/chat",
        json={"question": "hi"},
        headers=_auth(session, users["alice"]),
    )

    assert response.status_code == 200
    assert response.text == "hello world"
    assert response.headers["Trace-Id"] == "trace-1"
    assert response.headers["Conversation-Id"] == "conv-1"
    assert response.headers["content-type"].startswith("text/plain")
