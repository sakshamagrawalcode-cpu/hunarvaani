import struct
import wave

import pytest

from core import stt


def _wav(path, seconds, rate=8000):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack("<h", 100) * int(rate * seconds))
    return str(path)


def test_split_into_pieces_of_at_most_28_seconds(tmp_path):
    pieces = stt.split_wav(_wav(tmp_path / "a.wav", 70))
    lengths = []
    for p in pieces:
        path = tmp_path / "p.wav"
        path.write_bytes(p)
        with wave.open(str(path)) as w:
            lengths.append(w.getnframes() / w.getframerate())
    assert lengths == [28, 28, 14]


class FakeResp:
    def __init__(self, status, body):
        self.status_code, self._body, self.text = status, body, str(body)

    def json(self):
        return self._body


def test_transcribe_joins_pieces_in_order(tmp_path, monkeypatch):
    calls = []

    def post(url, headers, files, data, timeout):
        calls.append((url, headers["api-subscription-key"], data))
        n = len(calls)
        return FakeResp(200, {"transcript": f"part{n} "})

    monkeypatch.setattr(stt.requests, "post", post)
    text = stt.transcribe_file(_wav(tmp_path / "a.wav", 30), "hi-IN", "key")
    assert sorted(text.split()) == ["part1", "part2"]
    assert all(c[0] == stt.STT_URL and c[1] == "key" for c in calls)
    assert calls[0][2] == {"model": "saaras:v3", "mode": "transcribe", "language_code": "hi-IN"}


def test_http_error_and_missing_key(tmp_path, monkeypatch):
    monkeypatch.setattr(stt.requests, "post", lambda *a, **k: FakeResp(401, {"error": "bad key"}))
    with pytest.raises(stt.SttError, match="401"):
        stt.transcribe_file(_wav(tmp_path / "a.wav", 2), "hi-IN", "key")
    with pytest.raises(stt.SttError, match="SARVAM_API_KEY"):
        stt.transcribe_file(_wav(tmp_path / "a.wav", 2), "hi-IN", "")
