"""Plain-language explanations of every decision, for the officer console (live call and person page).

Nothing here decides anything. It reads what the LLM checks, the question planner and the ranker
already did, and says it in short English sentences an officer can check against the person's own
words: what was heard, why the next question was asked, why an option is on the list, and why other
work was left out (which gate removed it, with the numbers behind it).
"""

from .data import EDUCATION_ORDER, Data
from .labels import FOLLOW_UP_HELP, Labels
from .policy import FACTORS, Policy
from .profile import Profile
from .prompts import T
from .ranker import Ctx, gate_value, load, rank

FACTOR_LABEL = {"aspiration": "Wants", "skill": "Skills", "demand": "Demand", "access": "Nearby",
                "completion": "Easy to finish", "income": "Pay"}
FACTOR_TEXT = {"aspiration": "doing the work they want", "skill": "using the skills they already have",
               "demand": "work that is in demand in their district", "access": "staying close to home",
               "completion": "a short course that is easy to finish", "income": "better pay"}
STRENGTH_TEXT = {"insists": "insists on", "prefers": "would like", "neutral": "is neutral about",
                 "doesnt_care": "does not mind much about", "tradeoff_win": "chose", "tradeoff_lose": "gave up"}
GATE_LABEL = {"work_capacity": "Physical load", "distance": "Distance", "eligibility": "Eligibility",
              "preference": "Said no", "duration": "Course length", "relevance": "Unrelated work"}
EDU_TEXT = {"none": "no schooling", "upto_5th": "up to class 5", "upto_8th": "up to class 8", "10th": "class 10",
            "12th": "class 12", "graduate": "graduate"}
GENDER_TEXT = {"female": "woman", "male": "man", "other": "prefers not to say"}
HEALTH_TEXT = {"none": "no physical limits", "some": "some physical limits", "severe": "severe physical limits"}
LEAN_TEXT = {"job": "a salaried job", "own_work": "their own work", "either": "a job or own work"}
KIND_TEXT = {"upskill": "training", "certificate": "a certificate for skills already held (RPL)",
             "startup": "support to start their own work"}
QUESTION_NAME = {"ask_name": "name", "say_age": "age", "say_gender": "woman / man", "say_education": "studies",
                 "say_travel": "daily travel", "say_health": "physical limits", "say_lean": "job or own work",
                 "ask_story": "their story", "ask_aspiration": "work they want", "ask_family": "family's work",
                 "q_goal": "grow in their work or learn something new", "q_lead": "check the best-matching work",
                 "q_home": "from home or go out", "q_duration": "longest training", "q_earn_soon": "earn soon or learn first",
                 "q_certificate": "certificate for their skills", "q_own_business": "start their own business",
                 "q_years": "years of experience", "review_ok": "check what was understood",
                 "confirm_choice": "confirm the option", "choose_prompt": "pick an option",
                 "consent": "consent", "consent_ai": "consent for AI training", "returning": "new or returning"}


def question_name(key: str) -> str:
    return QUESTION_NAME.get(key, FOLLOW_UP_HELP.get(key, key.replace("_", " ")))


def question_text(key: str, data: Data | None = None, lead: str | None = None) -> str:
    """The English wording of a spoken question (what the person heard, in their language)."""
    if key == "q_lead":
        s = data.sectors.get(lead or "") if data else None
        return f"{T['q_lead_pre'][2]} {s.title_en if s else lead or ''}. {T['q_lead_post'][2]}"
    return T[key][2] if key in T else question_name(key)


def _occ(data: Data, codes) -> str:
    return ", ".join(data.occupations[c].title_en for c in codes if c in data.occupations)


def _pct(x: float) -> str:
    return f"{round(100 * x)}%"


