"""Numbers for the slides, measured from the calls already in the database (step A14).

Everything here is counted from what real calls saved: the call row, its events, the story and
the options. Nothing is estimated or filled in; a number that no call has data for is shown as
"no data". The optional api log adds how late Exotel played each prompt ("exotel played X
(+N s)" lines), which the database does not keep.
"""

import re
import statistics
from dataclasses import dataclass, field
from datetime import datetime

from core.timeutil import IST

PLAYED = re.compile(r"exotel played (\S+) (?:\(\+(\d+(?:\.\d+)?) s\)|(\d+(?:\.\d+)?) s after)")
EARLY = "Call ended early"
# The steps of a call in order, and the event that shows a call got that far.
FUNNEL = (
    ("answered", "call answered"),
    ("language", "language chosen"),
    ("consents", "consents done"),
    ("profile", "keypad questions done"),
    ("story", "work story recorded"),
    ("readback", "occupation confirmed or retold"),
    ("options", "options offered"),
    ("chosen", "an option chosen"),
    ("goodbye", "reached the goodbye"),
)


@dataclass
class CallData:
    id: str
    language: str | None
    status: str | None
    duration: int | None
    answered_at: datetime | None
    events: list[tuple[str, dict, datetime]] = field(default_factory=list)
    stories: list[dict] = field(default_factory=list)
    recommendations: list[dict] = field(default_factory=list)
    answers: list[tuple[str, str | None]] = field(default_factory=list)

    def kinds(self) -> set[str]:
        return {k for k, _, _ in self.events}

    def steps(self) -> set[str]:
        out = {"answered"} if self.answered_at else set()
        kinds = self.kinds()
        said = {p.get("step") for k, p, _ in self.events if k == "say"}
        if "language" in kinds:
            out.add("language")
        if any(str(step or "").startswith("q_") for step in said):  # past the consents
            out.add("consents")
        if any(step == "q_lean" for step, _ in self.answers):
            out.add("profile")
        if "story_recorded" in kinds:
            out.add("story")
        if "readback" in kinds:
            out.add("readback")
        if any(p.get("spoken") for k, p, _ in self.events if k == "recommendations"):
            out.add("options")
        if any(p.get("rank") for k, p, _ in self.events if k == "interest"):
            out.add("chosen")
        if "goodbye" in said:
            out.add("goodbye")
        return out

    def ended_early(self) -> str | None:
        for k, p, _ in self.events:
            if k == "problem" and str(p.get("what", "")).startswith(EARLY):
                return str(p["what"]).split(":", 1)[-1].strip()
        return None

    def story_waits(self) -> list[float]:
        """Seconds the caller waited between the end of the story and what came next (the
        read-back, a retell request, or the trade list)."""
        waits, ended = [], None
        for k, p, at in self.events:
            if k == "recording":
                ended = at
            elif k == "say" and ended is not None and p.get("step") != "story":
                waits.append((at - ended).total_seconds())
                ended = None
        return waits


def load(conn, since: datetime | None = None, min_seconds: int = 0) -> list[CallData]:
    rows = conn.execute(
        "SELECT id, language, status, duration_seconds, answered_at FROM call "
        "WHERE answered_at IS NOT NULL AND (%(since)s::timestamptz IS NULL "
        "OR answered_at >= %(since)s) AND COALESCE(duration_seconds, 0) >= %(min)s "
        "ORDER BY answered_at",
        {"since": since, "min": min_seconds},
    ).fetchall()
    calls = []
    for r in rows:
        cid = str(r["id"])
        c = CallData(cid, r["language"], r["status"], r["duration_seconds"], r["answered_at"])
        c.events = [
            (e["kind"], e["payload"] or {}, e["created_at"])
            for e in conn.execute(
                "SELECT kind, payload, created_at FROM event WHERE call_id = %s ORDER BY id",
                (cid,),
            )
        ]
        c.stories = list(conn.execute("SELECT * FROM story WHERE call_id = %s", (cid,)))
        c.recommendations = list(
            conn.execute(
                "SELECT rank, course_id, details, spoken, chosen FROM recommendation "
                "WHERE call_id = %s ORDER BY rank",
                (cid,),
            )
        )
        c.answers = [
            (a["step"], a["value"])
            for a in conn.execute(
                "SELECT step, value FROM answer WHERE call_id = %s ORDER BY created_at", (cid,)
            )
        ]
        calls.append(c)
    return calls


def played_lags(lines) -> list[float]:
    """How late (seconds) Exotel played each prompt, from api log lines."""
    out = []
    for line in lines:
        m = PLAYED.search(line)
        if m:
            out.append(float(m.group(2) or m.group(3)))
    return out


def _stats(values: list[float]) -> dict | None:
    if not values:
        return None
    ordered = sorted(values)
    p90 = ordered[min(len(ordered) - 1, round(0.9 * (len(ordered) - 1)))]
    return {
        "n": len(values),
        "median": statistics.median(ordered),
        "p90": p90,
        "max": ordered[-1],
    }


def _pct(part: int, whole: int) -> float | None:
    return round(100 * part / whole) if whole else None


