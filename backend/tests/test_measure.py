"""The slide numbers (step A14) are counted only from saved call data."""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg
import pytest
from psycopg.types.json import Jsonb

from core import measure, store

T0 = datetime(2026, 9, 30, 10, 0, tzinfo=timezone.utc)


def at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


def full_call(cid="a") -> measure.CallData:
    c = measure.CallData(cid, "hi-IN", "completed", 230, T0)
    c.events = [
        ("language", {"code": "hi-IN"}, at(5)),
        ("say", {"step": "q_age"}, at(40)),
        ("say", {"step": "story"}, at(100)),
        ("recording", {"seconds": 20.0, "stopped_by": "silence"}, at(125)),
        ("say", {"step": "story", "prompts": []}, at(133)),  # P30 "stay on the line"
        ("story_recorded", {"seconds": 20.0}, at(137)),
        ("say", {"step": "readback"}, at(137.5)),
        ("readback", {"key": "1", "confirmed": "7531", "candidates": ["7531", "7533"]}, at(150)),
        ("recommendations", {"options": [], "spoken": True}, at(160)),
        ("option_heard", {"rank": 2}, at(180)),
        ("interest", {"rank": 2, "course_id": "U0001"}, at(200)),
        ("say", {"step": "goodbye"}, at(210)),
    ]
    c.answers = [("q_age", "25-34"), ("q_lean", "job"), ("occupation", "7531")]
    c.stories = [{"stt_ms": 2400, "search_ms": 300, "llm": {"occupations": ["7531"]}}]
    c.recommendations = [
        {"details": {"kind": "upskill"}},
        {"details": {"kind": "certificate"}},
        {"details": {"kind": "startup"}},
    ]
    return c


def dropped_call() -> measure.CallData:
    c = measure.CallData("b", "mr-IN", "completed", 70, at(3600))
    c.events = [
        ("language", {"code": "mr-IN"}, at(3605)),
        ("problem", {"what": "Call ended early: the connection to Exotel closed"}, at(3670)),
    ]
    return c


def test_funnel_and_numbers_come_from_the_events():
    m = measure.summarize([full_call(), dropped_call()], lags=[1.1, 1.0, 3.2])
    funnel = dict(m["funnel"])
    assert funnel["call answered"] == 2
    assert funnel["language chosen"] == 2
    assert funnel["consents done"] == 1
    assert funnel["reached the goodbye"] == 1
    assert funnel["an option chosen"] == 1
    assert m["ended_early"] == ["the connection to Exotel closed"]
    assert m["story_wait"]["median"] == pytest.approx(12.5)  # recording end → read-back
    assert m["confirmed"] == m["confirmed_first"] == 1
    assert m["option_kinds"] == {"certificate": 1, "startup": 1, "upskill": 1}
    assert m["lags"]["max"] == 3.2
    text = measure.report(m)
    assert text.startswith("Measured on 2 real calls, 30 Sep 2026 to 30 Sep 2026.")
    assert "1 of 2 (50%)" in text


def test_missing_data_is_said_not_invented():
    text = measure.report(measure.summarize([dropped_call()]))
    assert "speech-to-text (Sarvam):  no data" in text
    assert "confirmed one of the 3:   0 of 0" in text
    assert measure.report(measure.summarize([])).startswith("No answered calls")


def test_played_lags_reads_both_log_forms():
    lines = [
        "INFO exotel played P05 (+1.1 s)",
        "WARNING exotel played P21 3.4 s after our last audio (slow network?)",
        "INFO call abcd: asking q_age",
    ]
    assert measure.played_lags(lines) == [1.1, 3.4]


DB = os.environ.get("TEST_DATABASE_URL")


@pytest.mark.skipif(not DB, reason="TEST_DATABASE_URL unset")
def test_load_reads_a_saved_call():
    with psycopg.connect(DB, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        for f in sorted(
            (Path(__file__).resolve().parents[2] / "database" / "schema").glob("*.sql")
        ):
            conn.execute(f.read_text(encoding="utf-8"))
    with store.connect(DB) as conn:
        cid = conn.execute(
            "INSERT INTO call (phone_hash, answered_at, duration_seconds, language, status) "
            "VALUES ('h', %s, 230, 'hi-IN', 'completed') RETURNING id",
            (T0,),
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO event (call_id, kind, payload, created_at) VALUES (%s, 'say', %s, %s)",
            (cid, Jsonb({"step": "goodbye"}), at(200)),
        )
        conn.execute(
            "INSERT INTO call (phone_hash, answered_at, duration_seconds, status) "
            "VALUES ('h2', %s, 5, 'completed')",
            (at(10),),
        )
        calls = measure.load(conn, min_seconds=10)
    assert [c.duration for c in calls] == [230]
    assert "goodbye" in calls[0].steps()
