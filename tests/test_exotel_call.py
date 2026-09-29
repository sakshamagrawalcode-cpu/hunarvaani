"""A full Exotel Voicebot call over a real WebSocket, against real Postgres and Redis."""

import base64
import json
import os
import struct
import threading
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
from core import callbacks, store, story_job
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
        story_wait_seconds=0.5,
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


def test_nine_after_the_story_also_deletes_the_recordings(client, settings, audio_dir):
    folder = Path(settings.recordings_dir)
    folder.mkdir(parents=True, exist_ok=True)
    h = phone_hash("+919876543210", "hash-secret")
    [(old_id,)] = rows(
        "INSERT INTO call (phone_hash, status) VALUES (%s, 'completed') RETURNING id", h
    )
    (folder / f"{old_id}-20260101T000000.wav").write_bytes(b"old story")
    (folder / "someone-else-20260101T000000.wav").write_bytes(b"not theirs")
    redis.Redis.from_url(RD).rpush(story_job.result_key(str(old_id)), "{}")

    worker = fake_worker(audio_dir, ["7531", "7411"])
    with dial(client) as ws:
        p = Phone(ws)
        p.start()
        _to_story(p)
        p.speak(1)
        p.hear("DYN:0123456789abcdef01234567")
        assert len(list(folder.glob("*.wav"))) == 3
        p.press("9")
        p.hear("P18")
        p.until_hangup()
    worker.join(2)
    assert [f.name for f in folder.glob("*.wav")] == ["someone-else-20260101T000000.wav"]
    assert rows("SELECT count(*) FROM call") == [(0,)]
    assert rows("SELECT count(*) FROM story") == [(0,)]
    assert redis.Redis.from_url(RD).exists(story_job.result_key(str(old_id))) == 0


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


def test_callback_is_matched_by_number_when_the_call_id_differs(client, settings):
    h = phone_hash("+919876543210", "hash-secret")
    with psycopg.connect(DB, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO call (phone_hash, status, provider_call_id, callback_at) "
            "VALUES (%s, 'dialing', 'dial-api-sid', now())",
            (h,),
        )
    with dial(client) as ws:
        p = Phone(ws)
        p.start(call_sid="stream-sid")
        p.hear("P01")
        ws.close()
    assert rows("SELECT status FROM call") == [("completed",)]
    [(payload,)] = rows("SELECT payload FROM event WHERE kind = 'answered'")
    assert payload == {"matched_by": "number"}


def test_calls_without_a_number_do_not_share_a_hash(client, settings):
    for sid in ("anon-1", "anon-2"):
        with dial(client) as ws:
            p = Phone(ws)
            p.start(caller=None, call_sid=sid)
            p.hear("P01")
            ws.close()
    assert rows("SELECT count(DISTINCT phone_hash) FROM call") == [(2,)]


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


