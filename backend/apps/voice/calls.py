"""Plivo webhook handlers. Each takes already-verified form params and returns Plivo XML."""

import logging
from datetime import timedelta

from core import callbacks, store
from core.config import Settings
from core.phone import encrypt, last4, normalize_indian_mobile, phone_hash
from core.plivo_xml import HANGUP, REJECT, play_then_hangup
from core.timeutil import in_quiet_hours, ist_day, next_allowed, utcnow

log = logging.getLogger("voice")


def missed_call(params: dict, settings: Settings, r) -> str:
    """Someone dialled our number: reject the call (free for them) and queue a callback."""
    now = utcnow()
    inbound_uuid = params.get("CallUUID") or None
    if inbound_uuid and not callbacks.first_seen(r, inbound_uuid):
        return REJECT

    number = normalize_indian_mobile(params.get("From"))
    if number is None:
        log.info("missed call ignored: not an Indian mobile number")
        return REJECT
    if not (settings.phone_hash_secret and settings.phone_enc_key):
        log.error("missed call ignored: PHONE_HASH_SECRET or PHONE_ENC_KEY is empty")
        return REJECT

    h = phone_hash(number, settings.phone_hash_secret)
    with store.connect(settings.database_url) as conn:
        if store.is_blocked(conn, h):
            log.info("missed call from blocked number %s ignored", last4(number))
            return REJECT

        triggers = callbacks.count_trigger(r, h, ist_day(now))
        if triggers > settings.max_triggers_per_day:
            call_id = store.create_call(
                conn,
                phone_hash=h,
                phone_enc=None,
                inbound_uuid=inbound_uuid,
                status="limit_reached",
                missed_at=now,
            )
            if call_id:
                store.add_event(conn, call_id, "missed_call", {"triggers_today": triggers})
            log.info("missed call from %s: daily limit reached (%d)", last4(number), triggers)
            return REJECT

        earliest = now + timedelta(seconds=settings.callback_delay_seconds)
        due = next_allowed(earliest, settings.quiet_hours)
        quiet = in_quiet_hours(earliest, settings.quiet_hours)
        call_id = store.create_call(
            conn,
            phone_hash=h,
            phone_enc=encrypt(number, settings.phone_enc_key),
            inbound_uuid=inbound_uuid,
            status="queued_quiet_hours" if quiet else "queued",
            missed_at=now,
        )
        if call_id is None:
            return REJECT
        store.add_event(
            conn,
            call_id,
            "missed_call",
            {"triggers_today": triggers, "callback_due": due.isoformat(), "quiet_hours": quiet},
        )
    callbacks.schedule(r, call_id, due)
    log.info("missed call from %s: callback queued for %s", last4(number), due.isoformat())
    return REJECT


def ivr_start(call_id: str | None, settings: Settings) -> str:
    """Our callback was answered. Step 8 replaces this with the full interview."""
    if not call_id:
        return HANGUP
    with store.connect(settings.database_url) as conn:
        call = store.get_call(conn, call_id)
        if call is None:
            return HANGUP
        if call["answered_at"] is None:
            store.update_call(conn, call_id, answered_at=utcnow(), status="answered")
            store.add_event(conn, call_id, "answered")
    return play_then_hangup(f"{settings.public_base_url}/audio/hi/P01.wav")


def hangup(call_id: str | None, params: dict, settings: Settings) -> None:
    if not call_id:
        return
    with store.connect(settings.database_url) as conn:
        call = store.get_call(conn, call_id)
        if call is None:
            return
        try:
            duration = int(params.get("Duration") or 0)
        except ValueError:
            duration = 0
        cause = params.get("HangupCause") or ""
        status = "completed" if call["answered_at"] else "no_answer"
        store.update_call(
            conn, call_id, ended_at=utcnow(), duration_seconds=duration, status=status
        )
        store.add_event(conn, call_id, "hangup", {"cause": cause, "duration": duration})
