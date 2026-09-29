import logging
import time

import redis

from core import callbacks, store
from core.config import Settings, load_settings
from core.dialers import make_dialer, missing_config
from core.phone import decrypt, last4
from core.timeutil import in_quiet_hours, ist_day, next_allowed, utcnow

logging.basicConfig(level=logging.INFO, format="%(asctime)s worker %(message)s")
log = logging.getLogger("worker")

DIALABLE = {"queued", "queued_quiet_hours"}


def process_one(r, settings: Settings, dialer, now=None) -> bool:
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
            callbacks.schedule(r, call_id, next_allowed(now, settings.quiet_hours))
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
        try:
            provider_call_id = dialer.dial(number, call_id)
        except Exception as exc:
            store.update_call(conn, call_id, status="dial_failed")
            store.add_event(
                conn, call_id, "dial_failed", {"error": f"{type(exc).__name__}: {exc}"[:300]}
            )
            log.warning("callback to %s failed: %s", last4(number), exc)
            return True

        store.update_call(
            conn, call_id, callback_at=now, status="dialing", provider_call_id=provider_call_id
        )
        store.add_event(conn, call_id, "callback_placed", {"provider": settings.telephony_provider})
        log.info("callback placed to %s via %s", last4(number), settings.telephony_provider)
    return True


def main() -> None:
    settings = load_settings()
    r = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=3, socket_timeout=5)
    missing = missing_config(settings)
    if missing:
        log.warning("callbacks paused; empty in .env: %s", ", ".join(missing))
        dialer = None
    else:
        dialer = make_dialer(settings)
        log.info("started; placing callbacks via %s", settings.telephony_provider)

    last_heartbeat = 0.0
    while True:
        try:
            worked = dialer is not None and process_one(r, settings, dialer)
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