def fake_worker(audio_dir, candidates, transcript="मैं सिलाई का काम करती हूं"):
    """Answer one story job the way the real worker would."""
    r = redis.Redis.from_url(RD)

    def serve():
        item = r.blpop(story_job.QUEUE, timeout=10)
        if not item:
            return
        job = json.loads(item[1])
        prompt = None
        if candidates:
            prompt = "DYN:0123456789abcdef01234567"
            (audio_dir / "dyn").mkdir(exist_ok=True)
            with wave.open(str(audio_dir / "dyn" / "0123456789abcdef01234567.wav"), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(8000)
                w.writeframes(b"\x00\x00" * 400)
        story_job.publish(
            r,
            job["call_id"],
            {
                "transcript": transcript,
                "candidates": candidates,
                "prompt": prompt,
                "scores": [{"code": c, "score": 0.7} for c in candidates]
                or [{"code": "5142", "score": 0.1}],
                "stt_ms": 900,
                "search_ms": 12,
            },
        )

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    return t


def test_story_is_read_back_and_confirmed(client, settings, audio_dir):
    worker = fake_worker(audio_dir, ["7531", "7411"])
    with dial(client) as ws:
        p = Phone(ws)
        p.start()
        _to_story(p)
        p.speak(1)
        heard = p.hear("DYN:0123456789abcdef01234567")
        assert "P17" in heard and "P14" not in heard
        p.press("1")
        p.until_hangup()
    worker.join(2)
    [(transcript, top1, top2, confirmed, stt_ms)] = rows(
        "SELECT transcript, top1, top2, confirmed, stt_ms FROM story"
    )
    assert (transcript, top1, top2, confirmed, stt_ms) == (
        "मैं सिलाई का काम करती हूं",
        "7531",
        "7411",
        "7531",
        900,
    )
    assert dict(rows("SELECT step, value FROM answer"))["occupation"] == "7531"
    [(payload,)] = rows("SELECT payload FROM event WHERE kind = 'readback'")
    assert payload == {"key": "1", "confirmed": "7531", "candidates": ["7531", "7411"]}


def test_unclear_story_offers_the_trade_list(client, settings, audio_dir):
    worker = fake_worker(audio_dir, [], transcript="आज मौसम अच्छा है")
    with dial(client) as ws:
        p = Phone(ws)
        p.start()
        _to_story(p)
        p.speak(1)
        p.hear("P14")
        ws.close()
    worker.join(2)
    [(transcript, top1, confirmed)] = rows("SELECT transcript, top1, confirmed FROM story")
    assert (transcript, top1, confirmed) == ("आज मौसम अच्छा है", "5142", None)


def test_no_worker_answer_in_time_offers_the_trade_list(client, settings):
    with dial(client) as ws:
        p = Phone(ws)
        p.start()
        _to_story(p)
        p.speak(1)
        p.hear("P14")
        ws.close()
    [(transcript,)] = rows("SELECT transcript FROM story")
    assert transcript is None


def test_late_worker_answer_is_still_saved(client, settings):
    with dial(client) as ws:
        p = Phone(ws)
        p.start()
        _to_story(p)
        p.speak(1)
        p.hear("P14")
        ws.close()
    assert rows("SELECT transcript FROM story") == [(None,)]
    job = json.loads(redis.Redis.from_url(RD).lpop(story_job.QUEUE))
    late = {
        "transcript": "मैं सिलाई का काम करती हूं",
        "scores": [{"code": "7531", "score": 0.8}, {"code": "7411", "score": 0.1}],
        "stt_ms": 7000,
        "search_ms": 30,
    }
    with store.connect(DB) as conn:
        assert story_job.save(conn, job, late) is True
    assert rows("SELECT transcript, top1, top2, stt_ms FROM story") == [
        ("मैं सिलाई का काम करती हूं", "7531", "7411", 7000)
    ]


def test_story_saves_merge_in_either_order_and_skip_deleted_calls(settings):
    [(cid,)] = rows("INSERT INTO call (phone_hash, status) VALUES ('h', 'in_call') RETURNING id")
    with store.connect(DB) as conn:
        store.save_story(conn, str(cid), "/r/a.wav", transcript="खेती करता हूं", top1="9211")
        store.save_story(conn, str(cid), "/r/a.wav", transcript=None, top1=None, stt_ms=None)
        gone = {"call_id": "00000000-0000-0000-0000-000000000000", "path": "/r/b.wav"}
        assert story_job.save(conn, gone, {"transcript": "x"}) is False
    assert rows("SELECT transcript, top1 FROM story") == [("खेती करता हूं", "9211")]


def test_logs_hide_the_exotel_token():
    import logging

    record = logging.LogRecord(
        "uvicorn.error",
        logging.INFO,
        "",
        0,
        '%s - "WebSocket %s" [accepted]',
        ("1.2.3.4:5", f"/exotel/ws/{TOKEN}"),
        None,
    )
    main._HideTokens().filter(record)
    assert TOKEN not in record.getMessage() and "/exotel/ws/<token>" in record.getMessage()


@pytest.fixture
def fake_tts(monkeypatch, audio_dir):
    from apps.voice import exotel

    spoken = []

    def ensure(text, language, api_key, speaker, folder):
        spoken.append(text)
        (folder / "dyn").mkdir(exist_ok=True)
        with wave.open(str(folder / "dyn" / "aaaabbbbccccdddd11112222.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(8000)
            w.writeframes(b"\x00\x00" * 400)
        return "DYN:aaaabbbbccccdddd11112222"

    monkeypatch.setattr(exotel.dynprompt, "ensure", ensure)
    return spoken


def _seed_titles():
    with psycopg.connect(DB, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO nco (nco_code, title_en, title_hi, aliases) VALUES "
            "('7422', 'Mobile', 'मोबाइल मिस्त्री', 'mobile') ON CONFLICT DO NOTHING"
        )


def test_call_ends_with_the_spoken_summary(client, settings, fake_tts):
    _seed_titles()
    with dial(client) as ws:
        p = Phone(ws)
        p.start()
        _to_story(p)
        p.hear("P14")
        p.press("5")
        p.hear("DYN:aaaabbbbccccdddd11112222")
        p.until_hangup()
    [text] = fake_tts
    assert "दसवीं पास, मोबाइल मिस्त्री" in text and "ओटीपी" in text
    [(payload,)] = rows("SELECT payload FROM event WHERE kind = 'summary'")
    assert payload["text"] == text


def test_summary_falls_back_to_p20_when_tts_fails(client, settings, monkeypatch):
    from apps.voice import exotel

    def broken(*a, **k):
        raise RuntimeError("sarvam down")

    monkeypatch.setattr(exotel.dynprompt, "ensure", broken)
    with dial(client) as ws:
        p = Phone(ws)
        p.start()
        _to_story(p)
        p.hear("P14")
        p.press("2")
        p.hear("P20")
        p.until_hangup()
    assert rows("SELECT status FROM call") == [("completed",)]


def test_calls_page_needs_the_password_and_hides_numbers(client, settings, monkeypatch):
    import dataclasses

    monkeypatch.setattr(main, "settings", dataclasses.replace(settings, calls_page_password="pw"))
    with dial(client) as ws:
        p = Phone(ws)
        p.start()
        p.hear("P01")
        ws.close()
    with psycopg.connect(DB, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO story (call_id, transcript) "
            "SELECT id, '<script>alert(1)</script>' FROM call"
        )
    assert client.get("/calls").status_code == 401
    assert client.get("/calls", auth=("admin", "wrong")).status_code == 401
    r = client.get("/calls", auth=("admin", "pw"))
    assert r.status_code == 200
    assert "xxxxxx3210" in r.text and "9876543210" not in r.text
    assert "<script>alert(1)</script>" not in r.text and "&lt;script&gt;" in r.text


def test_calls_page_is_closed_without_a_password(client, settings):
    assert client.get("/calls", auth=("admin", "")).status_code == 503


def test_slow_worker_answer_does_not_hit_the_redis_socket_timeout():
    """The api's Redis client times out a socket read after 3 s; the story wait is longer."""
    key = story_job.result_key("slow")
    redis.Redis.from_url(RD).delete(key)
    short = redis.Redis.from_url(RD, socket_timeout=2)

    def late_answer():
        time.sleep(1.8)
        redis.Redis.from_url(RD).rpush(key, json.dumps({"transcript": "देर से"}))

    threading.Thread(target=late_answer).start()
    assert story_job.wait_result(short, "slow", 3) == {"transcript": "देर से"}
    started = time.monotonic()
    assert story_job.wait_result(short, "none", 2.5) is None
    assert 2.0 < time.monotonic() - started < 3.5


def test_story_queue_failure_offers_the_trade_list(client, settings, monkeypatch):
    def broken(*args):
        raise redis.exceptions.TimeoutError("Timeout reading from socket")

    monkeypatch.setattr(story_job, "wait_result", broken)
    with dial(client) as ws:
        p = Phone(ws)
        p.start()
        _to_story(p)
        p.speak(1)
        p.hear("P14")
        ws.close()
