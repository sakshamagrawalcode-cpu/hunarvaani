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


def test_console_polling_is_kept_out_of_the_access_log():
    import logging

    from apps.voice.main import _HideConsolePolling

    def line(msg):
        return logging.LogRecord("uvicorn.access", logging.INFO, "", 0, msg, (), None)

    f = _HideConsolePolling()
    assert not f.filter(line('172.18.0.1:1 - "GET /console/api/summary HTTP/1.1" 200 OK'))
    assert not f.filter(line('172.18.0.1:1 - "GET /ready HTTP/1.1" 200 OK'))
    assert f.filter(line('172.18.0.1:1 - "GET /console/api/summary HTTP/1.1" 401 Unauthorized'))
    assert f.filter(line('1.2.3.4:1 - "WebSocket /exotel/ws/<token>" [accepted]'))
