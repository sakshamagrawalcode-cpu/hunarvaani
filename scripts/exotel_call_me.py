"""Ask Exotel to call one phone and connect it to your flow: checks outbound callbacks.

Run on your laptop from the project root (standard library only):
  python scripts/exotel_call_me.py 9876543210

On a trial account the phone usually has to be verified in the Exotel dashboard first.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.config import load_settings  # noqa: E402
from core.dialers import REQUIRED, DialError, ExotelDialer  # noqa: E402


def load_env() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and not line.lstrip().startswith("#"):
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    digits = "".join(c for c in sys.argv[1] if c.isdigit())[-10:]
    if len(digits) != 10 or digits[0] not in "6789":
        sys.exit("give a 10-digit Indian mobile number")
    load_env()
    s = load_settings()
    missing = [env for env, attr in REQUIRED["exotel"].items() if not getattr(s, attr)]
    if not s.public_base_url:
        missing.append("PUBLIC_BASE_URL")
    if missing:
        sys.exit("empty in .env: " + ", ".join(missing))
    dialer = ExotelDialer(s)
    print(f"asking Exotel to call xxxxxx{digits[-4:]} and connect it to {dialer.flow_url()}")
    try:
        sid = dialer.dial("+91" + digits, "manual-test")
    except DialError as exc:
        sys.exit(f"FAILED: {exc}")
    print(f"OK, Exotel accepted the call (Sid {sid}). Your phone should ring now.")


if __name__ == "__main__":
    main()
