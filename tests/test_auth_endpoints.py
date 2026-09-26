def test_login_returns_token(client, users):
    r = client.post("/users/login", json={"username": "alice", "password": "alice-pw"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert body["user"]["username"] == "alice"
    assert isinstance(body["token"], str) and len(body["token"]) >= 32


def test_login_rejects_bad_password(client, users):
    r = client.post("/users/login", json={"username": "alice", "password": "wrong"})
    assert r.status_code == 200
    assert r.json()["status"] == "error"
    assert r.json()["token"] is None


def test_logout_revokes_token(client, users):
    token = client.post(
        "/users/login", json={"username": "alice", "password": "alice-pw"}
    ).json()["token"]
    r = client.post("/users/logout", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    # token no longer lists files
    r2 = client.get("/files/me", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 401
