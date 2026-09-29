import json
import logging
import time
from pathlib import Path

import redis

from core import callbacks, dynprompt, store, story_job
from core.config import Settings, load_settings
from core.dialers import make_dialer, missing_config
from core.phone import decrypt, last4
from core.search.nco_search import NcoIndex, load_occupations
from core.stt import transcribe_file
from core.timeutil import in_quiet_hours, ist_day, next_allowed, utcnow
from core.translate import to_english

logging.basicConfig(level=logging.INFO, format="%(asctime)s worker %(message)s")
log = logging.getLogger("worker")
for _noisy in ("httpx", "huggingface_hub", "sentence_transformers"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

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


AUDIO_DIR = Path(__file__).resolve().parents[3] / "audio"
EMBED_MODEL = "intfloat/multilingual-e5-base"


def load_encoder():
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(EMBED_MODEL)
    except Exception as exc:
        log.warning("embedding model unavailable (%s); search uses keywords only", exc)
        return None
    log.info("embedding model loaded")
    return lambda text: model.encode("query: " + text, normalize_embeddings=True)


def handle_story(raw, r, settings: Settings, encode) -> None:
    job = json.loads(raw)
    with store.connect(settings.database_url) as conn:
        occupations = load_occupations(conn)
    index = NcoIndex(occupations) if occupations else None

    def render(text: str, language: str) -> str:
        return dynprompt.ensure(
            text, language, settings.sarvam_api_key, settings.sarvam_speaker, AUDIO_DIR
        )

    result = story_job.process(
        job,
        settings,
        index,
        encode,
        transcribe_file,
        render,
        # English copy of the caller's words costs Sarvam credits: off unless asked for
        translate=to_english if settings.translate_for_console else None,
    )
    try:
        with store.connect(settings.database_url) as conn:
            kept = story_job.save(conn, job, result)
    except Exception:
        log.exception("story %s: could not save the transcript", job["call_id"][:8])
        kept = True
    if not kept:
        log.info("story %s: the caller deleted their data; result dropped", job["call_id"][:8])
        return
    story_job.publish(r, job["call_id"], result)
    log.info(
        "story %s: stt %s ms, search %s ms, tts %s ms, top %s, read-back %s%s",
        job["call_id"][:8],
        result.get("stt_ms"),
        result.get("search_ms"),
        result.get("tts_ms"),
        result.get("scores"),
        "yes" if result.get("readback") else "no",
        f", error: {result['error']}" if result.get("error") else "",
    )


def main() -> None:
    settings = load_settings()
    r = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=3, socket_timeout=5)
    missing = missing_config(settings)
    if missing:
        log.warning("callbacks paused; empty in .env: %s", ", ".join(missing))
        dialer = None
    else:
        dialer = make_dialer(settings)
        log.info("placing callbacks via %s", settings.telephony_provider)
    if not settings.sarvam_api_key:
        log.warning("SARVAM_API_KEY is empty; work stories cannot be transcribed")
    encode = load_encoder()
    log.info("started; waiting for work stories and callbacks")

    last_heartbeat = 0.0
    while True:
        try:
            raw = r.lpop(story_job.QUEUE)
            if raw:
                handle_story(raw, r, settings, encode)
                continue
            worked = dialer is not None and process_one(r, settings, dialer)
            if time.monotonic() - last_heartbeat > 60:
                log.info("heartbeat: %d callback(s) queued", r.zcard(callbacks.QUEUE))
                last_heartbeat = time.monotonic()
            if not worked:
                item = r.blpop(story_job.QUEUE, timeout=1)
                if item:
                    handle_story(item[1], r, settings, encode)
        except Exception:
            log.exception("worker error")
            time.sleep(1)


if __name__ == "__main__":
    main()
