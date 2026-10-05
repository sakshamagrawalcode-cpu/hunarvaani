"""The LLM's only job: read what the person said and return labels with their own words as proof.

Labels: facts (occupation codes from our list, years, skills, aspiration, constraints), emphasis
(how strongly they care about each ranking factor) and mood. Code checks every label: codes must
be in our list, and an emphasis label is kept only if its quote really appears in what was said.
"""

import re
import unicodedata
from dataclasses import dataclass, field

from .data import Data
from .profile import FACTORS, MOODS, STRENGTH, Profile
from .understand import (EDUCATION_LEVELS, numbers, parse_age, parse_education, parse_gender, parse_name,
                         parse_travel, parse_yes_no)

LEANS = ("job", "own_work", "either")
HEALTH = ("none", "some", "severe")


def schema(data: Data, follow_ups: list[str] | tuple = ()) -> dict:
    """JSON schema handed to Ollama (structured output), so the model can only answer in this shape."""
    codes = sorted(data.occupations)
    return {
        "type": "object",
        "properties": {
            "occupation_codes": {"type": "array", "items": {"type": "integer", "enum": codes}, "maxItems": 3},
            "years_experience": {"type": ["integer", "null"]},
            "skills": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
            "aspiration_codes": {"type": "array", "items": {"type": "integer", "enum": codes}, "maxItems": 3},
            "aspiration_sector": {"type": ["string", "null"], "enum": sorted(data.sectors) + [None]},
            "lean": {"type": ["string", "null"], "enum": list(LEANS) + [None]},
            "cannot_leave_home": {"type": ["boolean", "null"]},
            "max_travel_km": {"type": ["integer", "null"]},
            "health_limit": {"type": ["string", "null"], "enum": list(HEALTH) + [None]},
            "family_occupation_code": {"type": ["integer", "null"]},
            "continue_family_work": {"type": ["boolean", "null"]},
            "name": {"type": ["string", "null"]},
            "age": {"type": ["integer", "null"]},
            "gender": {"type": ["string", "null"], "enum": ["female", "male", "other", None]},
            "education": {"type": ["string", "null"], "enum": list(EDUCATION_LEVELS) + [None]},
            "max_travel_minutes": {"type": ["integer", "null"]},
            "travel_mode": {"type": ["string", "null"], "enum": ["walk", "cycle", "bus", "own_vehicle", None]},
            "hostel_ok": {"type": ["boolean", "null"]},
            "yes_no": {"type": ["boolean", "null"]},
            "choice": {"type": ["integer", "null"], "enum": [1, 2, 3, None]},
            "training_weeks": {"type": ["integer", "null"]},
            "follow_up": {"type": ["string", "null"], "enum": list(follow_ups) + [None]},
            "emphasis": {"type": "array", "maxItems": 4, "items": {
                "type": "object",
                "properties": {"factor": {"type": "string", "enum": list(FACTORS)},
                               "strength": {"type": "string", "enum": list(STRENGTH)},
                               "intensity": {"type": "number", "minimum": 0, "maximum": 1},
                               "quote": {"type": "string"}},
                "required": ["factor", "strength", "quote"]}},
            "mood": {"type": "string", "enum": list(MOODS)},
        },
        "required": ["occupation_codes", "emphasis", "mood"],
    }


FOLLOW_UP_HELP = {
    "q_goal": "grow in their current work or learn something new",
    "q_lead": "check that the best-matching work suits them",
    "q_home": "work from home or go out to work",
    "q_duration": "how long a training they can do",
    "q_earn_soon": "need to earn soon or can learn first",
    "q_certificate": "a certificate for skills they already have",
    "q_own_business": "start their own business with a loan",
    "q_years": "years of experience in their work",
    "ask_aspiration": "what work they want",
    "ask_family": "their family's work",
    "say_health": "physical limits",
    "say_lean": "salaried job or own work",
}


