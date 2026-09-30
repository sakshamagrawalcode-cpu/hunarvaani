"""Prompts rendered during a call (P13 read-back, later P15), cached by a hash of their text."""

import hashlib
import os
from pathlib import Path

from core.tts import PACE, synthesize, to_8k_mono

PREFIX = "DYN:"


def prompt_id(text: str, language: str, speaker: str) -> str:
    digest = hashlib.sha256(f"{language}|{speaker}|{PACE}|{text}".encode()).hexdigest()[:24]
    return PREFIX + digest


def ensure(text: str, language: str, api_key: str, speaker: str, audio_dir: Path) -> str:
    """Render `text` once and return its prompt id ("DYN:<hash>")."""
    pid = prompt_id(text, language, speaker)
    path = Path(audio_dir) / "dyn" / f"{pid[len(PREFIX) :]}.wav"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        wav = to_8k_mono(synthesize(text, language, api_key, speaker))
        tmp = path.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_bytes(wav)
        tmp.replace(path)
    return pid