# ---- what the LLM heard --------------------------------------------------------------------------
def labels(lab: Labels, data: Data) -> list[str]:
    """What the LLM labelled in one answer, after the checks (codes in our list, quotes really said)."""
    out = []
    if lab.occupation_codes:
        out.append(f"Work they do: {_occ(data, lab.occupation_codes)}")
    if lab.years is not None:
        out.append(f"Years in that work: {lab.years}")
    if lab.aspiration_codes:
        out.append(f"Wants to do: {_occ(data, lab.aspiration_codes)}")
    elif lab.aspiration_sector in data.sectors:
        out.append(f"Wants work in: {data.sectors[lab.aspiration_sector].title_en}")
    if lab.family_code in data.occupations:
        out.append(f"Family's work: {data.occupations[lab.family_code].title_en}")
    for attr, text in (("name", "Name"), ("age", "Age")):
        if getattr(lab, attr):
            out.append(f"{text}: {getattr(lab, attr)}")
    if lab.gender:
        out.append(f"Woman / man: {GENDER_TEXT.get(lab.gender, lab.gender)}")
    if lab.education:
        out.append(f"Studied: {EDU_TEXT.get(lab.education, lab.education)}")
    if lab.max_travel_km:
        out.append(f"Can travel: {lab.max_travel_km} km a day")
    elif lab.max_travel_minutes:
        out.append(f"Can travel: {lab.max_travel_minutes} minutes{' by ' + lab.travel_mode if lab.travel_mode else ''}")
    if lab.cannot_leave_home:
        out.append("Cannot leave home to stay elsewhere")
    if lab.hostel_ok is not None:
        out.append("Hostel is fine" if lab.hostel_ok else "No hostel")
    if lab.health and lab.health != "none":
        out.append(f"Health: {HEALTH_TEXT[lab.health]}")
    if lab.lean:
        out.append(f"Prefers {LEAN_TEXT[lab.lean]}")
    if lab.yes_no is not None:
        out.append(f"Answer: {'yes' if lab.yes_no else 'no'}")
    if lab.choice:
        out.append(f"Picked choice {lab.choice}")
    if lab.training_weeks is not None:
        out.append("Any course length is fine" if lab.training_weeks == 0 else f"Longest training: {lab.training_weeks} weeks")
    for e in lab.emphasis:
        out.append(f"{STRENGTH_TEXT.get(e['strength'], e['strength']).capitalize()} {FACTOR_TEXT[e['factor']]}: "
                   f"“{e['quote']}”")
    if lab.mood != "neutral":
        out.append(f"Sounds {lab.mood}: the next questions are worded more gently" if lab.mood in ("worried", "upset")
                   else f"Sounds {lab.mood}")
    if lab.follow_up:
        out.append(f"LLM suggests asking next: {question_name(lab.follow_up)}")
    for r in lab.rejected:
        out.append(f"Thrown out by the checks: {r}")
    return out or ["Nothing usable in this answer"]


def slot(key: str, p: Profile) -> str:
    """One detail read by the simple rules, as the console shows it."""
    if key == "say_age":
        return f"Age: {p.age}"
    if key == "say_gender":
        return f"Woman / man: {GENDER_TEXT.get(p.gender or '', '?')}"
    if key == "say_education":
        return f"Studied: {EDU_TEXT.get(p.education or '', '?')}"
    if key == "say_travel":
        extra = " · cannot leave home" if p.cannot_leave_home else " · hostel fine" if p.hostel_ok else ""
        return f"Daily travel: {p.radius_km} km{extra}"
    if key == "say_health":
        return f"Health: {HEALTH_TEXT.get(p.health, p.health)}"
    if key == "say_lean":
        return f"Prefers {LEAN_TEXT.get(p.lean or '', '?')}"
    if key == "ask_name":
        return f"Name: {p.name}"
    if key == "q_years":
        return f"Years of experience: {p.years}"
    return f"Answer to “{question_name(key)}” understood"


# ---- why this question ---------------------------------------------------------------------------
def plan(key: str, score: float, why: str, scores: dict[str, float], lead: str | None, data: Data,
         shortlist: list[dict] | None = None) -> dict:
    """Why the next question was picked over the others still open."""
    cands = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    lines = [f"Picked “{question_name(key)}”: {why}."]
    others = [f"{question_name(k)} ({v:.2f})" for k, v in cands if k != key][:4]
    if others:
        lines.append("Other questions still open: " + ", ".join(others) + ".")
    if lead in data.sectors:
        lines.append(f"Best-matching work so far: {data.sectors[lead].title_en}.")
    if shortlist:
        lines.append("Shortlist right now: " + "; ".join(f"{o['rank']}. {o['course']} ({o['score']:.2f})"
                                                         for o in shortlist) + ".")
    return {"lines": lines, "question": key, "text": question_text(key, data, lead), "score": round(score, 3),
            "shortlist": shortlist or [],
            "candidates": [{"key": k, "name": question_name(k), "value": round(v, 3), "picked": k == key}
                           for k, v in cands[:8]]}


def shortlist(data: Data, p: Profile, pol: Policy, n: int = 3) -> list[dict]:
    return [{"rank": i, "course": o.course.title_en, "score": round(o.score, 3)}
            for i, o in enumerate(rank(data, p, n, policy=pol), 1)]


