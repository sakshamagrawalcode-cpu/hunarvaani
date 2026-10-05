"""Small audio helpers (16-bit mono PCM): read/write WAV, resample, loudness, beep, prompt bank."""

import io
import logging
import wave
from functools import lru_cache
from math import gcd
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly

log = logging.getLogger("hv.audio")
TARGET_RMS = 3000


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as w:
        rate, ch, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if width != 2:
        raise ValueError(f"{path}: only 16-bit WAV is supported")
    x = np.frombuffer(raw, dtype=np.int16)
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1).astype(np.int16)
    return x, rate


def write_wav(path: Path, x: np.ndarray, rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(np.asarray(x, dtype=np.int16).tobytes())


def wav_bytes(x: np.ndarray, rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(np.asarray(x, dtype=np.int16).tobytes())
    return buf.getvalue()


def to_int16(x: np.ndarray) -> np.ndarray:
    """Float audio in -1..1 (what the TTS model gives) to 16-bit."""
    return np.clip(np.asarray(x, dtype=np.float32) * 32767, -32768, 32767).astype(np.int16)


def resample(x: np.ndarray, src: int, dst: int) -> np.ndarray:
    if src == dst or len(x) == 0:
        return x
    g = gcd(src, dst)
    y = resample_poly(x.astype(np.float32), dst // g, src // g)
    return np.clip(y, -32768, 32767).astype(np.int16)


def level(x: np.ndarray) -> np.ndarray:
    """Even loudness across prompts, without clipping."""
    if len(x) == 0:
        return x
    rms = float(np.sqrt(np.mean(x.astype(np.float64) ** 2))) or 1.0
    gain = min(TARGET_RMS / rms, 26000 / max(1, int(np.abs(x).max())))
    return np.clip(x.astype(np.float32) * gain, -32768, 32767).astype(np.int16)


def rms(pcm: bytes) -> float:
    x = np.frombuffer(pcm[: len(pcm) // 2 * 2], dtype=np.int16)
    return float(np.sqrt(np.mean(x.astype(np.float64) ** 2))) if len(x) else 0.0


def beep(rate: int, ms: int = 220, freq: int = 880) -> np.ndarray:
    t = np.arange(int(rate * ms / 1000)) / rate
    env = np.minimum(1, np.minimum(t, t[::-1]) * 40)
    return (np.sin(2 * np.pi * freq * t) * env * 9000).astype(np.int16)


def silence(rate: int, ms: int) -> np.ndarray:
    return np.zeros(int(rate * ms / 1000), dtype=np.int16)


class PromptBank:
    """Pre-rendered pieces from audio/<lang>/<key>.wav, resampled to what the channel needs."""

    def __init__(self, folder: Path):
        self.folder = folder

    def path(self, lang: str, key: str) -> Path:
        return self.folder / lang / f"{key}.wav"

    def has(self, lang: str, key: str) -> bool:
        return self.path(lang, key).exists()

    @lru_cache(maxsize=4096)
    def get(self, lang: str, key: str, rate: int) -> np.ndarray | None:
        if key == "beep":
            return beep(rate)
        path = self.path(lang, key)
        if not path.exists():
            log.warning("missing audio %s (run scripts/render_audio.py)", path)
            return None
        x, src = read_wav(path)
        return level(resample(x, src, rate))

    def join(self, lang: str, keys: list[str], rate: int, gap_ms: int = 120) -> np.ndarray:
        pieces = []
        for k in keys:
            x = self.get(lang, k, rate)
            if x is not None:
                pieces += [x, silence(rate, gap_ms)]
        return np.concatenate(pieces) if pieces else np.zeros(0, dtype=np.int16)
