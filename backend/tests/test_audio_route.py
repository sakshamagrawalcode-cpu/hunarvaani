from fastapi.testclient import TestClient

from apps.voice import main


def test_audio_route_serves_wav_and_rejects_bad_names(tmp_path, monkeypatch):
    (tmp_path / "hi").mkdir()
    (tmp_path / "hi" / "P01.wav").write_bytes(b"RIFFdata")
    (tmp_path / "secret.wav").write_bytes(b"nope")
    monkeypatch.setattr(main, "AUDIO_DIR", tmp_path)
    client = TestClient(main.app)

    ok = client.get("/audio/hi/P01.wav")
    assert ok.status_code == 200
    assert ok.headers["content-type"] == "audio/wav"
    assert ok.content == b"RIFFdata"

    assert client.get("/audio/hi/P99.wav").status_code == 404
    assert client.get("/audio/hi/..%2Fsecret.wav").status_code == 404
    assert client.get("/audio/../P01.wav").status_code == 404
