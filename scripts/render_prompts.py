"""Render the Hindi voice prompts to audio/hi/*.wav (8 kHz mono) with Sarvam Bulbul v3.

Run from the project root, on your laptop (needs ffmpeg on PATH and SARVAM_API_KEY in .env):
  python scripts/render_prompts.py --dry-run     # show the text, no API calls
  python scripts/render_prompts.py --only P01    # render one prompt
  python scripts/render_prompts.py               # render every missing prompt
  python scripts/render_prompts.py --force       # re-render everything

SARVAM_SPEAKER in .env picks the voice; leave it empty to use Sarvam's default voice.
"""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

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
    ap.add_argument("--lang", default="hi-IN")
    ap.add_argument("--only", nargs="*", help="prompt ids, e.g. P01 P02")
    ap.add_argument("--force", action="store_true", help="re-render files that already exist")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    load_env()
    ids = args.only or prerendered_ids(args.lang)
    unknown = [i for i in ids if i not in PROMPTS[args.lang]]
    if unknown:
        sys.exit(f"unknown prompt id(s): {', '.join(unknown)}")
    out_dir = ROOT / "audio" / audio_dir_name(args.lang)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        for pid in ids:
            text = PROMPTS[args.lang][pid]
            state = "exists" if (out_dir / f"{pid}.wav").exists() else "missing"
            print(f"{pid} [{state}] {len(text)} chars: {text}")
        return

    key = os.environ.get("SARVAM_API_KEY", "").strip()
    if not key:
        sys.exit("SARVAM_API_KEY is empty. Put your key in .env first.")
    speaker = os.environ.get("SARVAM_SPEAKER", "").strip()
    print(f"voice: {speaker or 'Sarvam default'}")

    failed = 0
    for pid in ids:
        dst = out_dir / f"{pid}.wav"
        if dst.exists() and not args.force:
            print(f"{pid}: skipped, already exists")
            continue
        try:
            wav = to_8k_mono(synthesize(PROMPTS[args.lang][pid], args.lang, key, speaker))
        except TtsError as exc:
            failed += 1
            print(f"{pid}: FAILED - {exc}")
            continue
        dst.write_bytes(wav)
        print(f"{pid}: rendered {len(wav) / 1024:.0f} KB, about {len(wav) / 16000:.1f} s")
    if failed:
        sys.exit(f"{failed} prompt(s) failed")


if __name__ == "__main__":
    main()
