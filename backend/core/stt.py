"""Sarvam Saaras speech-to-text for recorded work stories.

The REST endpoint takes at most 30 s of audio per request, so recordings are cut into
pieces of at most 28 s, sent in parallel, and the transcripts joined in order.
"""

import io
import wave
from concurrent.futures import ThreadPoolExecutor

import requests

STT_URL = "https://api.sarvam.ai/speech-to-text"
PIECE_SECONDS = 28


class SttError(RuntimeError):
    pass


def split_wav(path: str, piece_seconds: int = PIECE_SECONDS) -> list[bytes]:
    with wave.open(path) as w:
        rate, width, channels = w.getframerate(), w.getsampwidth(), w.getnchannels()
        frames = w.readframes(w.getnframes())
    step = rate * width * channels * piece_seconds
    pieces = []
    for start in range(0, len(frames), step):
        buf = io.BytesIO()
        with wave.open(buf, "wb") as out:
            out.setnchannels(channels)
            out.setsampwidth(width)
            out.setframerate(rate)
            out.writeframes(frames[start : start + step])
        pieces.append(buf.getvalue())
    return pieces


def transcribe_piece(wav: bytes, language: str, api_key: str, timeout: int = 30) -> str:
    try:
        resp = requests.post(
            STT_URL,
            headers={"api-subscription-key": api_key},
            files={"file": ("story.wav", wav, "audio/wav")},
            data={"model": "saaras:v3", "mode": "transcribe", "language_code": language},
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise SttError(f"could not reach Sarvam: {type(exc).__name__}") from None
    if resp.status_code != 200:
        raise SttError(f"Sarvam STT HTTP {resp.status_code}: {resp.text[:200]}")
    return (resp.json().get("transcript") or "").strip()


def transcribe_file(path: str, language: str, api_key: str) -> str:
    if not api_key:
        raise SttError("SARVAM_API_KEY is empty")
    pieces = split_wav(path)
    if not pieces:
        return ""
    with ThreadPoolExecutor(max_workers=min(4, len(pieces))) as pool:
        texts = list(pool.map(lambda p: transcribe_piece(p, language, api_key), pieces))
    return " ".join(t for t in texts if t)
