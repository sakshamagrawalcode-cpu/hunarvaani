import logging
import time

import redis

from core import callbacks, store
from core.config import Settings, load_settings
from core.phone import decrypt, last4
from core.timeutil import in_quiet_hours, ist_day, next_allowed, utcnow

logging.basicConfig(level=logging.INFO, format="%(asctime)s worker %(message)s")
log = logging.getLogger("worker")

DIALABLE = {"queued", "queued_quiet_hours"}


def _request_uuid(resp) -> str | None:
    value = getattr(resp, "request_uuid", None)
    if value is None and isinstance(resp, dict):
        value = resp.get("request_uuid")
    if isinstance(value, list):
        value = value[0] if value else None
    return str(value) if value else None


def process_one(r, settings: Settings, plivo_client, now=None) -> bool:
    """Handle at most one due callback. Returns False when nothing was due."""
    now = now or utcnow()
    call_id = callbacks.pop_due(r, now)
    if call_id is None:
        return False

    with store.connect(settings.database_url) as conn:
        call = store.get_call(conn, call_id)
        if call is None or call["status"] not in DIALABLE:
            return True

        if in_quiet_hours(now, settings.quiet_hours):
            due = next_allowed(now, settings.quiet_hours)
            callbacks.schedule(r, call_id, due)
            store.update_call(conn, call_id, status="queued_quiet_hours")
            return True

        if store.is_blocked(conn, call["phone_hash"]):
            store.update_call(conn, call_id, status="blocked")
            store.add_event(conn, call_id, "callback_skipped", {"reason": "blocked"})
            return True

        if not callbacks.take_budget(r, ist_day(now), settings.daily_call_budget):
            store.update_call(conn, call_id, status="budget_exceeded")
            store.add_event(conn, call_id, "callback_skipped", {"reason": "daily_budget"})
            log.warning("daily call budget reached; callback %s skipped", call_id)
            return True

        number = decrypt(call["phone_enc"], settings.phone_enc_key)
        base = settings.public_base_url
        try:
            resp = plivo_client.calls.create(
                from_=settings.plivo_number,
                to_=number,
                answer_url=f"{base}/pv/ivr/start?call={call_id}",
                answer_method="POST",
                hangup_url=f"{base}/pv/hangup?call={call_id}",
                hangup_method="POST",
                ring_timeout=30,
            )
        except Exception as exc:
            store.update_call(conn, call_id, status="dial_failed")
            store.add_event(
                conn, call_id, "dial_failed", {"error": f"{type(exc).__name__}: {exc}"[:300]}
            )
            log.warning("callback to %s failed: %s", last4(number), type(exc).__name__)
            return True

        store.update_call(
            conn,
            call_id,
            callback_at=now,
            status="dialing",
            plivo_request_uuid=_request_uuid(resp),
        )
        store.add_event(conn, call_id, "callback_placed")
        log.info("callback placed to %s", last4(number))
    return True


def _missing_config(settings: Settings) -> list[str]:
    required = {
        "PUBLIC_BASE_URL": settings.public_base_url,
        "PLIVO_AUTH_ID": settings.plivo_auth_id,
        "PLIVO_AUTH_TOKEN": settings.plivo_auth_token,
        "PLIVO_NUMBER": settings.plivo_number,
        "PHONE_ENC_KEY": settings.phone_enc_key,
    }
    return [name for name, value in required.items() if not value]


def main() -> None:
    settings = load_settings()
    r = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=3, socket_timeout=5)
    missing = _missing_config(settings)
    if missing:
        log.warning("callbacks paused; empty in .env: %s", ", ".join(missing))
        plivo_client = None
    else:
        import plivo

        plivo_client = plivo.RestClient(settings.plivo_auth_id, settings.plivo_auth_token)
        log.info("started; placing callbacks from the queue")

    last_heartbeat = 0.0
    while True:
        try:
            worked = plivo_client is not None and process_one(r, settings, plivo_client)
            if time.monotonic() - last_heartbeat > 60:
                log.info("heartbeat: %d callback(s) queued", r.zcard(callbacks.QUEUE))
                last_heartbeat = time.monotonic()
        except Exception:
            log.exception("callback processing error")
            worked = False
        if not worked:
            time.sleep(1)


if __name__ == "__main__":
    main()