def summarize(calls: list[CallData], lags: list[float] | None = None) -> dict:
    n = len(calls)
    steps = [c.steps() for c in calls]
    funnel = [(label, sum(key in s for s in steps)) for key, label in FUNNEL]
    stories = [s for c in calls for s in c.stories]
    readbacks = [p for c in calls for k, p, _ in c.events if k == "readback"]
    confirmed = [p for p in readbacks if p.get("confirmed")]
    first = [p for p in confirmed if (p.get("candidates") or [None])[0] == p["confirmed"]]
    offered = [c for c in calls if "options" in c.steps()]
    chosen = [c for c in calls if "chosen" in c.steps()]
    heard = [c for c in offered if "option_heard" in c.kinds()]
    kinds: dict[str, int] = {}
    for c in offered:
        for rec in c.recommendations:
            kind = (rec["details"] or {}).get("kind") or "other"
            kinds[kind] = kinds.get(kind, 0) + 1
    languages: dict[str, int] = {}
    for c in calls:
        languages[c.language or "unknown"] = languages.get(c.language or "unknown", 0) + 1
    early = [c.ended_early() for c in calls if c.ended_early()]
    return {
        "calls": n,
        "first": calls[0].answered_at if calls else None,
        "last": calls[-1].answered_at if calls else None,
        "languages": languages,
        "duration": _stats([c.duration for c in calls if c.duration]),
        "funnel": funnel,
        "ended_early": early,
        "stories": len(stories),
        "story_seconds": _stats(
            [p.get("seconds") for c in calls for k, p, _ in c.events if k == "recording"]
        ),
        "stt_ms": _stats([s["stt_ms"] for s in stories if s.get("stt_ms") is not None]),
        "search_ms": _stats([s["search_ms"] for s in stories if s.get("search_ms") is not None]),
        "story_wait": _stats([w for c in calls for w in c.story_waits()]),
        "llm_used": sum(1 for s in stories if s.get("llm")),
        "readbacks": len(readbacks),
        "confirmed": len(confirmed),
        "confirmed_first": len(first),
        "offered": len(offered),
        "chosen": len(chosen),
        "heard_detail": len(heard),
        "option_kinds": kinds,
        "timeouts": sum(1 for c in calls for k, _, _ in c.events if k == "timeout"),
        "problems": sum(1 for c in calls for k, _, _ in c.events if k == "problem"),
        "lags": _stats(lags or []),
    }


def _fmt_stats(s: dict | None, unit: str, scale: float = 1) -> str:
    if not s:
        return "no data"
    return (
        f"median {s['median'] * scale:.1f} {unit}, 90% under {s['p90'] * scale:.1f} {unit}, "
        f"max {s['max'] * scale:.1f} {unit} ({s['n']})"
    )


def _fmt_pct(part: int, whole: int) -> str:
    pct = _pct(part, whole)
    return f"{part} of {whole}" + (f" ({pct}%)" if pct is not None else "")


def report(m: dict) -> str:
    """Plain-text report; every line says how many calls it is based on."""
    if not m["calls"]:
        return "No answered calls in the database for this period."
    day = "%d %b %Y"
    first, last = m["first"].astimezone(IST), m["last"].astimezone(IST)
    lines = [
        f"Measured on {m['calls']} real calls, {first:{day}} to {last:{day}}.",
        "Languages: " + ", ".join(f"{k} {v}" for k, v in sorted(m["languages"].items())),
        f"Call length: {_fmt_stats(m['duration'], 's')}",
        "",
        "How far calls got:",
    ]
    lines += [f"  {label:<32} {_fmt_pct(count, m['calls'])}" for label, count in m["funnel"]]
    lines += [
        f"Ended early (not by the caller hanging up at the end): {len(m['ended_early'])}",
        *[f"  - {why}" for why in m["ended_early"]],
        "",
        f"Work stories: {m['stories']}",
        f"  story length:             {_fmt_stats(m['story_seconds'], 's')}",
        f"  speech-to-text (Sarvam):  {_fmt_stats(m['stt_ms'], 's', 0.001)}",
        f"  occupation search:        {_fmt_stats(m['search_ms'], 's', 0.001)}",
        f"  caller waited after story: {_fmt_stats(m['story_wait'], 's')}",
        f"  LLM understood the story: {_fmt_pct(m['llm_used'], m['stories'])}",
        "",
        "Occupation read-back (the caller's own confirmation):",
        f"  confirmed one of the 3:   {_fmt_pct(m['confirmed'], m['readbacks'])}",
        f"  it was the first one:     {_fmt_pct(m['confirmed_first'], m['readbacks'])}",
        "",
        "Options:",
        f"  offered on the call:      {_fmt_pct(m['offered'], m['calls'])}",
        f"  asked to hear details:    {_fmt_pct(m['heard_detail'], m['offered'])}",
        f"  chose an option:          {_fmt_pct(m['chosen'], m['offered'])}",
        "  kinds offered: "
        + (", ".join(f"{k} {v}" for k, v in sorted(m["option_kinds"].items())) or "none"),
        "",
        f"No-answer repeats: {m['timeouts']}   Problems logged: {m['problems']}",
        f"Prompt played late by (from the api log): {_fmt_stats(m['lags'], 's')}",
    ]
    return "\n".join(lines)