def system_prompt(data: Data, follow_ups: list[str] | tuple = ()) -> str:
    follow_up_help = "; ".join(f"{k} ({FOLLOW_UP_HELP.get(k, k)})" for k in follow_ups) or "none"
    occ = "\n".join(f"{o.code}: {o.title_en} / {o.title_hi} / {o.title_mr}" for o in data.occupations.values())
    sectors = ", ".join(sorted(data.sectors))
    return f"""You label what a job seeker said on a phone call in India (Hindi, Marathi or English).
You are told the question that was asked and what is already known about the person.
You never give advice and never rank. Answer only with JSON in the given schema.

Rules:
- occupation_codes: the person's CURRENT or past work, only codes from the list below.
- aspiration_codes / aspiration_sector: the work they WANT to do or learn. Sectors: {sectors}.
- lean: "job" (salaried job), "own_work" (own business or self-employed) or "either".
- cannot_leave_home: true only if they say they cannot leave home / family / children to stay elsewhere.
- health_limit: "some" or "severe" only if they mention pain, illness or disability affecting work.
- emphasis: how strongly they care about a ranking factor. factor is one of
  aspiration (doing the work they want), skill (using what they already know), demand (jobs nearby),
  access (staying close to home), completion (short, easy to finish), income (pay).
  strength: insists (must have, non-negotiable), prefers (would like), neutral, doesnt_care.
  intensity: 0..1, how forcefully they said it (0.5 = plain statement, 1 = repeated or emphatic).
  quote: copy the exact words from the transcript that show it. No quote, no label.
- mood: hopeful, worried, upset or neutral, from how they speak.
- name, age, gender, education: only if the person says them in THIS answer. education is one of
  none, upto_5th, upto_8th, 10th, 12th, graduate (ITI or diploma counts as 12th).
- max_travel_km, max_travel_minutes, travel_mode, hostel_ok: how far they can travel each day for
  training; give minutes if they answer in time; hostel_ok true if they can stay away from home.
- yes_no: their answer to a yes/no question. choice: for a question that offers options, the number
  of the option they picked, in the order the question mentions them (1, 2 or 3).
- training_weeks: the longest training they can do, in weeks (one month = 4); 0 if any length is fine.
- follow_up: the ONE next question that would best help find the right work for this person, given
  what they said and what is already known: {follow_up_help}. null if nothing more is needed.
- Leave anything not said as null or an empty list. Never guess.

Occupations (code: English / Hindi / Marathi):
{occ}
"""


@dataclass
class Labels:
    occupation_codes: list[int] = field(default_factory=list)
    years: int | None = None
    skills: list[str] = field(default_factory=list)
    aspiration_codes: list[int] = field(default_factory=list)
    aspiration_sector: str | None = None
    lean: str | None = None
    cannot_leave_home: bool | None = None
    max_travel_km: int | None = None
    health: str | None = None
    family_code: int | None = None
    continue_family: bool | None = None
    emphasis: list[dict] = field(default_factory=list)
    mood: str = "neutral"
    name: str | None = None
    age: int | None = None
    gender: str | None = None
    education: str | None = None
    max_travel_minutes: int | None = None
    travel_mode: str | None = None
    hostel_ok: bool | None = None
    yes_no: bool | None = None
    choice: int | None = None
    training_weeks: int | None = None
    follow_up: str | None = None
    rejected: list[str] = field(default_factory=list)  # labels thrown out by the checks, for the log


def _norm(text: str) -> str:
    """Lower-case, drop punctuation and symbols, keep Indic vowel signs (they are not \\w in re)."""
    text = unicodedata.normalize("NFC", text or "").lower()
    text = "".join(" " if unicodedata.category(ch)[0] in "PS" else ch for ch in text)
    return re.sub(r"\s+", " ", text).strip()