# ---- why an option, and why not the others ---------------------------------------------------------
def weights(p: Profile, pol: Policy, ctx: Ctx | None = None) -> list[dict]:
    """Base weight w (officers), the person's multiplier m (their own words) and the share w·m."""
    from .emphasis import multiplier

    mult = ctx.mult if ctx else {k: multiplier(p, k, pol) for k in FACTORS}
    raw = {k: pol.weights[k] * mult[k] for k in FACTORS}
    total = sum(raw.values()) or 1
    return [{"factor": k, "label": FACTOR_LABEL[k], "base": round(pol.weights[k], 1), "m": round(mult[k], 2),
             "share": round(raw[k] / total, 3)} for k in FACTORS]


def option(o: dict) -> dict:
    """One option (an Option.summary() or a stored option): score = gates × fit, and the main reasons."""
    w, f, g = o.get("weights") or {}, o.get("factors") or {}, o.get("gates") or {}
    parts = {k: w.get(k, 0) * f.get(k, 0) for k in FACTORS}
    fit = sum(parts.values())
    gate = 1.0
    for v in g.values():
        gate *= v
    top = sorted(parts, key=parts.get, reverse=True)[:2]
    reasons = " and ".join(FACTOR_TEXT[k] for k in top if f.get(k, 0) >= 0.5) or "the best of what is left"
    held_back = [f"{GATE_LABEL.get(k, k)} ×{v:.2f}" for k, v in g.items() if v < 0.999]
    weeks = max(1, round((o.get("hours") or 0) / 40))
    sentence = (f"{o.get('course')} at {o.get('centre')} ({o.get('distance_km')} km, about {weeks} week{'s' if weeks > 1 else ''}"
                f"{', free' if not o.get('fee_inr') else ''}): fit {fit:.2f} × gates {gate:.2f} = {o.get('score', 0):.2f}. "
                f"Mostly because it means {reasons}.")
    if held_back:
        sentence += " Held back by: " + ", ".join(held_back) + "."
    return {"sentence": sentence, "fit": round(fit, 3), "gate": round(gate, 3),
            "contrib": [{"factor": k, "label": FACTOR_LABEL[k], "f": round(f.get(k, 0), 3), "w": round(w.get(k, 0), 3),
                         "part": round(parts[k], 3)} for k in FACTORS],
            "held_back": held_back}


def gate_reasons(data: Data, p: Profile, o, pol: Policy, ctx: Ctx) -> list[str]:
    """Why the gates held an option back, with the numbers (o is a ranker Option)."""
    course, centre, g = o.course, o.centre, o.gates
    out = []
    if g["work_capacity"] < 0.999:
        who = f"age {p.age}" if p.age else "their age"
        if p.health != "none":
            who += f" with {HEALTH_TEXT[p.health]}"
        out.append(f"physical load {load(data, course, pol)} of 5 is above what fits {who} "
                   f"(capacity {ctx.capacity:.1f})")
    if g["distance"] < 0.999:
        d = centre.distance_km
        if g["distance"] == 0:
            out.append(f"residential centre {d} km away, and they "
                       + ("cannot leave home" if p.cannot_leave_home else "do not want a hostel"))
        else:
            out.append(f"{d} km away, beyond their {ctx.radius:g} km daily travel")
    if g["eligibility"] < 0.999:
        age = p.age or 30
        if not course.min_age <= age <= course.max_age:
            out.append(f"the course is for ages {course.min_age}–{course.max_age}")
        elif p.education and course.min_education in EDUCATION_ORDER and p.education in EDUCATION_ORDER \
                and EDUCATION_ORDER.index(p.education) < EDUCATION_ORDER.index(course.min_education):
            out.append(f"needs {EDU_TEXT[course.min_education]}; they studied {EDU_TEXT[p.education]}")
        elif set(course.nco_codes) & pol.consent_only:
            out.append("caste-linked work: offered only if the person brings it up")
        elif course.kind == "certificate":
            out.append("a certificate (RPL) is only for skills they already have")
        else:
            out.append("not eligible")
    if g["preference"] < 0.999:
        out.append("they said no to this kind of work")
    if g["duration"] < 0.999:
        out.append(f"{max(1, round(course.hours / 40))} weeks, longer than the {p.max_weeks} weeks they can give")
    if g["relevance"] < 0.999:
        out.append("not related to the work they do or want")
    return out


