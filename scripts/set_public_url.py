"""Write the public HTTPS address into PUBLIC_BASE_URL in .env, and check that it answers.

  python scripts/set_public_url.py --from-tunnel        # read the tunnel address from Docker logs
  python scripts/set_public_url.py https://example.com  # or set one by hand

A quick tunnel gets a new address every time it starts, so run this again after a restart.
"""

import argparse
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV = ROOT / ".env"
COMPOSE = ["docker", "compose", "-f", str(ROOT / "infra" / "docker-compose.yml")]
TUNNEL_URL = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def find_tunnel_url(logs: str) -> str | None:
    found = TUNNEL_URL.findall(logs)
    return found[-1] if found else None


def set_env_value(text: str, key: str, value: str) -> str:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.partition("=")[0].strip() == key:
            lines[i] = f"{key}={value}"
            break
    else:
        lines.append(f"{key}={value}")
    return "\n".join(lines) + "\n"


def check(url: str) -> str:
    try:
        with urllib.request.urlopen(f"{url}/health", timeout=15) as resp:
            return f"GET /health -> {resp.status} {resp.read().decode()[:80]}"
    except urllib.error.URLError as exc:
        return f"not reachable yet ({exc.reason}); wait 10 seconds and run this again"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("url", nargs="?")
    ap.add_argument("--from-tunnel", action="store_true")
    args = ap.parse_args()

    if args.from_tunnel:
        proc = subprocess.run(
            [*COMPOSE, "logs", "tunnel", "--no-color"], capture_output=True, text=True
        )
        url = find_tunnel_url(proc.stdout + proc.stderr)
        if not url:
            sys.exit("no tunnel address in the logs yet. Start it first, wait 10 s, retry.")
    elif args.url:
        url = args.url.rstrip("/")
        if not url.startswith("https://"):
            sys.exit("the public address must start with https://")
    else:
        sys.exit("give a URL or use --from-tunnel")

    if not ENV.exists():
        sys.exit(f"{ENV} not found")
    ENV.write_text(set_env_value(ENV.read_text(encoding="utf-8"), "PUBLIC_BASE_URL", url))
    print(f"PUBLIC_BASE_URL={url}")
    print(check(url))
    print("Now run: docker compose -f infra/docker-compose.yml up -d api")


if __name__ == "__main__":
    main()
