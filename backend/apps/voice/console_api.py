"""JSON for the team console (frontend/): calls, one call in detail, people, occupations.

Everything here is read-only and sits behind the same team password as /calls. Phone numbers
never leave the server whole: only the last four digits.
"""

from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from core import geo, store
from core.config import Settings
from core.phone import decrypt, last4
from core.timeutil import IST, utcnow

STEPS = ("q_age", "q_gender", "q_education", "q_travel", "q_physical", "q_district", "q_lean")
LIVE_FOR = timedelta(minutes=30)  # an "in call" row older than this is a crashed call, not live


def _live(c: dict) -> bool:
    started = c["answered_at"]
    return c["status"] == "in_call" and bool(started) and utcnow() - started < LIVE_FOR


def _when(c: dict) -> datetime | None:
    return c["answered_at"] or c["callback_at"] or c["missed_at"]


def _iso(ts: datetime | None) -> str | None:
    return ts.isoformat() if ts else None


def _number(settings: Settings, enc) -> str | None:
    if not enc or not settings.phone_enc_key:
        return None
    try:
        return last4(decrypt(enc, settings.phone_enc_key))
    except Exception:
        return None


class _Db:
    """One connection's worth of lookups shared by the endpoints."""

    def __init__(self, conn):
        self.conn = conn
        self._titles: dict[str, dict] | None = None

    def titles(self) -> dict[str, dict]:
        if self._titles is None:
            self._titles = {
                r["nco_code"]: {
                    "code": r["nco_code"],
                    "title_en": r["title_en"],
                    "title_hi": r["title_hi"],
                    "title_mr": r["title_mr"],
                }
                for r in self.conn.execute(
                    "SELECT nco_code, title_en, title_hi, title_mr FROM nco"
                ).fetchall()
            }
        return self._titles

    def occupation(self, code: str | None) -> dict | None:
        if not code or code in ("none", "skipped"):
            return None
        return self.titles().get(code) or {
            "code": code,
            "title_en": "",
            "title_hi": "",
            "title_mr": "",
        }

    def answers(self, call_ids: list) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {}
        if not call_ids:
            return out
        for a in self.conn.execute(
            "SELECT call_id, step, key_pressed, value, created_at FROM answer "
            "WHERE call_id = ANY(%s) ORDER BY created_at",
            (call_ids,),
        ):
            out.setdefault(str(a["call_id"]), []).append(a)
        return out

    def stories(self, call_ids: list) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {}
        if not call_ids:
            return out
        for s in self.conn.execute(
            "SELECT * FROM story WHERE call_id = ANY(%s) ORDER BY created_at", (call_ids,)
        ):
            out.setdefault(str(s["call_id"]), []).append(s)
        return out


def _district(values: dict) -> str | None:
    """ "Pune, Maharashtra" for the caller's PIN code (sample table); "Area not found"."""
    code = values.get("q_district")
    if not code:
        return None
    for row in geo.table().values():
        if row["district_code"] == code:
            return f"{row['district_en']}, {row['state']}"
    return "Area not found"


def _row(settings: Settings, db: _Db, c: dict, answers: list[dict], stories: list[dict]) -> dict:
    values = {a["step"]: a["value"] for a in answers}
    occupation, via = values.get("occupation"), "read-back"
    if not occupation:
        occupation, via = values.get("trades"), "keypad list"
    return {
        "id": str(c["id"]),
        "short": str(c["id"])[:8],
        "when": _iso(_when(c)),
        "number": _number(settings, c["phone_enc"]),
        "status": c["status"],
        "language": c["language"],
        "duration": c["duration_seconds"],
        "answers": {s: values.get(s) for s in STEPS} | {"q_district": _district(values)},
        "occupation": db.occupation(occupation),
        "occupation_via": via if db.occupation(occupation) else None,
        "transcripts": [s["transcript"] for s in stories if s["transcript"]],
        "human_flag": c["human_flag"],
        "keypad_only": c["keypad_only"],
        "live": _live(c),
    }


