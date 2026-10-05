"""SQLite storage: people (by HunarVaani ID, district, name), sessions, every turn with its labels,
options offered and chosen, and an audit log of officer actions."""

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .identity import MAX_PIN_TRIES, check_pin, hash_pin, new_id

SCHEMA = """
CREATE TABLE IF NOT EXISTS persons (
  hv_id TEXT PRIMARY KEY, name TEXT, district TEXT, language TEXT, channel TEXT,
  pin_salt TEXT, pin_hash TEXT, pin_tries INTEGER DEFAULT 0,
  profile_json TEXT, consent_json TEXT, status TEXT DEFAULT 'new', created TEXT, updated TEXT);
CREATE INDEX IF NOT EXISTS persons_district ON persons(district);
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY, hv_id TEXT, channel TEXT, started TEXT, ended TEXT, end_reason TEXT);
CREATE TABLE IF NOT EXISTS turns (
  id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, ts TEXT, kind TEXT, question TEXT,
  answer TEXT, labels_json TEXT);
CREATE TABLE IF NOT EXISTS options (
  session_id TEXT, hv_id TEXT, rank INTEGER, course_id TEXT, centre_id TEXT, score REAL, raw REAL,
  detail_json TEXT, chosen INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS outcomes (
  id INTEGER PRIMARY KEY AUTOINCREMENT, hv_id TEXT, course_id TEXT, completed INTEGER, working_6m INTEGER,
  verified_by TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, actor TEXT, action TEXT, hv_id TEXT, note TEXT);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: Path | str):
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        with self.lock:
            self.db.executescript(SCHEMA)

    def _x(self, sql: str, args: tuple = ()) -> list[sqlite3.Row]:
        with self.lock:
            cur = self.db.execute(sql, args)
            rows = cur.fetchall()
            self.db.commit()
            return rows

    # sessions and turns ------------------------------------------------------------------------
    def start_session(self, channel: str) -> str:
        sid = uuid.uuid4().hex[:12]
        self._x("INSERT INTO sessions(id, channel, started) VALUES (?,?,?)", (sid, channel, now()))
        return sid

    def end_session(self, sid: str, reason: str, hv_id: str | None = None) -> None:
        self._x("UPDATE sessions SET ended=?, end_reason=?, hv_id=COALESCE(?, hv_id) WHERE id=?",
                (now(), reason, hv_id, sid))

    def turn(self, sid: str, kind: str, question: str, answer: str, labels: dict | None = None) -> None:
        self._x("INSERT INTO turns(session_id, ts, kind, question, answer, labels_json) VALUES (?,?,?,?,?,?)",
                (sid, now(), kind, question, answer, json.dumps(labels or {}, ensure_ascii=False)))

    # people --------------------------------------------------------------------------------------
    def create_person(self, name: str, district: str | None, language: str, channel: str,
                      profile: dict, consent: dict) -> str:
        for _ in range(20):
            hv_id = new_id()
            if not self._x("SELECT 1 FROM persons WHERE hv_id=?", (hv_id,)):
                break
        self._x("INSERT INTO persons(hv_id, name, district, language, channel, profile_json, consent_json, "
                "created, updated) VALUES (?,?,?,?,?,?,?,?,?)",
                (hv_id, name, district, language, channel, json.dumps(profile, ensure_ascii=False),
                 json.dumps(consent), now(), now()))
        return hv_id

    def update_profile(self, hv_id: str, profile: dict) -> None:
        self._x("UPDATE persons SET profile_json=?, updated=? WHERE hv_id=?",
                (json.dumps(profile, ensure_ascii=False), now(), hv_id))

    def set_pin(self, hv_id: str, pin: str) -> None:
        salt, digest = hash_pin(pin)
        self._x("UPDATE persons SET pin_salt=?, pin_hash=?, pin_tries=0 WHERE hv_id=?", (salt, digest, hv_id))

    def check_pin(self, hv_id: str, pin: str) -> str:
        """'ok', 'wrong', 'locked' or 'missing'."""
        rows = self._x("SELECT pin_salt, pin_hash, pin_tries FROM persons WHERE hv_id=?", (hv_id,))
        if not rows or not rows[0]["pin_hash"]:
            return "missing"
        r = rows[0]
        if r["pin_tries"] >= MAX_PIN_TRIES:
            return "locked"
        if check_pin(pin, r["pin_salt"], r["pin_hash"]):
            self._x("UPDATE persons SET pin_tries=0 WHERE hv_id=?", (hv_id,))
            return "ok"
        self._x("UPDATE persons SET pin_tries=pin_tries+1 WHERE hv_id=?", (hv_id,))
        return "locked" if r["pin_tries"] + 1 >= MAX_PIN_TRIES else "wrong"

    def person(self, hv_id: str) -> dict | None:
        rows = self._x("SELECT * FROM persons WHERE hv_id=?", (hv_id,))
        if not rows:
            return None
        p = dict(rows[0])
        p.pop("pin_salt", None)
        p.pop("pin_hash", None)
        p["profile"] = json.loads(p.pop("profile_json") or "{}")
        p["consent"] = json.loads(p.pop("consent_json") or "{}")
        return p

    def find(self, district: str = "", name: str = "", hv_id: str = "", limit: int = 200) -> list[dict]:
        sql = "SELECT hv_id, name, district, language, channel, status, created FROM persons WHERE 1=1"
        args: list = []
        if district:
            sql += " AND district=?"
            args.append(district)
        if name:
            sql += " AND name LIKE ?"
            args.append(f"%{name}%")
        if hv_id:
            sql += " AND hv_id LIKE ?"
            args.append(f"{hv_id.replace('-', '')}%")
        sql += " ORDER BY created DESC LIMIT ?"
        args.append(limit)
        return [dict(r) for r in self._x(sql, tuple(args))]

    def delete_person(self, hv_id: str, actor: str) -> None:
        """Right to erase: profile, turns and options go; one audit line stays (who, when)."""
        sids = [r["id"] for r in self._x("SELECT id FROM sessions WHERE hv_id=?", (hv_id,))]
        for sid in sids:
            self._x("DELETE FROM turns WHERE session_id=?", (sid,))
        self._x("DELETE FROM options WHERE hv_id=?", (hv_id,))
        self._x("DELETE FROM persons WHERE hv_id=?", (hv_id,))
        self.audit(actor, "erased", hv_id, "person asked to delete their data")

    # options ------------------------------------------------------------------------------------
    def save_options(self, sid: str, hv_id: str, options: list[dict]) -> None:
        self._x("DELETE FROM options WHERE hv_id=?", (hv_id,))
        for i, o in enumerate(options, 1):
            self._x("INSERT INTO options(session_id, hv_id, rank, course_id, centre_id, score, raw, detail_json) "
                    "VALUES (?,?,?,?,?,?,?,?)", (sid, hv_id, i, o["course_id"], o["centre_id"], o["score"],
                                                 o["raw"], json.dumps(o, ensure_ascii=False)))

    def choose(self, hv_id: str, rank: int) -> None:
        self._x("UPDATE options SET chosen=(rank=?) WHERE hv_id=?", (rank, hv_id))

    def options(self, hv_id: str) -> list[dict]:
        rows = self._x("SELECT rank, chosen, detail_json FROM options WHERE hv_id=? ORDER BY rank", (hv_id,))
        return [dict(json.loads(r["detail_json"]), rank=r["rank"], chosen=bool(r["chosen"])) for r in rows]

    def turns(self, hv_id: str) -> list[dict]:
        rows = self._x("SELECT t.ts, t.kind, t.question, t.answer, t.labels_json FROM turns t JOIN sessions s "
                       "ON s.id=t.session_id WHERE s.hv_id=? ORDER BY t.id", (hv_id,))
        return [dict(r) | {"labels": json.loads(r["labels_json"] or "{}")} for r in rows]

    # officers -------------------------------------------------------------------------------------
    def set_status(self, hv_id: str, status: str, actor: str, note: str = "") -> None:
        self._x("UPDATE persons SET status=?, updated=? WHERE hv_id=?", (status, now(), hv_id))
        self.audit(actor, f"status:{status}", hv_id, note)

    def audit(self, actor: str, action: str, hv_id: str, note: str = "") -> None:
        self._x("INSERT INTO audit(ts, actor, action, hv_id, note) VALUES (?,?,?,?,?)",
                (now(), actor, action, hv_id, note))

    def audit_log(self, hv_id: str) -> list[dict]:
        return [dict(r) for r in self._x("SELECT ts, actor, action, note FROM audit WHERE hv_id=? ORDER BY id",
                                         (hv_id,))]

    # learning data ------------------------------------------------------------------------------
    def add_outcome(self, hv_id: str, course_id: str, completed: bool, working_6m: bool | None, actor: str) -> None:
        self._x("INSERT INTO outcomes(hv_id, course_id, completed, working_6m, verified_by, ts) VALUES (?,?,?,?,?,?)",
                (hv_id, course_id, int(completed), None if working_6m is None else int(working_6m), actor, now()))
        self.audit(actor, "outcome", hv_id, f"{course_id}: completed={completed} working_6m={working_6m}")

    def choice_sets(self) -> list[dict]:
        """Every offered list where the person picked one: [{"options": [...], "chosen": index}]."""
        rows = self._x("SELECT hv_id, rank, chosen, detail_json FROM options ORDER BY hv_id, rank")
        sets: dict[str, list] = {}
        for r in rows:
            sets.setdefault(r["hv_id"], []).append((r["chosen"], json.loads(r["detail_json"])))
        out = []
        for items in sets.values():
            chosen = [i for i, (c, _) in enumerate(items) if c]
            if chosen and len(items) >= 2:
                out.append({"options": [d for _, d in items], "chosen": chosen[0]})
        return out

    def outcome_rows(self) -> list[dict]:
        """Chosen option + its verified outcome, with the gate inputs it had when offered."""
        rows = self._x("SELECT o.detail_json, x.completed, x.working_6m FROM outcomes x JOIN options o "
                       "ON o.hv_id = x.hv_id AND o.course_id = x.course_id")
        return [dict(json.loads(r["detail_json"]), completed=r["completed"], working_6m=r["working_6m"]) for r in rows]
