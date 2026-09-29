"""Persist what happens during a live interview: call start/end, key presses, effects."""

import hashlib
import logging
from datetime import timedelta

from core import callbacks, store
from core.config import Settings
from core.dialogue.flow import Effect
from core.dialogue.prompts import PROMPTS
from core.phone import encrypt, normalize_indian_mobile, phone_hash
from core.timeutil import next_allowed, utcnow

log = logging.getLogger("interview")


def begin_call(settings: Settings, provider_call_id: str | None, caller: str | None) -> str:
    """Find the callback row this live call belongs to, or create one for an inbound call."""
    if not (settings.phone_hash_secret and settings.phone_enc_key):
        raise RuntimeError("PHONE_HASH_SECRET or PHONE_ENC_KEY is empty")
    now = utcnow()
    with store.connect(settings.database_url) as conn:
        if provider_call_id:
            row = conn.execute(
                "SELECT id FROM call WHERE provider_call_id = %s ORDER BY callback_at DESC LIMIT 1",
                (provider_call_id,),
            ).fetchone()
            if row:
                call_id = str(row["id"])
                store.update_call(conn, call_id, answered_at=now, status="in_call")
                store.add_event(conn, call_id, "answered")
                return call_id
        number = normalize_indian_mobile(caller)
        h = phone_hash(number or (caller or "unknown"), settings.phone_hash_secret)
        row = conn.execute(
            "INSERT INTO call (phone_hash, phone_enc, provider_call_id, answered_at, status) "
            "VALUES (%s, %s, %s, %s, 'in_call') RETURNING id",
            (h, encrypt(number, settings.phone_enc_key) if number else None, provider_call_id, now),
        ).fetchone()
        call_id = str(row["id"])
        store.add_event(conn, call_id, "inbound_call", {"indian_mobile": number is not None})
        return call_id


def log_event(settings: Settings, call_id: str, kind: str, payload: dict) -> None:
    with store.connect(settings.database_url) as conn:
        if store.get_call(conn, call_id):
            store.add_event(conn, call_id, kind, payload)


def end_call(settings: Settings, call_id: str) -> None:
    now = utcnow()
    with store.connect(settings.database_url) as conn:
        call = store.get_call(conn, call_id)
        if call is None:
            return
        duration = int((now - call["answered_at"]).total_seconds()) if call["answered_at"] else 0
        status = "completed" if call["status"] == "in_call" else call["status"]
        store.update_call(conn, call_id, ended_at=now, duration_seconds=duration, status=status)
        store.add_event(conn, call_id, "call_ended", {"duration": duration})


def prompt_hash(prompt_id: str, language: str = "hi-IN") -> str:
    text = PROMPTS.get(language, PROMPTS["hi-IN"]).get(prompt_id, "")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def apply_effects(settings: Settings, r, call_id: str, effects: list[Effect]) -> None:
    if not effects:
        return
    with store.connect(settings.database_url) as conn:
        call = store.get_call(conn, call_id)
        if call is None:
            return
        for e in effects:
            _apply(conn, settings, r, call, e)
            if e.kind == "delete_and_block":
                return
            store.add_event(conn, call_id, e.kind, e.data)


def _apply(conn, settings: Settings, r, call: dict, e: Effect) -> None:
    call_id = str(call["id"])
    if e.kind == "answer":
        conn.execute(
            "INSERT INTO answer (call_id, step, key_pressed, value) VALUES (%s, %s, %s, %s)",
            (call_id, e.data["step"], e.data["key"], e.data["value"]),
        )
    elif e.kind == "skipped":
        conn.execute(
            "INSERT INTO answer (call_id, step, key_pressed, value) "
            "VALUES (%s, %s, NULL, 'skipped')",
            (call_id, e.data["step"]),
        )
    elif e.kind == "consent":
        conn.execute(
            "INSERT INTO consent (call_id, kind, granted, prompt_version, hash) "
            "VALUES (%s, %s, %s, %s, %s)",
            (
                call_id,
                e.data["kind"],
                e.data["granted"],
                e.data["prompt_id"],
                prompt_hash(e.data["prompt_id"], call["language"] or "hi-IN"),
            ),
        )
    elif e.kind == "language":
        store.update_call(conn, call_id, language=e.data["code"])
    elif e.kind == "keypad_only":
        store.update_call(conn, call_id, keypad_only=True)
    elif e.kind == "human_flag":
        store.update_call(conn, call_id, human_flag=True)
    elif e.kind == "story_recorded":
        d = e.data
        conn.execute(
            "INSERT INTO story (call_id, recording_url, transcript, top1, top2, stt_ms, search_ms) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                call_id,
                d["path"],
                d.get("transcript"),
                d.get("top1"),
                d.get("top2"),
                d.get("stt_ms"),
                d.get("search_ms"),
            ),
        )
    elif e.kind == "readback":
        conn.execute(
            "UPDATE story SET confirmed = %s WHERE call_id = %s",
            (e.data["confirmed"] or "none", call_id),
        )
    elif e.kind == "callback_tomorrow":
        _callback_tomorrow(conn, settings, r, call)
    elif e.kind == "delete_and_block":
        conn.execute(
            "INSERT INTO blocked_number (phone_hash, reason) VALUES (%s, 'caller_request') "
            "ON CONFLICT (phone_hash) DO NOTHING",
            (call["phone_hash"],),
        )
        conn.execute("DELETE FROM call WHERE phone_hash = %s", (call["phone_hash"],))
        log.info("caller asked for deletion; data removed and number blocked")


def _callback_tomorrow(conn, settings: Settings, r, call: dict) -> None:
    if not call["phone_enc"]:
        return
    due = next_allowed(utcnow() + timedelta(days=1), settings.quiet_hours)
    row = conn.execute(
        "INSERT INTO call (phone_hash, phone_enc, missed_at, status) "
        "VALUES (%s, %s, %s, 'queued') RETURNING id",
        (call["phone_hash"], call["phone_enc"], utcnow()),
    ).fetchone()
    new_id = str(row["id"])
    store.add_event(conn, new_id, "callback_requested", {"from_call": str(call["id"])})
    callbacks.schedule(r, new_id, due)


NOT_CONNECTED = {"busy", "no-answer", "failed", "canceled"}


def provider_status(settings: Settings, provider_call_id: str, status: str) -> None:
    """Exotel's StatusCallback: record callbacks that never connected."""
    status = (status or "").lower()
    with store.connect(settings.database_url) as conn:
        row = conn.execute(
            "SELECT id, answered_at FROM call WHERE provider_call_id = %s", (provider_call_id,)
        ).fetchone()
        if row is None:
            return
        call_id = str(row["id"])
        store.add_event(conn, call_id, "provider_status", {"status": status})
        if status in NOT_CONNECTED and row["answered_at"] is None:
            store.update_call(
                conn,
                call_id,
                status="no_answer" if status != "failed" else "dial_failed",
                ended_at=utcnow(),
            )


def occupation_title(settings: Settings, code: str) -> str | None:
    if not code:
        return None
    with store.connect(settings.database_url) as conn:
        row = conn.execute("SELECT title_hi FROM nco WHERE nco_code = %s", (code,)).fetchone()
    return row["title_hi"] if row else None
