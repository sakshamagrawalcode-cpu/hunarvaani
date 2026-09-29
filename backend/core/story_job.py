"""Work-story jobs: the api queues a recording, the worker transcribes, translates, searches and
renders the read-back, and the api waits for the answer on a per-call Redis list (the caller
hears "please stay on the line" meanwhile)."""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor

import psycopg

from core import store
from core.config import Settings
from core.dialogue.prompts import fill, local_title, readback_text

log = logging.getLogger("story")

QUEUE = "hv:stories"
THRESHOLD = 0.35  # the best match must reach this for a read-back
TOP_K = 3  # occupations offered in the read-back
MIN_OPTION_SCORE = 0.2  # a 2nd or 3rd occupation below this is not offered


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
        "transcript_en": result.get("transcript_en"),
        "top1": scores[0]["code"] if scores else None,
        "top2": scores[1]["code"] if len(scores) > 1 else None,
        "top3": scores[2]["code"] if len(scores) > 2 else None,
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


def process(job: dict, settings: Settings, index, encode, stt, render, translate=None) -> dict:
    """Transcribe, translate, search and render what we heard (P21) and the read-back (P13).

    Never raises. The caller's words are put into English (`translate`, Sarvam) and the search
    runs on both the original words and the English, keeping each occupation's best score.
    When the best match is confident, the read-back offers up to TOP_K occupations (keys 1-3,
    the next key = none of these). Text-to-speech is the slowest step, so the two sentences
    are rendered at the same time. `texts` maps each rendered prompt id to its words and their
    English version.
    """
    language = job.get("language") or "hi-IN"
    out: dict = {"candidates": [], "readback": [], "heard": [], "texts": {}}
    try:
        t0 = time.monotonic()
        transcript = stt(job["path"], language, settings.sarvam_api_key)
        out["stt_ms"] = int((time.monotonic() - t0) * 1000)
        out["transcript"] = transcript
        if not transcript:
            return out

        transcript_en = _english(translate, transcript, language, settings, out)
        out["transcript_en"] = transcript_en

        t1 = time.monotonic()
        if index is None:
            out["error"] = "occupation index is empty; run scripts/seed_nco.py"
            return out
        queries = [transcript]
        if transcript_en and transcript_en != transcript:
            queries.append(transcript_en)
        top = best_matches(index, encode, queries)
        out["search_ms"] = int((time.monotonic() - t1) * 1000)
        out["scores"] = [
            {"code": c.code, "score": c.score, "title_en": c.title_en, "title_hi": c.title_hi}
            for c in top
        ]
        confident = bool(top) and top[0].score >= THRESHOLD
        shown = [c for c in top if c.score >= MIN_OPTION_SCORE] if confident else []

        texts = [fill(language, "P21", heard=heard_text(transcript))]
        english_texts = [
            fill("en-IN", "P21", heard=heard_text(transcript_en)) if transcript_en else None
        ]
        if shown:
            names = [local_title(language, c.title_en, c.title_hi, c.title_mr) for c in shown]
            texts.append(readback_text(language, names))
            english_texts.append(readback_text("en-IN", [c.title_en.lower() for c in shown]))
        t2 = time.monotonic()
        with ThreadPoolExecutor(len(texts)) as pool:
            rendered = list(pool.map(lambda text: render(text, language), texts))
        out["tts_ms"] = int((time.monotonic() - t2) * 1000)
        out["texts"] = {
            pid: {"text": text, "text_en": text_en}
            for pid, text, text_en in zip(rendered, texts, english_texts, strict=True)
        }
        out["heard"] = rendered[:1]
        if shown:
            out["readback"] = rendered[1:]
            out["candidates"] = [c.code for c in shown]
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"[:300]
        out["candidates"], out["readback"], out["heard"] = [], [], []
    return out


def best_matches(index, encode, queries: list[str], top_k: int = TOP_K) -> list:
    """Search each wording (original, English) and keep every occupation's best score."""
    best: dict = {}
    for text in queries:
        vec = encode(text) if encode else None
        for c in index.search(text, vec, top_k=top_k):
            if c.code not in best or c.score > best[c.code].score:
                best[c.code] = c
    return sorted(best.values(), key=lambda c: c.score, reverse=True)[:top_k]


def _english(translate, transcript: str, language: str, settings: Settings, out: dict):
    """The transcript in English; None if there is no translator or it fails."""
    if language == "en-IN":
        return transcript
    if translate is None:
        return None
    t = time.monotonic()
    try:
        return translate(transcript, language, settings.sarvam_api_key)
    except Exception as exc:
        out["translate_error"] = f"{type(exc).__name__}: {exc}"[:200]
        return None
    finally:
        out["translate_ms"] = int((time.monotonic() - t) * 1000)
