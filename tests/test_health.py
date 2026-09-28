import dataclasses

from fastapi.testclient import TestClient

from apps.voice import main


def test_health():
    r = TestClient(main.app).get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_ready_reports_failure_when_dependencies_are_down(monkeypatch):
    down = dataclasses.replace(
        main.settings,
        database_url="postgresql://x:x@127.0.0.1:1/x",
        redis_url="redis://127.0.0.1:1/0",
    )
    monkeypatch.setattr(main, "settings", down)
    r = TestClient(main.app).get("/ready")
    assert r.status_code == 503
    assert r.json()["ok"] is False
