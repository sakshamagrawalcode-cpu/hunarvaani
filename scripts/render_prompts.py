"""Render the voice prompts to audio/<hi|en|mr>/*.wav (8 kHz mono) with Sarvam Bulbul v3.

Run from the project root, on your laptop (needs ffmpeg on PATH and SARVAM_API_KEY in .env):
  python scripts/render_prompts.py --dry-run          # show the text, no API calls
  python scripts/render_prompts.py --only P01         # render one prompt in every language
  python scripts/render_prompts.py --lang mr-IN       # one language only
  python scripts/render_prompts.py                    # render missing or changed prompts
  python scripts/render_prompts.py --force            # re-render everything (uses Sarvam credits)

Each language folder keeps rendered.json (a fingerprint of each prompt's text and voice), so a
normal run re-renders only what changed. Files made before rendered.json existed are taken as up
to date. The run stops at the first "no credits" answer from Sarvam.

SARVAM_SPEAKER in .env picks the voice; leave it empty to use Sarvam's default voice.
"""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from core.dialogue.prompts import PROMPTS, audio_dir_name, prerendered_ids  # noqa: E402
from core.tts import TtsError, synthesize, to_8k_mono  # noqa: E402


def load_env() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition("=")
        if sep and not line.lstrip().startswith("#"):
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--lang", default="all", help="hi-IN, en-IN, mr-IN or all")
    ap.add_argument("--only", nargs="*", help="prompt ids, e.g. P01 P02")
    ap.add_argument("--force", action="store_true", help="re-render files that already exist")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    load_env()
    if args.lang != "all" and args.lang not in PROMPTS:
        sys.exit(f"unknown language {args.lang}; use one of {', '.join(PROMPTS)} or all")
    languages = list(PROMPTS) if args.lang == "all" else [args.lang]
    jobs = []
    for lang in languages:
        ids = args.only or prerendered_ids(lang)
        unknown = [i for i in ids if i not in PROMPTS[lang]]
        if unknown:
            sys.exit(f"unknown prompt id(s): {', '.join(unknown)}")
        out_dir = ROOT / "audio" / audio_dir_name(lang)
        out_dir.mkdir(parents=True, exist_ok=True)
        jobs += [(lang, pid, out_dir / f"{pid}.wav") for pid in ids]

    if args.dry_run:
        for lang, pid, dst in jobs:
            text = PROMPTS[lang][pid]
            state = "exists" if dst.exists() else "missing"
            print(f"{lang} {pid} [{state}] {len(text)} chars: {text}")
        return

    key = os.environ.get("SARVAM_API_KEY", "").strip()
    if not key:
        sys.exit("SARVAM_API_KEY is empty. Put your key in .env first.")
    speaker = os.environ.get("SARVAM_SPEAKER", "").strip()
    print(f"voice: {speaker or 'Sarvam default'}")

    failed = 0
    records: dict = {}
    for lang, pid, dst in jobs:
        record_file = dst.parent / "rendered.json"
        if record_file not in records:
            records[record_file] = _load(record_file)
        record = records[record_file]
        mark = fingerprint(PROMPTS[lang][pid], speaker)
        if dst.exists() and not args.force:
            if record.get(pid) in (mark, None):
                record[pid] = mark
                print(f"{lang} {pid}: up to date")
                continue
        try:
            wav = _synthesize(PROMPTS[lang][pid], lang, key, speaker)
        except TtsError as exc:
            failed += 1
            print(f"{lang} {pid}: FAILED - {exc}")
            if "HTTP 402" in str(exc):
                print(
                    "Sarvam says there are no credits left: stopping. Add credits, then run again;"
                )
                print("prompts already rendered are kept and will not be made again.")
                break
            continue
        dst.write_bytes(wav)
        record[pid] = mark
        _save(record_file, record)
        print(f"{lang} {pid}: rendered {len(wav) / 1024:.0f} KB, about {len(wav) / 16000:.1f} s")
    for record_file, record in records.items():
        _save(record_file, record)
    if failed:
        sys.exit(f"{failed} prompt(s) failed")


def fingerprint(text: str, speaker: str) -> str:
    return hashlib.sha256(f"{speaker}|{text}".encode()).hexdigest()[:16]


def _synthesize(text: str, lang: str, key: str, speaker: str) -> bytes:
    """One retry after a short wait when Sarvam says we are going too fast (HTTP 429)."""
    try:
        return to_8k_mono(synthesize(text, lang, key, speaker))
    except TtsError as exc:
        if "HTTP 429" not in str(exc):
            raise
        time.sleep(5)
        return to_8k_mono(synthesize(text, lang, key, speaker))


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(path: Path, record: dict) -> None:
    path.write_text(json.dumps(record, indent=1, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
