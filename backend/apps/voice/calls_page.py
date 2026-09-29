"""The team's calls page: one row per call with answers, own words, read-back and timings."""

from html import escape

from core import store
from core.config import Settings
from core.phone import decrypt, last4

STEPS = ("q_age", "q_gender", "q_education", "q_travel", "q_physical", "q_lean")
LABELS = {
    "none": "no schooling",
    "upto_5th": "up to 5th",
    "upto_8th": "up to 8th",
    "10th": "10th pass",
    "12th": "12th pass",
    "iti_or_diploma": "ITI / diploma",
    "graduate": "graduate",
    "village": "only in village",
    "10km": "up to 10 km",
    "30km": "up to 30 km",
    "district_hq": "district HQ",
    "hostel": "can stay in hostel",
    "job": "regular job",
    "own_work": "own work",
    "unsure": "not sure",
    "under_18": "under 18",
    "18_25": "18–25",
    "26_35": "26–35",
    "36_45": "36–45",
    "46_60": "46–60",
    "over_60": "over 60",
    "female": "woman",
    "male": "man",
    "other": "other",
    "not_said": "not said",
    "some": "some difficulty",
}
LANGUAGE_NAMES = {"hi-IN": "Hindi", "en-IN": "English", "mr-IN": "Marathi"}
STYLE = """
body{font-family:system-ui,sans-serif;margin:16px;color:#1b1b1b;background:#fafafa}
h1{font-size:20px} table{border-collapse:collapse;width:100%;background:#fff}
th,td{border:1px solid #ddd;padding:6px 8px;vertical-align:top;font-size:13px;text-align:left}
th{background:#f0f0f0;position:sticky;top:0} .muted{color:#777} .flag{color:#b00020;font-weight:600}
@media (prefers-color-scheme: dark){body{background:#121212;color:#e6e6e6}
table{background:#1c1c1c} th{background:#262626} th,td{border-color:#333} .muted{color:#999}}
"""


def _fmt(ts) -> str:
    from core.timeutil import IST

    return ts.astimezone(IST).strftime("%d %b %H:%M:%S") if ts else "—"


def _number(settings: Settings, enc) -> str:
    if not enc or not settings.phone_enc_key:
        return "—"
    try:
        return last4(decrypt(enc, settings.phone_enc_key))
    except Exception:
        return "—"


def _seconds(a, b) -> str:
    return f"{(b - a).total_seconds():.0f} s" if a and b else "—"


def render(settings: Settings, limit: int = 50) -> str:
    with store.connect(settings.database_url) as conn:
        titles = {
            r["nco_code"]: r["title_hi"]
            for r in conn.execute("SELECT nco_code, title_hi FROM nco").fetchall()
        }
        calls = conn.execute(
            "SELECT * FROM call ORDER BY COALESCE(answered_at, callback_at, missed_at) DESC "
            "NULLS LAST LIMIT %s",
            (limit,),
        ).fetchall()
        rows = []
        for c in calls:
            cid = c["id"]
            answers = {
                a["step"]: a["value"]
                for a in conn.execute(
                    "SELECT step, value FROM answer WHERE call_id = %s ORDER BY created_at", (cid,)
                )
            }
            stories = conn.execute(
                "SELECT * FROM story WHERE call_id = %s ORDER BY created_at", (cid,)
            ).fetchall()
            consents = ", ".join(
                f"{k['kind']}:{'yes' if k['granted'] else 'no'}"
                for k in conn.execute(
                    "SELECT kind, granted FROM consent WHERE call_id = %s ORDER BY created_at",
                    (cid,),
                )
            )
            rows.append((c, answers, stories, consents))

    def cell(value) -> str:
        if value in (None, ""):
            return "<td><span class=muted>—</span></td>"
        return f"<td>{escape(str(value))}</td>"

    out = []
    for c, answers, stories, consents in rows:
        story = stories[-1] if stories else None
        own_words = " / ".join(s["transcript"] for s in stories if s["transcript"])
        occupation = answers.get("occupation") or answers.get("trades")
        via = "read-back" if answers.get("occupation") else ("keypad list" if occupation else "")
        heard = []
        if story:
            for code in (story["top1"], story["top2"]):
                if code:
                    heard.append(f"{code} {titles.get(code, '')}")
        timings = []
        if story and story["stt_ms"] is not None:
            timings.append(f"STT {story['stt_ms']} ms")
        if story and story["search_ms"] is not None:
            timings.append(f"search {story['search_ms']} ms")
        callback = _seconds(c["missed_at"], c["answered_at"]) if c["missed_at"] else ""
        flags = []
        if c["human_flag"]:
            flags.append("human")
        if c["keypad_only"]:
            flags.append("keypad only")
        out.append(
            "<tr>"
            + cell(_fmt(c["answered_at"] or c["callback_at"] or c["missed_at"]))
            + cell(_number(settings, c["phone_enc"]))
            + cell(c["status"])
            + cell(LANGUAGE_NAMES.get(c["language"], c["language"]))
            + cell(f"{c['duration_seconds']} s" if c["duration_seconds"] is not None else "")
            + "".join(cell(LABELS.get(answers.get(s), answers.get(s))) for s in STEPS)
            + cell(own_words)
            + cell(" / ".join(heard))
            + cell(f"{occupation} {titles.get(occupation, '')} ({via})" if occupation else "")
            + cell(", ".join(timings + ([f"callback {callback}"] if callback else [])))
            + cell(consents)
            + (f"<td class=flag>{escape(', '.join(flags))}</td>" if flags else cell(""))
            + "</tr>"
        )
    head = (
        "<tr><th>When (IST)</th><th>Number</th><th>Status</th><th>Language</th><th>Duration</th>"
        "<th>Age</th><th>Gender</th><th>Education</th><th>Travel</th><th>Physical</th>"
        "<th>Prefers</th><th>Own words</th>"
        "<th>Search top 2</th><th>Occupation</th><th>Timings</th><th>Consents</th>"
        "<th>Flags</th></tr>"
    )
    body = "".join(out) or "<tr><td colspan=17 class=muted>No calls yet.</td></tr>"
    return (
        "<!doctype html><html lang=hi><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>HunarVaani calls</title><style>{STYLE}</style></head><body>"
        f"<h1>HunarVaani calls</h1><p class=muted>Latest {len(rows)} calls. "
        "Numbers show only the last four digits.</p>"
        f"<div style='overflow-x:auto'><table>{head}{body}</table></div></body></html>"
    )
