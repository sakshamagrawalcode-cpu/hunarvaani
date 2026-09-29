"""End-to-end tests of Step 7 against real Postgres and Redis.

Set TEST_DATABASE_URL and TEST_REDIS_URL to run them; they are skipped otherwise.
The test database is wiped, so never point these at real data.
"""

import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
import pytest
import redis
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from apps.voice import calls, main
from apps.worker.main import process_one
from core import callbacks
from core.config import Settings
from core.phone import phone_hash
from core.timeutil import IST
from tests.plivo_signing import plivo_headers

DB = os.environ.get("TEST_DATABASE_URL")
RD = os.environ.get("TEST_REDIS_URL")
pytestmark = pytest.mark.skipif(not (DB and RD), reason="TEST_DATABASE_URL/TEST_REDIS_URL unset")

BASE = "https://hv.test"
TOKEN = "test-auth-token"
NUMBER = "919876543210"


@pytest.fixture(scope="module")
def schema():
    with psycopg.connect(DB, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        for f in sorted((Path(__file__).resolve().parent.parent / "db").glob("*.sql")):
            conn.execute(f.read_text(encoding="utf-8"))


@pytest.fixture
def settings(schema, monkeypatch):
    s = Settings(
        public_base_url=BASE,
        database_url=DB,
        redis_url=RD,
        default_language="hi-IN",
        languages=("hi-IN",),
        callback_delay_seconds=5,
        max_triggers_per_day=3,
        daily_call_budget=100,
        quiet_hours="",
        plivo_auth_id="id",
        plivo_auth_token=TOKEN,
        plivo_number="+918000000000",
        phone_hash_secret="hash-secret",
        phone_enc_key=Fernet.generate_key().decode(),
    )
    with psycopg.connect(DB, autocommit=True) as conn:
        conn.execute("TRUNCATE call, answer, consent, story, event, blocked_number CASCADE")
    redis.Redis.from_url(RD).flushdb()
    monkeypatch.setattr(main, "settings", s)
    main._redis_for.cache_clear()
    return s


@pytest.fixture
def client(settings):
    return TestClient(main.app)


def post(client, path, params, token=TOKEN):
    return client.post(path, data=params, headers=plivo_headers(BASE + path, params, token))


def missed(client, number=NUMBER, call_uuid=None):
    params = {"From": number, "To": "918000000000", "CallUUID": call_uuid or str(uuid.uuid4())}
    return post(client, "/pv/answer", params)


def rows(sql, *args):
    with psycopg.connect(DB) as conn:
        return conn.execute(sql, args).fetchall()


class FakeDialer:
    def __init__(self, fail=False):
        self.made, self.fail = [], fail

    def dial(self, number, call_id):
        if self.fail:
            raise RuntimeError("provider down")
        self.made.append((number, call_id))
        return "prov-" + str(len(self.made))


def later(seconds=10):
    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


def test_missed_call_is_rejected_and_queued(client, settings):
    r = missed(client)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/xml")
    assert r.text == '<Response><Hangup reason="rejected"/></Response>'

    [(status, enc, h)] = rows("SELECT status, phone_enc, phone_hash FROM call")
    assert status == "queued"
    assert b"9876543210" not in bytes(enc)
    assert h == phone_hash("+919876543210", settings.phone_hash_secret)
    assert redis.Redis.from_url(RD).zcard(callbacks.QUEUE) == 1


def test_bad_signature_is_403_and_stores_nothing(client):
    params = {"From": NUMBER, "CallUUID": "x"}
    r = client.post(
        "/pv/answer", data=params, headers=plivo_headers(BASE + "/pv/answer", params, "wrong")
    )
    assert r.status_code == 403
    r = client.post("/pv/answer", data=params)
    assert r.status_code == 403
    assert rows("SELECT count(*) FROM call") == [(0,)]


def test_repeated_call_uuid_is_ignored(client):
    missed(client, call_uuid="same-uuid")
    missed(client, call_uuid="same-uuid")
    assert rows("SELECT count(*) FROM call") == [(1,)]


def test_fourth_missed_call_in_a_day_gets_no_callback(client):
    for _ in range(4):
        assert missed(client).status_code == 200
    statuses = [s for (s,) in rows("SELECT status FROM call ORDER BY missed_at")]
    assert statuses == ["queued", "queued", "queued", "limit_reached"]
    assert redis.Redis.from_url(RD).zcard(callbacks.QUEUE) == 3


def test_non_indian_number_is_ignored(client):
    missed(client, number="14155550123")
    assert rows("SELECT count(*) FROM call") == [(0,)]


def test_blocked_number_gets_no_callback(client, settings):
    h = phone_hash("+919876543210", settings.phone_hash_secret)
    with psycopg.connect(DB, autocommit=True) as conn:
        conn.execute("INSERT INTO blocked_number (phone_hash, reason) VALUES (%s, 'test')", (h,))
    missed(client)
    assert rows("SELECT count(*) FROM call") == [(0,)]


def test_missed_call_in_quiet_hours_waits_until_nine(client, settings, monkeypatch):
    monkeypatch.setattr(
        main, "settings", Settings(**{**settings.__dict__, "quiet_hours": "21:00-09:00"})
    )
    fixed = datetime(2026, 10, 10, 22, 30, tzinfo=IST)
    monkeypatch.setattr(calls, "utcnow", lambda: fixed.astimezone(timezone.utc))
    missed(client)
    [(status,)] = rows("SELECT status FROM call")
    assert status == "queued_quiet_hours"
    [(_, score)] = redis.Redis.from_url(RD).zrange(callbacks.QUEUE, 0, -1, withscores=True)
    assert datetime.fromtimestamp(score, IST) == datetime(2026, 10, 11, 9, 0, tzinfo=IST)


def test_worker_places_callback(client, settings):
    missed(client)
    fake = FakeDialer()
    r = redis.Redis.from_url(RD)
    assert process_one(r, settings, fake, now=later()) is True
    assert process_one(r, settings, fake, now=later()) is False

    [(number, dialled_id)] = fake.made
    [(call_id, status, prov)] = rows("SELECT id::text, status, provider_call_id FROM call")
    assert (number, dialled_id) == ("+919876543210", call_id)
    assert (status, prov) == ("dialing", "prov-1")


def test_worker_waits_until_the_callback_is_due(client, settings):
    missed(client)
    fake = FakeDialer()
    assert process_one(redis.Redis.from_url(RD), settings, fake, now=later(0)) is False
    assert fake.made == []


def test_worker_respects_quiet_hours(client, settings):
    missed(client)
    quiet = Settings(**{**settings.__dict__, "quiet_hours": "21:00-09:00"})
    night = datetime(2030, 1, 1, 23, 0, tzinfo=IST)
    fake = FakeDialer()
    assert process_one(redis.Redis.from_url(RD), quiet, fake, now=night) is True
    assert fake.made == []
    assert rows("SELECT status FROM call") == [("queued_quiet_hours",)]
    [(_, score)] = redis.Redis.from_url(RD).zrange(callbacks.QUEUE, 0, -1, withscores=True)
    assert datetime.fromtimestamp(score, IST) == datetime(2030, 1, 2, 9, 0, tzinfo=IST)


def test_worker_respects_daily_budget(client, settings):
    missed(client)
    missed(client, number="919876500000")
    tight = Settings(**{**settings.__dict__, "daily_call_budget": 1})
    fake = FakeDialer()
    r = redis.Redis.from_url(RD)
    process_one(r, tight, fake, now=later())
    process_one(r, tight, fake, now=later())
    assert len(fake.made) == 1
    assert sorted(s for (s,) in rows("SELECT status FROM call")) == ["budget_exceeded", "dialing"]


def test_worker_records_dial_failure(client, settings):
    missed(client)
    process_one(redis.Redis.from_url(RD), settings, FakeDialer(fail=True), now=later())
    assert rows("SELECT status FROM call") == [("dial_failed",)]
    assert rows("SELECT kind FROM event WHERE kind = 'dial_failed'") == [("dial_failed",)]


def test_answer_then_hangup_records_the_call(client, settings):
    missed(client)
    process_one(redis.Redis.from_url(RD), settings, FakeDialer(), now=later())
    [(call_id,)] = rows("SELECT id::text FROM call")

    r = post(client, f"/pv/ivr/start?call={call_id}", {"CallUUID": "out-1", "From": "x"})
    assert r.status_code == 200
    assert f"<Play>{BASE}/audio/hi/P01.wav</Play>" in r.text

    r = post(client, f"/pv/hangup?call={call_id}", {"CallUUID": "out-1", "Duration": "12"})
    assert r.status_code == 200
    [(status, dur, answered, ended)] = rows(
        "SELECT status, duration_seconds, answered_at IS NOT NULL, ended_at IS NOT NULL FROM call"
    )
    assert (status, dur, answered, ended) == ("completed", 12, True, True)


def test_unanswered_callback_is_marked_no_answer(client, settings):
    missed(client)
    process_one(redis.Redis.from_url(RD), settings, FakeDialer(), now=later())
    [(call_id,)] = rows("SELECT id::text FROM call")
    post(client, f"/pv/hangup?call={call_id}", {"HangupCause": "NO_ANSWER", "Duration": "0"})
    assert rows("SELECT status FROM call") == [("no_answer",)]


def test_signed_url_for_one_call_cannot_touch_another(client, settings):
    missed(client)
    [(call_id,)] = rows("SELECT id::text FROM call")
    params = {"CallUUID": "out-1"}
    headers = plivo_headers(f"{BASE}/pv/hangup?call={call_id}", params, TOKEN)
    r = client.post(f"/pv/hangup?call={uuid.uuid4()}", data=params, headers=headers)
    assert r.status_code == 403


def test_unknown_or_malformed_call_id_hangs_up(client):
    r = post(client, "/pv/ivr/start?call=not-a-uuid", {"CallUUID": "x"})
    assert r.text == "<Response><Hangup/></Response>"
    r = post(client, f"/pv/ivr/start?call={uuid.uuid4()}", {"CallUUID": "x"})
    assert r.text == "<Response><Hangup/></Response>"
