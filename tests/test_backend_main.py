import src.backend as backend


def test_backend_binds_to_loopback_by_default(monkeypatch):
    monkeypatch.delenv("API_HOST", raising=False)
    monkeypatch.delenv("API_PORT", raising=False)
    captured = {}

    def fake_run(app, *, host, port):
        captured.update(app=app, host=host, port=port)

    monkeypatch.setattr(backend.uvicorn, "run", fake_run)

    backend.main()

    assert captured == {
        "app": "src.backend:app",
        "host": "127.0.0.1",
        "port": 8000,
    }


def test_backend_accepts_explicit_bind_address(monkeypatch):
    monkeypatch.setenv("API_HOST", "0.0.0.0")
    monkeypatch.setenv("API_PORT", "9000")
    captured = {}

    def fake_run(app, *, host, port):
        captured.update(app=app, host=host, port=port)

    monkeypatch.setattr(backend.uvicorn, "run", fake_run)

    backend.main()

    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 9000
