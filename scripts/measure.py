"""Slide numbers from the calls already in the database (step A14): how far calls got, how long
the caller waited, how often the read-back was right, what options were offered and chosen.
Only real saved data is counted; each line says how many calls it is based on.

docker compose -f infra/docker-compose.yml exec api python scripts/measure.py
docker compose -f infra/docker-compose.yml exec api python scripts/measure.py --since 2026-09-30
docker compose -f infra/docker-compose.yml logs api > api.log     # adds prompt delays:
docker compose -f infra/docker-compose.yml exec -T api python scripts/measure.py --log - < api.log
"""

import argparse
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from core import measure, store  # noqa: E402
from core.timeutil import IST  # noqa: E402


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--since", help="only calls on or after this date (YYYY-MM-DD, IST)")
    ap.add_argument(
        "--min-seconds", type=int, default=0, help="leave out calls shorter than this (tests)"
    )
    ap.add_argument("--log", help="api log file for prompt delays ('-' reads standard input)")
    args = ap.parse_args()
    since = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=IST) if args.since else None
    lags = None
    if args.log:
        if args.log == "-":
            lags = measure.played_lags(sys.stdin)
        else:
            with open(args.log, encoding="utf-8", errors="replace") as f:
                lags = measure.played_lags(f)
    url = os.environ.get("DATABASE_URL") or "postgresql://hv:hv@db:5432/hv"
    with store.connect(url) as conn:
        calls = measure.load(conn, since, args.min_seconds)
    print(measure.report(measure.summarize(calls, lags)))


if __name__ == "__main__":
    main()
