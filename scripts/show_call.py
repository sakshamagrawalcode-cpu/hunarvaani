"""Print what happened in recent calls: steps, keys, timeouts, story and answers.

docker compose -f infra/docker-compose.yml exec api python scripts/show_call.py       # latest
docker compose -f infra/docker-compose.yml exec api python scripts/show_call.py -n 3  # last 3
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core import store  # noqa: E402
from core.timeutil import IST  # noqa: E402


def fmt(ts) -> str:
    return ts.astimezone(IST).strftime("%H:%M:%S") if ts else "--:--:--"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("-n", type=int, default=1, help="how many recent calls")
    args = ap.parse_args()
    url = os.environ.get("DATABASE_URL") or "postgresql://hv:hv@db:5432/hv"
    with store.connect(url) as conn:
        calls = conn.execute(
            "SELECT * FROM call ORDER BY COALESCE(answered_at, missed_at, callback_at) DESC "
            "NULLS LAST LIMIT %s",
            (args.n,),
        ).fetchall()
        if not calls:
            print("no calls yet")
            return
        for c in reversed(calls):
            cid = str(c["id"])
            print("=" * 70)
            print(
                f"call {cid[:8]}  status={c['status']}  duration={c['duration_seconds']}s  "
                f"keypad_only={c['keypad_only']}  human_flag={c['human_flag']}"
            )
            print(f"answered {fmt(c['answered_at'])}  ended {fmt(c['ended_at'])} (IST)")
            print("-- timeline")
            for e in conn.execute(
                "SELECT kind, payload, created_at FROM event WHERE call_id = %s ORDER BY id",
                (cid,),
            ):
                p = e["payload"] or {}
                detail = " ".join(f"{k}={v}" for k, v in p.items())
                print(f"  {fmt(e['created_at'])}  {e['kind']:<16} {detail}")
            print("-- answers")
            for a in conn.execute(
                "SELECT step, key_pressed, value FROM answer WHERE call_id = %s "
                "ORDER BY created_at",
                (cid,),
            ):
                print(f"  {a['step']:<12} key={a['key_pressed'] or '-'}  {a['value']}")
            print("-- consents")
            for k in conn.execute(
                "SELECT kind, granted FROM consent WHERE call_id = %s ORDER BY created_at", (cid,)
            ):
                print(f"  {k['kind']:<10} {'yes' if k['granted'] else 'no'}")
            for st in conn.execute(
                "SELECT recording_url, transcript, top1, top2, confirmed FROM story "
                "WHERE call_id = %s ORDER BY created_at",
                (cid,),
            ):
                print(f"-- story file: {st['recording_url']}")
                if st["transcript"]:
                    print(f"   transcript: {st['transcript']}")
                if st["top1"]:
                    print(
                        f"   understood: {st['top1']} / {st['top2']}, confirmed: {st['confirmed']}"
                    )


if __name__ == "__main__":
    main()
