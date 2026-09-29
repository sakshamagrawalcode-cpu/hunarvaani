"""One Sarvam chat call with sarvam-105b-conversations, to check that SARVAM_API_KEY works.

Run from the project root on your laptop (needs `pip install sarvamai` once):
  python scripts/sarvam_chat_check.py

The key is read from .env (SARVAM_API_KEY=...) and never printed.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and not line.lstrip().startswith("#"):
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    load_env()
    key = os.environ.get("SARVAM_API_KEY", "").strip()
    if not key:
        sys.exit("SARVAM_API_KEY is empty. Paste your key into .env first.")

    from sarvamai import SarvamAI

    client = SarvamAI(api_subscription_key=key)
    response = client.chat.completions(
        model="sarvam-105b-conversations",
        messages=[{"role": "user", "content": "नमस्ते! एक वाक्य में बताइए कि आप कौन हैं।"}],
    )
    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()
