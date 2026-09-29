"""A full Exotel Voicebot call over a real WebSocket, against real Postgres and Redis."""

import base64
import os
import struct
import time
import wave
from pathlib import Path

import psycopg
import pytest
import redis
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from apps.voice import main
from core import callbacks
from core.config import Settings
from core.dialogue.prompts import PROMPTS
from core.phone import phone_hash

DB = os.environ.get("TEST_DATABASE_URL")
RD = os.environ.get("TEST_REDIS_URL")
pytestmark = pytest.mark.skipif(not (DB and RD), reason="TEST_DATABASE_URL/TEST_REDIS_URL unset")

TOKEN = "ws-secret-token"
CALLER = "919876543210"


@pytest.fixture(scope="module")
def schema():
    with psycopg.connect(DB, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        for f in sorted((Path(__file__).resolve().parent.parent / "db").glob("*.sql")):
            conn.execute(f.read_text(encoding="utf-8"))


@pytest.fixture
def audio_dir(tmp_path):
    folder = tmp_path / "audio" / "hi"
    folder.mkdir(parents=True)
    for pid in PROMPTS["hi-IN"]:
        with wave.open(str(folder / f"{pid}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(8000)
            w.writeframes(b"\x00\x00" * 400)
    return tmp_path / "audio"


@pytest.fixture
def settings(schema, audio_dir, tmp_path, monkeypatch):
    s = Settings(
        public_base_url="https://hv.test",
        database_url=DB,
        redis_url=RD,
        default_language="hi-IN",
        second_language="",
        callback_delay_seconds=5,
        max_triggers_per_day=3,
        daily_call_budget=100,
        quiet_hours="",
        phone_hash_secret="hash-secret",
        phone_enc_key=Fernet.generate_key().decode(),
        exotel_ws_token=TOKEN,
        ivr_timeout_seconds=0.3,
        record_silence_seconds=0.6,
        record_no_speech_seconds=0.6,
        recordings_dir=str(tmp_path / "recordings"),
    )
    with psycopg.connect(DB, autocommit=True) as conn:
        conn.execute("TRUNCATE call, answer, consent, story, event, blocked_number CASCADE")
    redis.Redis.from_url(RD).flushdb()
    monkeypatch.setattr(main, "settings", s)
    monkeypatch.setattr(main, "AUDIO_DIR", audio_dir)
    main._redis_for.cache_clear()
    return s


@pytest.fixture
def client(settings):
    return TestClient(main.app)


def rows(sql, *args):
    with psycopg.connect(DB) as conn:
        return conn.execute(sql, args).fetchall()


class Phone:
    """Plays the Exotel side of the WebSocket."""

    def __init__(self, ws):
        self.ws = ws

    def start(self, caller=CALLER, call_sid="exo-sid-1"):
        self.ws.send_json({"event": "connected"})
        self.ws.send_json(
            {
                "event": "start",
                "stream_sid": "stream-1",
                "start": {
                    "stream_sid": "stream-1",
                    "call_sid": call_sid,
                    "from": caller,
                    "media_format": {"encoding": "raw/slin", "sample_rate": "8000"},
                },
            }
        )

    def hear(self, name):
        """Read until the prompt(s) `name` finish playing; return every mark heard."""
        heard = []
        while True:
            msg = self.ws.receive_json()
            if msg["event"] == "mark":
                heard.append(msg["mark"]["name"])
                if msg["mark"]["name"] == name:
                    return heard

    def press(self, digit):
        self.ws.send_json({"event": "dtmf", "stream_sid": "stream-1", "dtmf": {"digit": digit}})

    def speak(self, seconds):
        time.sleep(0.6)  # a caller starts after the beep has actually played
        frame = base64.b64encode(struct.pack("<h", 1000) * 160).decode()
        for _ in range(int(seconds * 50)):
            self.ws.send_json({"event": "media", "media": {"payload": frame}})

    def until_hangup(self):
        with pytest.raises(WebSocketDisconnect):
            while True:
                self.ws.receive_json()


def dial(client):
    return client.websocket_connect(f"/exotel/ws/{TOKEN}")


def test_full_interview_with_story(client, settings):
    with dial(client) as ws:
        p = Phone(ws)
        p.start()
        p.hear("P01")
        p.press("1")
        p.hear("P03")
        p.press("1")
        p.hear("P06")
        p.press("1")
        p.hear("P07")
        p.press("1")
        p.hear("P08")
        p.press("2")
        p.hear("P09")
        p.press("4")
        p.hear("P10")
        p.press("2")
        p.hear("P11")
        p.press("1")
        p.hear("P12")
        p.speak(2)
        p.press("#")
        p.hear("P14")
        p.press("2")
        p.until_hangup()

    [(status, dur, answered, ended)] = rows(
        "SELECT status, duration_seconds, answered_at IS NOT NULL, ended_at IS NOT NULL FROM call"
    )
    assert (status, answered, ended) == ("completed", True, True) and dur >= 0
    answers = dict(rows("SELECT step, value FROM answer"))
    assert answers == {"q_education": "10th", "q_travel": "10km", "q_lean": "job", "trades": "7531"}
    consents = sorted(rows("SELECT kind, granted FROM consent"))
    assert consents == [("recording", True), ("research", False), ("share", True)]
    [(path,)] = rows("SELECT recording_url FROM story")
    with wave.open(path) as w:
        assert w.getframerate() == 8000 and w.getnframes() / 8000 == pytest.approx(2, abs=0.2)
    keys = rows("SELECT count(*) FROM event WHERE kind = 'key'")
    assert keys == [(9,)]


def test_nine_deletes_data_and_blocks_the_hashed_number(client, settings):
    with dial(client) as ws:
        p = Phone(ws)
        p.start()
        p.hear("P01")
        p.press("9")
        p.until_hangup()
    [(h, reason)] = rows("SELECT phone_hash, reason FROM blocked_number")
    assert h == phone_hash("+919876543210", "hash-secret") and reason == "caller_request"
    assert rows("SELECT count(*) FROM call") == [(0,)]


def test_timeouts_repeat_then_skip(client, settings):
    with dial(client) as ws:
        p = Phone(ws)
        p.start()
        for prompt, key in (("P01", "1"), ("P03", "1"), ("P06", "1"), ("P07", "1"), ("P08", "1")):
            p.hear(prompt)
            p.press(key)
        p.hear("P09")
        p.hear("P16+P09")
        p.hear("P10")
        p.press("3")
        p.hear("P11")
        p.press("2")
        p.hear("P12")
        ws.close()
    answers = dict(rows("SELECT step, value FROM answer"))
    assert answers["q_education"] == "skipped" and answers["q_travel"] == "30km"
    assert rows("SELECT count(*) FROM event WHERE kind = 'timeout'") == [(2,)]


def test_zero_flags_human_and_no_to_recording_skips_story(client, settings):
    with dial(client) as ws:
        p = Phone(ws)
        p.start()
        p.hear("P01")
        p.press("1")
        p.hear("P03")
        p.press("0")
        p.hear("P19+P03")
        p.press("1")
        p.hear("P06")
        p.press("2")
        for prompt, key in (("P07", "2"), ("P08", "2"), ("P09", "1"), ("P10", "1"), ("P11", "3")):
            p.hear(prompt)
            p.press(key)
        heard = p.hear("P14")
        assert "P12" not in heard
        p.press("5")
        p.until_hangup()
    [(human, keypad)] = rows("SELECT human_flag, keypad_only FROM call")
    assert human is True and keypad is True
    assert rows("SELECT count(*) FROM story") == [(0,)]


def test_not_now_schedules_tomorrow(client, settings):
    with dial(client) as ws:
        p = Phone(ws)
        p.start()
        p.hear("P01")
        p.press("1")
        p.hear("P03")
        p.press("2")
        p.hear("P04")
        p.until_hangup()
    assert sorted(s for (s,) in rows("SELECT status FROM call")) == ["completed", "queued"]
    assert redis.Redis.from_url(RD).zcard(callbacks.QUEUE) == 1


def test_silent_opening_hangs_up(client, settings):
    with dial(client) as ws:
        p = Phone(ws)
        p.start()
        p.hear("P01")
        p.hear("P02")
        p.until_hangup()
    assert rows("SELECT kind FROM event WHERE kind = 'no_response'") == [("no_response",)]


def test_callback_row_is_matched_by_provider_call_id(client, settings):
    with psycopg.connect(DB, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO call (phone_hash, status, provider_call_id) "
            "VALUES ('h', 'dialing', 'cb-7')"
        )
    with dial(client) as ws:
        p = Phone(ws)
        p.start(call_sid="cb-7")
        p.hear("P01")
        ws.close()
    assert rows("SELECT status FROM call") == [("completed",)]


def test_bad_token_is_refused(client, settings):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/exotel/ws/wrong-token") as ws:
            ws.receive_json()
    assert rows("SELECT count(*) FROM call") == [(0,)]


def test_status_callback_marks_unanswered_callbacks(client, settings):
    with psycopg.connect(DB, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO call (phone_hash, status, provider_call_id) "
            "VALUES ('h', 'dialing', 'cb-9')"
        )
    assert client.post("/exotel/status/wrong", data={"CallSid": "cb-9"}).status_code == 403
    r = client.post(f"/exotel/status/{TOKEN}", data={"CallSid": "cb-9", "Status": "no-answer"})
    assert r.status_code == 200
    assert rows("SELECT status FROM call") == [("no_answer",)]


def _to_story(p):
    for prompt, key in (("P01", "1"), ("P03", "1"), ("P06", "1"), ("P07", "1"), ("P08", "1")):
        p.hear(prompt)
        p.press(key)
    for prompt, key in (("P09", "4"), ("P10", "2"), ("P11", "1")):
        p.hear(prompt)
        p.press(key)
    p.hear("P12")


def test_story_ends_by_itself_after_silence(client, settings):
    with dial(client) as ws:
        p = Phone(ws)
        p.start()
        _to_story(p)
        p.speak(1)
        p.hear("P14")
        ws.close()
    [(path,)] = rows("SELECT recording_url FROM story")
    with wave.open(path) as w:
        assert w.getnframes() / 8000 == pytest.approx(1, abs=0.2)
    [(payload,)] = rows("SELECT payload FROM event WHERE kind = 'story_recorded'")
    assert payload["seconds"] == pytest.approx(1, abs=0.2)


def test_story_with_no_speech_moves_on(client, settings):
    with dial(client) as ws:
        p = Phone(ws)
        p.start()
        _to_story(p)
        p.hear("P14")
        ws.close()
    assert rows("SELECT count(*) FROM story") == [(0,)]
    assert rows("SELECT count(*) FROM event WHERE kind = 'story_empty'") == [(1,)]