def quote_found(quote: str, transcript: str) -> bool:
    """True if the quote is in the transcript, or most of its words are (STT spellings vary)."""
    q, t = _norm(quote), _norm(transcript)
    if not q:
        return False
    if q in t:
        return True
    words = q.split()
    have = set(t.split())
    return len(words) > 0 and sum(w in have for w in words) / len(words) >= 0.6


def validate(raw: dict, transcript: str, data: Data) -> Labels:
    out = Labels()
    codes = set(data.occupations)

    def pick_codes(values) -> list[int]:
        result = []
        for v in values or []:
            if isinstance(v, int) and v in codes and v not in result:
                result.append(v)
            else:
                out.rejected.append(f"code {v!r} not in our list")
        return result[:3]

    out.occupation_codes = pick_codes(raw.get("occupation_codes"))
    out.aspiration_codes = pick_codes(raw.get("aspiration_codes"))
    years = raw.get("years_experience")
    out.years = years if isinstance(years, int) and 0 <= years <= 60 else None
    out.skills = [s for s in raw.get("skills") or [] if isinstance(s, str) and s.strip()][:6]
    sector = raw.get("aspiration_sector")
    out.aspiration_sector = sector if sector in data.sectors else None
    out.lean = raw.get("lean") if raw.get("lean") in LEANS else None
    out.cannot_leave_home = raw.get("cannot_leave_home") if isinstance(raw.get("cannot_leave_home"), bool) else None
    km = raw.get("max_travel_km")
    out.max_travel_km = km if isinstance(km, int) and 1 <= km <= 200 else None
    out.health = raw.get("health_limit") if raw.get("health_limit") in HEALTH else None
    fam = raw.get("family_occupation_code")
    out.family_code = fam if isinstance(fam, int) and fam in codes else None
    cf = raw.get("continue_family_work")
    out.continue_family = cf if isinstance(cf, bool) else None
    for e in raw.get("emphasis") or []:
        if not isinstance(e, dict):
            continue
        f, s, q = e.get("factor"), e.get("strength"), e.get("quote", "")
        if f in FACTORS and s in STRENGTH and quote_found(q, transcript):
            i = e.get("intensity")
            i = min(1.0, max(0.0, float(i))) if isinstance(i, (int, float)) else 0.5
            out.emphasis.append({"factor": f, "strength": s, "intensity": i, "quote": q})
        else:
            out.rejected.append(f"emphasis {f}/{s} without a matching quote")
    out.mood = raw.get("mood") if raw.get("mood") in MOODS else "neutral"
    name = raw.get("name")
    if isinstance(name, str) and name.strip() and len(name) <= 40:
        if quote_found(name, transcript):
            out.name = name.strip()
        else:
            out.rejected.append(f"name {name!r} not in what was said")
    age = raw.get("age")
    out.age = age if isinstance(age, int) and 14 <= age <= 80 else None
    out.gender = raw.get("gender") if raw.get("gender") in ("female", "male", "other") else None
    out.education = raw.get("education") if raw.get("education") in EDUCATION_LEVELS else None
    mins = raw.get("max_travel_minutes")
    out.max_travel_minutes = mins if isinstance(mins, int) and 1 <= mins <= 300 else None
    out.travel_mode = raw.get("travel_mode") if raw.get("travel_mode") in ("walk", "cycle", "bus", "own_vehicle") else None
    for key in ("hostel_ok", "yes_no"):
        setattr(out, key, raw.get(key) if isinstance(raw.get(key), bool) else None)
    choice = raw.get("choice")
    out.choice = choice if choice in (1, 2, 3) else None
    weeks = raw.get("training_weeks")
    out.training_weeks = weeks if isinstance(weeks, int) and 0 <= weeks <= 104 else None
    out.follow_up = raw.get("follow_up") if isinstance(raw.get("follow_up"), str) else None
    return out


