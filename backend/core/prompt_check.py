"""Checks every rendered prompt file, for the console's "Voice prompts" page.

For each prompt and language: the words, whether the file exists, its length, how loud it is,
silence at the start and end, clipping, and whether the text changed after it was rendered
(then `python scripts/render_prompts.py` makes it again).
"""

import hashlib
import json
import math
import warnings
import wave
from pathlib import Path

from core.dialogue.prompts import DYNAMIC, FRAGMENTS, PROMPTS, audio_dir_name
from core.tts import PACE

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    import audioop

# the order a caller meets them, then the ones that play only sometimes
CALL_ORDER = (
    "P05 P01 P02 P03 P06 P07 P08 P28 P25 P26 P09 P10 P27 P31 P32 P11 P12 P17 P30 P21 P13 P24 "
    "P35 P36 P37 P22 P23 P14 P34 P41 P33 P15 P38 P40 P39 P16 P29 P19 P18 P04 P20"
).split()

USED_FOR = {
    "P01": "greeting",
    "P02": "no key at the greeting: can you hear us?",
    "P03": "is this a good time?",
    "P04": "call back tomorrow",
    "P05": "language menu",
    "P06": "consent: recording",
    "P07": "consent: sharing",
    "P08": "consent: training our AI",
    "P09": "education",
    "P10": "travel",
    "P11": "job or own work",
    "P12": "tell us about your work (beep)",
    "P13": "the 3 closest occupations: press 1-3 (made during the call)",
    "P14": "trade list",
    "P15": "closing summary (made during the call)",
    "P16": "no answer: please listen again",
    "P17": "please wait a moment",
    "P18": "data deleted (key 9)",
    "P19": "an officer will call (key 0)",
    "P20": "fixed goodbye",
    "P21": "you said... (made during the call)",
    "P22": "could not hear you",
    "P23": "tell it again in more detail (beep)",
    "P24": "could not understand your work",
    "P25": "age",
    "P26": "gender",
    "P27": "physical difficulty",
    "P28": "why we ask",
    "P29": "wrong key: please listen again",
    "P30": "still working, please stay on the line",
    "P31": "PIN code: 6 digits, # to end, * to skip",
    "P32": "PIN code not right: press the six digits again",
    "P33": "goodbye after the caller picks an option",
    "P34": "the training options: press 1-3 (made during the call)",
    "P35": "answer review: you told us ...",
    "P36": "answer review: all correct 1, change 2",
    "P37": "which answer to change: 1-7",
    "P38": "your reference number is",
    "P39": "write it down, where to go, documents to take, never pay; goodbye",
    "P40": "once more (the number again)",
    "P41": "after an option's details: choose it 1, hear the options again 2",
}

FRAME_MS = 20
SILENT_RMS = 300  # below this a 20 ms frame counts as silence


def fingerprint(text: str, speaker: str) -> str:
    """Same as scripts/render_prompts.py, to spot text changed after rendering."""
    return hashlib.sha256(f"{speaker}|{PACE}|{text}".encode()).hexdigest()[:16]


def _db(value: float) -> float | None:
    return round(20 * math.log10(value / 32768), 1) if value > 0 else None


def measure(path: Path) -> dict:
    with wave.open(str(path)) as w:
        rate, width, channels = w.getframerate(), w.getsampwidth(), w.getnchannels()
        pcm = w.readframes(w.getnframes())
    out = {"seconds": round(len(pcm) / (rate * width * channels), 2), "rate": rate}
    if width != 2 or channels != 1:
        return {**out, "issues": ["not 16-bit mono: render it again"]}
    frame = rate * 2 * FRAME_MS // 1000
    loud = [
        audioop.rms(pcm[i : i + frame], 2) >= SILENT_RMS for i in range(0, len(pcm), frame)
    ] or [False]
    first = loud.index(True) if True in loud else len(loud)
    last = loud[::-1].index(True) if True in loud else len(loud)
    rms, peak = (audioop.rms(pcm, 2), audioop.max(pcm, 2)) if pcm else (0, 0)
    out.update(
        level_db=_db(rms),
        peak_db=_db(peak),
        silence_start=round(first * FRAME_MS / 1000, 2),
        silence_end=round(last * FRAME_MS / 1000, 2),
    )
    issues = []
    if not any(loud):
        issues.append("silent")
    if out["seconds"] < 0.5:
        issues.append("very short")
    if out["level_db"] is not None and out["level_db"] < -32:
        issues.append("quiet")
    if peak >= 32000:
        issues.append("clipping")
    if out["silence_start"] > 0.8:
        issues.append(f"{out['silence_start']} s silence at the start")
    if out["silence_end"] > 1.2:
        issues.append(f"{out['silence_end']} s silence at the end")
    out["issues"] = issues
    return out


def check_all(audio_dir: Path, languages: tuple[str, ...], speaker: str = "") -> dict:
    ids = [p for p in CALL_ORDER if p in PROMPTS["hi-IN"]]
    ids += [p for p in PROMPTS["hi-IN"] if p not in ids]
    ids += list(FRAGMENTS["hi-IN"])
    records = {}
    for lang in languages:
        try:
            path = audio_dir / audio_dir_name(lang) / "rendered.json"
            records[lang] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            records[lang] = {}
    prompts = []
    for pid in ids:
        per_lang = {}
        for lang in languages:
            text = PROMPTS.get(lang, {}).get(pid) or FRAGMENTS.get(lang, {}).get(pid)
            item: dict = {"text": text}
            if pid in DYNAMIC or text is None:
                per_lang[lang] = item
                continue
            folder = audio_dir_name(lang)
            path = audio_dir / folder / f"{pid}.wav"
            if not path.is_file():
                per_lang[lang] = {**item, "missing": True, "issues": ["not rendered"]}
                continue
            try:
                item.update(measure(path))
            except (wave.Error, EOFError, OSError) as exc:
                item["issues"] = [f"unreadable file ({type(exc).__name__})"]
            item["audio"] = f"/audio/{folder}/{pid}.wav"
            mark = records[lang].get(pid)
            if mark is not None and mark != fingerprint(text, speaker):
                item.setdefault("issues", []).append("text changed since it was rendered")
            per_lang[lang] = item
        prompts.append(
            {
                "id": pid,
                "used_for": USED_FOR.get(pid, "piece of the answer review or of a number"),
                "dynamic": pid in DYNAMIC,
                "languages": per_lang,
            }
        )
    return {"languages": list(languages), "prompts": prompts}
