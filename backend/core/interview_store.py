"""Persist what happens during a live interview: call start/end, key presses, effects."""

import hashlib
import logging
import uuid
from datetime import timedelta
from pathlib import Path

from core import callbacks, store, story_job
from core.config import Settings
from core.dialogue.flow import Effect
from core.dialogue.prompts import PROMPTS, local_title
from core.phone import encrypt, normalize_indian_mobile, phone_hash
from core.timeutil import next_allowed, utcnow

log = logging.getLogger("interview")


CALLBACK_MATCH_MINUTES = 10


def begin_call(settings: Settings, provider_call_id: str | None, caller: str | None) -> str:
    """Find the callback row this live call belongs to, or create one for an inbound call.

    A callback is found by the provider's call id or, should the live call carry a different id
    than the dial request returned, by the number among callbacks placed in the last minutes.
    """
    if not (settings.phone_hash_secret and settings.phone_enc_key):
        raise RuntimeError("PHONE_HASH_SECRET or PHONE_ENC_KEY is empty")
    now = utcnow()
    number = normalize_indian_mobile(caller)
    # A call with no number at all gets a hash of its own, so pressing 9 affects only that call.
    who = number or caller or f"unknown:{provider_call_id or uuid.uuid4()}"
    h = phone_hash(who, settings.phone_hash_secret)
    with store.connect(settings.database_url) as conn:
        row, matched_by = None, None
        if provider_call_id:
            row = conn.execute(
                "SELECT id FROM call WHERE provider_call_id = %s ORDER BY callback_at DESC LIMIT 1",
                (provider_call_id,),
            ).fetchone()
            matched_by = "call_id"
        if row is None and number:
            row = conn.execute(
                "SELECT id FROM call WHERE phone_hash = %s AND status = 'dialing' "
                "AND callback_at > %s ORDER BY callback_at DESC LIMIT 1",
                (h, now - timedelta(minutes=CALLBACK_MATCH_MINUTES)),
            ).fetchone()
            matched_by = "number"
        if row:
            call_id = str(row["id"])
            store.update_call(conn, call_id, answered_at=now, status="in_call")
            store.add_event(conn, call_id, "answered", {"matched_by": matched_by})
            log.info("call %s: our callback was answered (matched by %s)", call_id[:8], matched_by)
            return call_id
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
        fields = {k: e.data.get(k) for k in store.STORY_FIELDS}
        store.save_story(conn, call_id, e.data["path"], **fields)
    elif e.kind == "readback":
        conn.execute(
            "UPDATE story SET confirmed = %s WHERE recording_url = ("
            "SELECT recording_url FROM story WHERE call_id = %s ORDER BY created_at DESC LIMIT 1)",
            (e.data["confirmed"] or "none", call_id),
        )
    elif e.kind == "callback_tomorrow":
        _callback_tomorrow(conn, settings, r, call)
    elif e.kind == "delete_and_block":
        h = call["phone_hash"]
        conn.execute(
            "INSERT INTO blocked_number (phone_hash, reason) VALUES (%s, 'caller_request') "
            "ON CONFLICT (phone_hash) DO NOTHING",
            (h,),
        )
        found = conn.execute("SELECT id FROM call WHERE phone_hash = %s", (h,)).fetchall()
        ids = [str(row["id"]) for row in found]
        conn.execute("DELETE FROM call WHERE phone_hash = %s", (h,))
        removed = _delete_recordings(settings.recordings_dir, ids)
        if r is not None and ids:
            r.delete(*(story_job.result_key(i) for i in ids))
        log.info(
            "caller asked for deletion; %d call(s) and %d recording(s) removed, number blocked",
            len(ids),
            removed,
        )


def _delete_recordings(folder: str, call_ids: list[str]) -> int:
    """Remove the story recordings of these calls (saved as <call id>-<time>.wav)."""
    removed = 0
    for call_id in call_ids:
        for path in Path(folder).glob(f"{call_id}-*.wav"):
            try:
                path.unlink(missing_ok=True)
                removed += 1
            except OSError as exc:
                log.warning("could not delete a recording: %s", type(exc).__name__)
    return removed


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


def occupation_title(settings: Settings, code: str, language: str = "hi-IN") -> str | None:
    if not code:
        return None
    with store.connect(settings.database_url) as conn:
        row = conn.execute(
            "SELECT title_en, title_hi, title_mr FROM nco WHERE nco_code = %s", (code,)
        ).fetchone()
    if not row:
        return None
    return local_title(language, row["title_en"], row["title_hi"], row["title_mr"])
