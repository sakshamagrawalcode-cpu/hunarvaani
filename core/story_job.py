"""Work-story jobs: the api queues a recording, the worker transcribes, searches and renders
the read-back, and the api waits (briefly) for the answer on a per-call Redis list."""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor

import psycopg

from core import store
from core.config import Settings
from core.dialogue.prompts import fill, local_title

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
    """Wait up to `timeout` seconds for the worker's answer.

    Waits in slices of at most one second, so a Redis client with a short socket timeout
    (the api's is 3 s) never times out while the worker is still busy.
    """
    deadline = time.monotonic() + timeout
    while True:
        left = deadline - time.monotonic()
        item = r.blpop(result_key(call_id), timeout=min(max(left, 0.1), 1.0))
        if item:
            return json.loads(item[1])
        if left <= 1.0:
            return None


def story_fields(result: dict) -> dict:
    """The parts of a worker result that are kept in the story table."""
    scores = result.get("scores") or []
    return {
        "transcript": result.get("transcript"),
        "top1": scores[0]["code"] if scores else None,
        "top2": scores[1]["code"] if len(scores) > 1 else None,
        "stt_ms": result.get("stt_ms"),
        "search_ms": result.get("search_ms"),
    }


def save(conn, job: dict, result: dict) -> bool:
    """Keep the worker's transcript even if the call stopped waiting for it.

    Returns False when the call no longer exists (the caller pressed 9), so nothing is kept.
    """
    try:
        store.save_story(conn, job["call_id"], job["path"], **story_fields(result))
    except psycopg.errors.ForeignKeyViolation:
        return False
    return True


HEARD_MAX_WORDS = 20


def heard_text(transcript: str) -> str:
    """What we heard, trimmed for reading back: at most HEARD_MAX_WORDS words."""
    words = transcript.split()
    return " ".join(words[:HEARD_MAX_WORDS]).rstrip(" ।.!?,")


def process(job: dict, settings: Settings, index, encode, stt, render) -> dict:
    """Transcribe, search and render what we heard (P21) and the read-back (P13). Never raises.

    The two are rendered at the same time, since text-to-speech is the slowest step.
    """
    language = job.get("language") or "hi-IN"
    out: dict = {"candidates": [], "readback": [], "heard": []}
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
        confident = len(top) == 2 and top[0].score >= THRESHOLD

        texts = [fill(language, "P21", heard=heard_text(transcript))]
        if confident:
            names = [local_title(language, c.title_en, c.title_hi, c.title_mr) for c in top]
            texts.append(fill(language, "P13", occupation_1=names[0], occupation_2=names[1]))
        t2 = time.monotonic()
        with ThreadPoolExecutor(len(texts)) as pool:
            rendered = list(pool.map(lambda text: render(text, language), texts))
        out["tts_ms"] = int((time.monotonic() - t2) * 1000)
        out["heard"] = rendered[:1]
        if confident:
            out["readback"] = rendered[1:]
            out["candidates"] = [c.code for c in top]
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"[:300]
        out["candidates"], out["readback"], out["heard"] = [], [], []
    return out