def apply(labels: Labels, p: Profile, transcript: str) -> None:
    """Merge checked labels into the profile. Keypad answers given earlier are not overwritten."""
    for c in labels.occupation_codes:
        if c not in p.occupation_codes:
            p.occupation_codes.append(c)
    for c in labels.aspiration_codes:
        if c not in p.aspiration_codes:
            p.aspiration_codes.append(c)
    p.aspiration_sector = labels.aspiration_sector or p.aspiration_sector
    p.years = labels.years if labels.years is not None else p.years
    p.skills = list(dict.fromkeys(p.skills + labels.skills))[:10]
    p.lean = p.lean or labels.lean
    if labels.cannot_leave_home:
        p.cannot_leave_home = True
    p.radius_km = p.radius_km or labels.max_travel_km
    if labels.health and labels.health != "none":
        p.health = labels.health
    if labels.family_code:
        p.family_code = labels.family_code
    if labels.continue_family is not None:
        p.continue_family = labels.continue_family
    # details volunteered in a free answer ("I am 35, studied up to 10th ...") are kept, so the
    # follow-up questions do not ask them again; they never overwrite a direct answer
    if labels.name and not p.name:
        p.name = labels.name
    if labels.age and p.age is None:
        p.age = labels.age
    if labels.gender and p.gender is None:
        p.gender = labels.gender
    if labels.education and p.education is None:
        p.education = labels.education
    if labels.hostel_ok is not None and p.hostel_ok is None:
        p.hostel_ok = False if p.cannot_leave_home else labels.hostel_ok
    for e in labels.emphasis:
        p.emphasis[e["factor"]] = e["strength"]
        p.evidence.append({"field": f"emphasis.{e['factor']}", "factor": e["factor"], "strength": e["strength"],
                           "intensity": e.get("intensity", 0.5), "quote": e["quote"], "source": "llm"})
    p.moods.append(labels.mood)


# ----------------------------------------------------------------------------------------------
# Rule-based stand-in for the LLM: lets the whole system run with no GPU (tests, UI work, demos).
# It matches the occupation aliases in our data and a few phrase lists. Not used with HV_MODELS=real.
_PHRASES = {
    ("access", "insists"): ["घर छोड़", "घर नहीं छोड़", "बच्चे", "can't leave", "cannot leave", "घर सोडू", "मुलं"],
    ("access", "prefers"): ["पास में", "नज़दीक", "nearby", "near home", "जवळ"],
    ("aspiration", "insists"): ["ही सीखनी", "ही करना है", "only want", "सिर्फ", "फक्त"],
    ("aspiration", "doesnt_care"): ["कुछ भी", "anything", "काहीही", "कोई भी काम"],
    ("income", "prefers"): ["कमाई", "पैसा", "पैसे", "income", "salary", "पगार", "money"],
}
_MOOD = {
    "upset": ["नौकरी चली गई", "निकाल दिया", "lost my job", "दुख", "परेशान", "upset", "नोकरी गेली"],
    "worried": ["डर", "चिंता", "worried", "पता नहीं", "काळजी", "भीती"],
    "hopeful": ["उम्मीद", "खुश", "hope", "excited", "आशा"],
}
_WANT = ["चाहती", "चाहता", "चाहते", "सीखना", "सीखनी", "सीखने", "करना है", "want", "like to", "learn", "इच्छा",
         "शिकायचं", "हवं", "करायचं"]


_STORY_AGE = ["उम्र", "वय", "age", "साल की", "साल का", "years old", "वर्षांचा", "वर्षांची", "वर्षाची", "वर्षाचा"]
_NAME_RE = re.compile(r"(?:मेरा नाम|my name is|माझं नाव|माझे नाव|मेरा नाम है)\s+([^\s,।.]+(?:\s+[^\s,।.]+)?)",
                      re.IGNORECASE)


