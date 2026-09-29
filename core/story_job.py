"""Work-story jobs: the api queues a recording, the worker transcribes, searches and renders
the read-back, and the api waits (briefly) for the answer on a per-call Redis list."""

import json
import logging
import time

from core.config import Settings
from core.dialogue.prompts import fill

log = logging.getLogger("story")

QUEUE = "hv:stories"
THRESHOLD = 0.35


def result_key(call_id: str) -> str:
    return f"hv:story_result:{call_id}"


def submit(r, call_id: str, path: str, language: str) -> None:
    r.delete(result_key(call_id))
    r.rpush(QUEUE, json.dumps({"call_id": call_id, "path": path, "language": language}))


def publish(r, call_id: str, result: dict) -> None:
    key = result_key(call_id)
    r.rpush(key, json.dumps(result, ensure_ascii=False))
    r.expire(key, 120)


def wait_result(r, call_id: str, timeout: float) -> dict | None:
    item = r.blpop(result_key(call_id), timeout=max(timeout, 0.1))
    return json.loads(item[1]) if item else None


def process(job: dict, settings: Settings, index, encode, stt, render) -> dict:
    """Transcribe, search and render the P13 read-back. Never raises."""
    language = job.get("language") or "hi-IN"
    out: dict = {"candidates": [], "prompt": None}
    try:
        t0 = time.monotonic()
        transcript = stt(job["path"], language, settings.sarvam_api_key)
        out["stt_ms"] = int((time.monotonic() - t0) * 1000)
        out["transcript"] = transcript
        if not transcript:
            return out

        t1 = time.monotonic()
        if index is None:
            out["error"] = "occupation index is empty; run scripts/seed_nco.py"
            return out
        query_vec = encode(transcript) if encode else None
        top = index.search(transcript, query_vec, top_k=2)
        out["search_ms"] = int((time.monotonic() - t1) * 1000)
        out["scores"] = [{"code": c.code, "score": c.score} for c in top]
        if not top or top[0].score < THRESHOLD or len(top) < 2:
            return out

        text = fill(language, "P13", occupation_1=top[0].title_hi, occupation_2=top[1].title_hi)
        t2 = time.monotonic()
        out["prompt"] = render(text, language)
        out["tts_ms"] = int((time.monotonic() - t2) * 1000)
        out["candidates"] = [c.code for c in top]
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"[:300]
        out["candidates"], out["prompt"] = [], None
    return out