def _calls(conn, limit: int) -> list[dict]:
    return conn.execute(
        "SELECT * FROM call ORDER BY COALESCE(answered_at, callback_at, missed_at) DESC "
        "NULLS LAST LIMIT %s",
        (limit,),
    ).fetchall()


def build_router(get_settings: Callable[[], Settings]) -> APIRouter:
    router = APIRouter()

    def rows(conn, calls: list[dict]) -> list[dict]:
        db = _Db(conn)
        ids = [c["id"] for c in calls]
        answers, stories = db.answers(ids), db.stories(ids)
        s = get_settings()
        return [
            _row(s, db, c, answers.get(str(c["id"]), []), stories.get(str(c["id"]), []))
            for c in calls
        ]

    @router.get("/summary")
    def summary():
        with store.connect(get_settings().database_url) as conn:
            calls = _calls(conn, 1000)
            recent = rows(conn, calls)
        today = utcnow().astimezone(IST).date()
        occupations = Counter(r["occupation"]["code"] for r in recent if r["occupation"])
        by_code = {r["occupation"]["code"]: r["occupation"] for r in recent if r["occupation"]}
        durations = [r["duration"] for r in recent if r["duration"]]
        return {
            "calls": len(recent),
            "completed": sum(1 for r in recent if r["status"] == "completed"),
            "today": sum(1 for c in calls if _when(c) and _when(c).astimezone(IST).date() == today),
            "people": len({c["phone_hash"] for c in calls}),
            "avg_duration": round(sum(durations) / len(durations)) if durations else None,
            "human_flags": sum(1 for r in recent if r["human_flag"]),
            "keypad_only": sum(1 for r in recent if r["keypad_only"]),
            "with_occupation": sum(1 for r in recent if r["occupation"]),
            "languages": dict(Counter(r["language"] or "unknown" for r in recent)),
            "statuses": dict(Counter(r["status"] or "unknown" for r in recent)),
            "occupations": [
                {**by_code[code], "count": n} for code, n in occupations.most_common(8)
            ],
            "recent": recent[:6],
            "live_now": [r for r in recent if r["live"]],
        }

    @router.get("/calls")
    def calls(limit: int = 200):
        with store.connect(get_settings().database_url) as conn:
            return rows(conn, _calls(conn, max(1, min(limit, 1000))))

    @router.get("/calls/{call_id}")
    def call_detail(call_id: str):
        with store.connect(get_settings().database_url) as conn:
            c = _one_call(conn, call_id)
            db = _Db(conn)
            answers = db.answers([c["id"]]).get(str(c["id"]), [])
            stories = db.stories([c["id"]]).get(str(c["id"]), [])
            out = _row(get_settings(), db, c, answers, stories)
            out["answer_log"] = [
                {
                    "step": a["step"],
                    "key": a["key_pressed"],
                    "value": a["value"],
                    "at": _iso(a["created_at"]),
                }
                for a in answers
            ]
            out["consents"] = [
                {"kind": k["kind"], "granted": k["granted"], "at": _iso(k["created_at"])}
                for k in conn.execute(
                    "SELECT kind, granted, created_at FROM consent WHERE call_id = %s "
                    "ORDER BY created_at",
                    (c["id"],),
                )
            ]
            out["stories"] = [
                {
                    "n": n,
                    "transcript": s["transcript"],
                    "transcript_en": s["transcript_en"],
                    "top1": db.occupation(s["top1"]),
                    "top2": db.occupation(s["top2"]),
                    "confirmed": s["confirmed"],
                    "stt_ms": s["stt_ms"],
                    "search_ms": s["search_ms"],
                    "at": _iso(s["created_at"]),
                    "audio": bool(_audio_path(get_settings(), s["recording_url"])),
                }
                for n, s in enumerate(stories)
            ]
            events = conn.execute(
                "SELECT id, kind, payload, created_at FROM event WHERE call_id = %s ORDER BY id",
                (c["id"],),
            ).fetchall()
            out["events"] = [
                {
                    "id": e["id"],
                    "kind": e["kind"],
                    "payload": _public(e["payload"]),
                    "at": _iso(e["created_at"]),
                }
                for e in events
            ]
            out["summary_text"] = next(
                (
                    e["payload"].get("text")
                    for e in events
                    if e["kind"] == "summary" and e["payload"]
                ),
                None,
            )
            for key in ("missed_at", "callback_at", "answered_at", "ended_at"):
                out[key] = _iso(c[key])
            return out

    @router.get("/calls/{call_id}/audio/{n}")
    def story_audio(call_id: str, n: int):
        with store.connect(get_settings().database_url) as conn:
            c = _one_call(conn, call_id)
            stories = _Db(conn).stories([c["id"]]).get(str(c["id"]), [])
        if not 0 <= n < len(stories):
            raise HTTPException(404)
        path = _audio_path(get_settings(), stories[n]["recording_url"])
        if not path:
            raise HTTPException(404)
        return FileResponse(path, media_type="audio/wav", headers={"Cache-Control": "no-store"})

    @router.get("/people")
    def people(limit: int = 1000):
        with store.connect(get_settings().database_url) as conn:
            calls = list(reversed(_calls(conn, max(1, min(limit, 5000)))))
            db = _Db(conn)
            ids = [c["id"] for c in calls]
            answers, stories = db.answers(ids), db.stories(ids)
            s = get_settings()
            by_person: dict[str, dict] = {}
            for c in calls:  # oldest first, so later answers overwrite earlier ones
                cid = str(c["id"])
                row = _row(s, db, c, answers.get(cid, []), stories.get(cid, []))
                p = by_person.setdefault(
                    c["phone_hash"],
                    {"id": c["phone_hash"][:12], "calls": 0, "answers": {}, "occupation": None},
                )
                p["calls"] += 1
                p["last_call"], p["last_call_id"] = row["when"], row["id"]
                p["number"] = row["number"] or p.get("number")
                p["language"] = row["language"] or p.get("language")
                p["answers"].update({k: v for k, v in row["answers"].items() if v})
                p["occupation"] = row["occupation"] or p["occupation"]
                p["human_flag"] = p.get("human_flag") or row["human_flag"]
        return sorted(by_person.values(), key=lambda p: p["last_call"] or "", reverse=True)

    @router.get("/occupations")
    def occupations():
        with store.connect(get_settings().database_url) as conn:
            counts = Counter(
                a["value"]
                for a in conn.execute(
                    "SELECT value FROM answer WHERE step IN ('occupation', 'trades')"
                )
            )
            return [
                {
                    "code": r["nco_code"],
                    "title_en": r["title_en"],
                    "title_hi": r["title_hi"],
                    "title_mr": r["title_mr"],
                    "aliases": [a.strip() for a in r["aliases"].split("|") if a.strip()],
                    "callers": counts.get(r["nco_code"], 0),
                }
                for r in conn.execute(
                    "SELECT nco_code, title_en, title_hi, title_mr, aliases FROM nco "
                    "ORDER BY title_en"
                )
            ]

    return router


def _one_call(conn, call_id: str) -> dict:
    try:
        c = store.get_call(conn, call_id)
    except Exception:
        c = None
    if c is None:
        raise HTTPException(404)
    return c


def _audio_path(settings: Settings, recording_url: str | None) -> Path | None:
    """The story recording, only if it really is a file inside the recordings folder."""
    if not recording_url:
        return None
    folder = Path(settings.recordings_dir).resolve()
    path = Path(recording_url).resolve()
    if folder not in path.parents or not path.is_file():
        return None
    return path


def _public(payload: dict | None) -> dict | None:
    """Event payloads without server file paths."""
    if not payload:
        return payload
    return {k: v for k, v in payload.items() if k != "path"}