def fake_label(transcript: str, data: Data, question: str = "") -> dict:
    """Rule-based stand-in for the LLM (no GPU). Reads the same fields, more crudely."""
    raw = _fake_core(transcript, data)
    if question in ("ask_story", "ask_aspiration", "ask_family", "review_work", ""):
        m = _NAME_RE.search(transcript or "")
        if m:
            raw["name"] = parse_name(m.group(1))
        if any(_norm(w) in _norm(transcript) for w in _STORY_AGE):
            raw["age"] = parse_age(transcript)
        raw["education"] = parse_education(transcript)
        t = parse_travel(transcript)
        if any(w in _norm(transcript) for w in ("किलोमीटर", "km", "kilometre", "मिनट", "minutes")):
            raw["max_travel_km"] = t["km"]
        if t["hostel_ok"] is not None:
            raw["hostel_ok"] = t["hostel_ok"]
    else:
        raw["name"] = parse_name(transcript) if question == "ask_name" else None
        raw["age"] = parse_age(transcript) if question == "say_age" else None
        raw["gender"] = parse_gender(transcript) if question == "say_gender" else None
        raw["education"] = parse_education(transcript) if question == "say_education" else None
        raw["yes_no"] = parse_yes_no(transcript)
    return raw


def _years_of_work(transcript: str) -> int | None:
    """'पाँच साल से सिलाई' -> 5; an age ('45 साल की हूँ', 'उम्र 45 साल') is not experience."""
    words = _norm(transcript).split()
    for v, i in numbers(transcript):
        before, after = words[max(0, i - 3): i], words[i + 1: i + 3]
        if not 0 <= v <= 60 or not after or any(w in ("उम्र", "वय", "age", "aged") for w in before):
            continue
        if after[0] in ("साल", "वर्ष", "वर्षं", "वर्षे", "years", "year", "बरस", "वर्षांपासून", "वर्षापासून"):
            if len(after) > 1 and after[1] in ("की", "का", "old", "वय", "चा", "ची"):
                continue  # an age
            return v
    return None


def _fake_core(transcript: str, data: Data) -> dict:
    text = _norm(transcript)
    raw: dict = {"occupation_codes": [], "aspiration_codes": [], "emphasis": [], "mood": "neutral", "skills": []}
    want_at = min([text.find(_norm(w)) for w in _WANT if _norm(w) in text] or [len(text) + 1])
    for code, aliases in data.aliases.items():
        for a in aliases:
            a_n = _norm(a)
            if len(a_n) < 3:
                continue
            pos = text.find(a_n)
            if pos >= 0:
                key = "aspiration_codes" if pos > want_at else "occupation_codes"
                if code not in raw[key]:
                    raw[key].append(code)
                break
    careless = any(_norm(p) in text for p in _PHRASES[("aspiration", "doesnt_care")])
    if not raw["aspiration_codes"] and want_at <= len(text) and raw["occupation_codes"] and not careless:
        raw["aspiration_codes"] = raw["occupation_codes"][:1]
    raw["years_experience"] = _years_of_work(transcript)
    for (factor, strength), phrases in _PHRASES.items():
        for ph in phrases:
            if _norm(ph) in text:
                raw["emphasis"].append({"factor": factor, "strength": strength, "quote": ph})
                break
    if any(_norm(p) in text for p in _PHRASES[("access", "insists")]):
        raw["cannot_leave_home"] = True
    if any(w in text for w in ["घुटन", "knee", "दर्द", "pain", "गुडघ", "बीमार", "illness"]):
        raw["health_limit"] = "some"
    if any(_norm(w) in text for w in ["अपना काम", "own business", "व्यवसाय", "खुद का", "स्वतःचा", "खोलना", "खोलनी",
                                      "अपनी दुकान", "अपना पार्लर", "own shop", "स्वतःचं दुकान", "सुरू करायचं"]):
        raw["lean"] = "own_work"
    elif any(_norm(w) in text for w in ["नौकरी", "job", "नोकरी"]):
        raw["lean"] = "job"
    for mood, phrases in _MOOD.items():
        if any(_norm(p) in text for p in phrases):
            raw["mood"] = mood
            break
    return raw
