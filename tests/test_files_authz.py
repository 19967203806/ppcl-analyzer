from sqlmodel import select

from src.models import Comment, File
from src.models.qa import Conversation, Message
from src.repositories.token_repository import TokenRepository


def _make_file(session, owner_id, tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    doc = tmp_path / "logic_blocks.md"
    doc.write_text("# blocks", encoding="utf-8")
    f = File(
        filename="a.ppcl",
        storage_path=str(tmp_path),
        owner_id=owner_id,
        status="completed",
        logic_blocks_path=str(doc),
    )
    session.add(f)
    session.commit()
    session.refresh(f)
    return f


def _auth(session, user):
    return {"Authorization": f"Bearer {TokenRepository.issue(session, user.id)}"}


def test_list_me_returns_only_callers_files(client, session, users, tmp_path):
    _make_file(session, users["alice"].id, tmp_path / "a")
    _make_file(session, users["bob"].id, tmp_path / "b")
    r = client.get("/files/me", headers=_auth(session, users["alice"]))
    assert r.status_code == 200
    assert {row["owner_id"] for row in r.json()} == {users["alice"].id}


def test_preview_requires_token(client, session, users, tmp_path):
    f = _make_file(session, users["alice"].id, tmp_path / "a")
    assert client.get(f"/files/{f.id}/preview/logic_blocks").status_code == 401


def test_preview_blocks_other_user(client, session, users, tmp_path):
    f = _make_file(session, users["alice"].id, tmp_path / "a")
    r = client.get(
        f"/files/{f.id}/preview/logic_blocks", headers=_auth(session, users["bob"])
    )
    assert r.status_code == 404


def test_preview_allows_owner(client, session, users, tmp_path):
    f = _make_file(session, users["alice"].id, tmp_path / "a")
    r = client.get(
        f"/files/{f.id}/preview/logic_blocks", headers=_auth(session, users["alice"])
    )
    assert r.status_code == 200
    assert "blocks" in r.json()["content"]


def test_delete_blocks_other_user(client, session, users, tmp_path):
    f = _make_file(session, users["alice"].id, tmp_path / "a")
    r = client.delete(f"/files/{f.id}", headers=_auth(session, users["bob"]))
    assert r.status_code == 404


def test_delete_removes_related_private_data_and_legacy_file_comments(
    client, session, users, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    f = _make_file(session, users["alice"].id, tmp_path / "storage")
    headers = _auth(session, users["alice"])
    comment_response = client.post(
        f"/files/{f.id}/comments",
        json={"file_type": "logic_blocks", "comment": "temporary test comment"},
        headers=headers,
    )
    assert comment_response.status_code == 200

    conversation = Conversation(
        owner_id=users["alice"].id,
        file_id=f.id,
        title="Temporary test conversation",
    )
    session.add(conversation)
    session.commit()
    session.refresh(conversation)
    session.add(
        Message(
            conversation_id=conversation.conversation_id,
            role="user",
            content="temporary test message",
        )
    )
    session.commit()

    legacy_comment_dir = tmp_path / "comments" / str(users["alice"].id) / str(f.id)
    legacy_comment_dir.mkdir(parents=True)
    (legacy_comment_dir / "logic_blocks.txt").write_text(
        "legacy comment", encoding="utf-8"
    )

    delete_response = client.delete(f"/files/{f.id}", headers=headers)

    assert delete_response.status_code == 200
    assert session.exec(select(Comment).where(Comment.file_id == f.id)).all() == []
    assert session.exec(
        select(Conversation).where(Conversation.file_id == f.id)
    ).all() == []
    assert session.exec(
        select(Message).where(
            Message.conversation_id == conversation.conversation_id
        )
    ).all() == []
    assert not legacy_comment_dir.exists()


def test_comment_blocks_other_user(client, session, users, tmp_path):
    f = _make_file(session, users["alice"].id, tmp_path / "a")
    r = client.post(
        f"/files/{f.id}/comments",
        json={"file_type": "logic_blocks", "comment": "hi"},
        headers=_auth(session, users["bob"]),
    )
    assert r.status_code == 404


def test_comment_rejects_unknown_file_type(client, session, users, tmp_path):
    f = _make_file(session, users["alice"].id, tmp_path / "a")
    r = client.post(
        f"/files/{f.id}/comments",
        json={"file_type": "../../outside", "comment": "hi"},
        headers=_auth(session, users["alice"]),
    )
    assert r.status_code == 400


def test_comment_rejects_blank_text(client, session, users, tmp_path):
    f = _make_file(session, users["alice"].id, tmp_path / "a")
    r = client.post(
        f"/files/{f.id}/comments",
        json={"file_type": "logic_blocks", "comment": "   "},
        headers=_auth(session, users["alice"]),
    )
    assert r.status_code == 400


def test_download_blocks_other_user(client, session, users, tmp_path):
    f = _make_file(session, users["alice"].id, tmp_path / "a")
    r = client.get(
        f"/files/{f.id}/download/logic_blocks", headers=_auth(session, users["bob"])
    )
    assert r.status_code == 404


def test_download_requires_token(client, session, users, tmp_path):
    f = _make_file(session, users["alice"].id, tmp_path / "a")
    assert client.get(f"/files/{f.id}/download/logic_blocks").status_code == 401