def ranking(data: Data, p: Profile, pol: Policy, options: list, n_left_out: int = 5) -> dict:
    """The whole ranking in plain words: the weights for this person, every option on the list, and
    the strongest options the gates left out."""
    ctx = Ctx(data, p, pol)
    w = weights(p, pol, ctx)
    picked = {o.course.course_id for o in options}
    every = rank(data, p, keep_dropped=True, policy=pol)
    left_out, seen = [], set()
    plain_fit = lambda o: sum(o.weights[k] * o.factors[k] for k in FACTORS)  # noqa: E731
    for o in sorted(every, key=plain_fit, reverse=True):
        if o.course.course_id in picked or o.course.course_id in seen or gate_value(o.gates) >= 0.5:
            continue
        seen.add(o.course.course_id)
        left_out.append({"course": o.course.title_en, "centre": o.centre.name_en, "distance_km": o.centre.distance_km,
                         "fit": round(plain_fit(o), 3), "score": round(o.score, 3),
                         "because": gate_reasons(data, p, o, pol, ctx)})
        if len(left_out) >= n_left_out:
            break
    items = []
    for i, o in enumerate(options, 1):
        s = o.summary()
        items.append({"rank": i, "course": s["course"], "kind": KIND_TEXT.get(s["kind"], s["kind"]),
                      "centre": s["centre"], "distance_km": s["distance_km"], "score": s["score"],
                      "gates": s["gates"], **option(s)})
    strong = sorted(w, key=lambda x: x["m"], reverse=True)
    lines = [f"Checked {len(every)} course × centre pairs in the district; {len(options)} made the list."]
    lines.append(f"Daily travel radius {ctx.radius:g} km; physical capacity {ctx.capacity:.1f} of 5.")
    moved = [f"{x['label']} ×{x['m']}" for x in strong if abs(x["m"] - 1) > 0.05]
    if moved:
        lines.append("Their own words changed the weights: " + ", ".join(moved) + ".")
    if items:
        lines.append(f"Top: {items[0]['sentence']}")
    if left_out:
        lines.append(f"Left out: {left_out[0]['course']} ({'; '.join(left_out[0]['because'])}).")
    return {"lines": lines, "weights": w, "radius_km": ctx.radius, "capacity": round(ctx.capacity, 2),
            "options": items, "left_out": left_out, "policy": pol.version}


# ---- the person page --------------------------------------------------------------------------------
def person(data: Data, p: Profile, options: list[dict], pol: Policy) -> dict:
    """A short plain-language summary for the person page, plus a fresh look at what was left out."""
    lines = []
    d = data.districts.get(p.district or "")
    who = [p.name or "No name"]
    if p.age:
        who.append(f"{p.age}")
    if p.gender:
        who.append(GENDER_TEXT.get(p.gender, p.gender))
    if p.education:
        who.append(f"studied {EDU_TEXT.get(p.education, p.education)}")
    if d:
        who.append(f"{d.name_en} district")
    lines.append(", ".join(who) + ".")
    work = _occ(data, p.occupation_codes)
    if work:
        lines.append(f"Works as {work}" + (f" for {p.years} years" if p.years else "") + ".")
    want = _occ(data, p.aspiration_codes) or (data.sectors[p.aspiration_sector].title_en
                                              if p.aspiration_sector in data.sectors else "")
    if want:
        lines.append(f"Wants to do {want}.")
    travel = f"Can travel up to {p.radius_km} km a day" if p.radius_km else "Daily travel not given"
    if p.cannot_leave_home:
        travel += "; cannot leave home"
    elif p.hostel_ok:
        travel += "; a hostel is fine"
    lines.append(travel + ".")
    if p.health != "none":
        lines.append(f"Has {HEALTH_TEXT[p.health]}, so heavy work is held back.")
    if p.rejected_sectors or p.rejected_kinds:
        names = [data.sectors[s].title_en if s in data.sectors else s for s in p.rejected_sectors] + \
                [KIND_TEXT.get(k, k) for k in p.rejected_kinds]
        lines.append("Said no to: " + ", ".join(names) + ".")
    for x in weights(p, pol):
        if abs(x["m"] - 1) > 0.25:
            quotes = [e.get("quote", "") for e in p.evidence if e.get("factor") == x["factor"] and e.get("quote")]
            q = f" (“{quotes[0]}”)" if quotes and not quotes[0].startswith(("key ", "simulated")) else ""
            verb = "Cares a lot about" if x["m"] > 1 else "Cares less about"
            lines.append(f"{verb} {FACTOR_TEXT[x['factor']]}{q}: weight ×{x['m']}.")
    chosen = next((o for o in options if o.get("chosen")), None)
    if options:
        lines.append(f"Top option: {option(options[0])['sentence']}")
    if chosen:
        lines.append(f"They chose option {chosen['rank']}: {chosen['course']}.")
    elif options:
        lines.append("They did not pick an option yet: follow up with them.")
    fresh = ranking(data, p, pol, rank(data, p, 5, policy=pol), n_left_out=4) if p.district else None
    return {"lines": lines, "left_out": fresh["left_out"] if fresh else [],
            "weights": fresh["weights"] if fresh else weights(p, pol), "policy": pol.version}
