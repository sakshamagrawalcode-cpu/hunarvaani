"""Fill PHONE_HASH_SECRET and PHONE_ENC_KEY in .env if they are empty.

Run from the project root:  python scripts/gen_secrets.py
Values are written to .env only and never printed. Existing values are kept.
"""

import base64
import os
import secrets
from pathlib import Path

ENV = Path(__file__).resolve().parent.parent / ".env"

GENERATORS = {
    "PHONE_HASH_SECRET": lambda: secrets.token_hex(32),
    "PHONE_ENC_KEY": lambda: base64.urlsafe_b64encode(os.urandom(32)).decode(),
}


def main() -> None:
    if not ENV.exists():
        raise SystemExit(f"{ENV} not found. Copy .env.example to .env first.")
    lines = ENV.read_text(encoding="utf-8").splitlines()
    seen = set()
    for i, line in enumerate(lines):
        key, sep, value = line.partition("=")
        if sep and key in GENERATORS:
            seen.add(key)
            if value.strip():
                print(f"{key}: already set, kept")
            else:
                lines[i] = f"{key}={GENERATORS[key]()}"
                print(f"{key}: generated")
    for key, gen in GENERATORS.items():
        if key not in seen:
            lines.append(f"{key}={gen()}")
            print(f"{key}: added")
    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
