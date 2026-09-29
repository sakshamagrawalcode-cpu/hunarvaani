"""Sarvam Bulbul v3 text to speech, plus conversion to 8 kHz mono WAV for phone calls.

Standard library only, so scripts can run on the host without installing anything.
"""

import base64
import json
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

TTS_URL = "https://api.sarvam.ai/text-to-speech"
MAX_CHARS = 2500


class TtsError(RuntimeError):
    pass


def extract_audio(body: dict) -> bytes:
    audios = body.get("audios")
    if audios is None and "audio" in body:
        audios = [body["audio"]]
    if not audios:
        raise TtsError("response contained no audio")
    if len(audios) != 1:
        raise TtsError(f"expected one audio chunk, got {len(audios)}")
    return base64.b64decode(audios[0])


def synthesize(
    text: str, language_code: str, api_key: str, speaker: str = "", timeout: int = 60
) -> bytes:
    if not text.strip():
        raise TtsError("empty text")
    if len(text) > MAX_CHARS:
        raise TtsError(f"text is {len(text)} characters; the limit is {MAX_CHARS}")
    payload = {
        "text": text,
        "target_language_code": language_code,
        "model": "bulbul:v3",
        "speech_sample_rate": 8000,
    }
    if speaker:
        payload["speaker"] = speaker
    req = urllib.request.Request(
        TTS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"api-subscription-key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.load(resp)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise TtsError(f"Sarvam returned HTTP {exc.code}: {detail}") from None
    except urllib.error.URLError as exc:
        raise TtsError(f"could not reach Sarvam: {exc.reason}") from None
    return extract_audio(body)


def to_8k_mono(wav: bytes) -> bytes:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise TtsError("ffmpeg not found on PATH")
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = Path(tmp) / "in.wav", Path(tmp) / "out.wav"
        src.write_bytes(wav)
        proc = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(src),
                "-ar",
                "8000",
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                str(dst),
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise TtsError(f"ffmpeg failed: {proc.stderr.strip()[:300]}")
        return dst.read_bytes()
