"""Training and livelihood options for a caller, from the sample dataset (step A9).

Rules first, weights in one place, no model: every option can be explained line by line.

1. Candidates for the caller's occupation: upskilling in the same trade, a certificate for the
   skills they already have (RPL), upskilling in a near trade, and for callers who want their
   own work: starting-a-business training plus the loan scheme that fits their trade.
2. Filters: age inside the course's range, education at or above the minimum, no heavy-work
   course for a caller with a physical difficulty, no business course for a caller who wants a
   job, and a centre that teaches the course within the caller's daily travel (or with a hostel
   when they said they can stay in one).
3. Score = WEIGHTS: occupation fit, local demand in their district, reach (closer is better),
   wish (job -> placement-linked, own work -> business), NSQF step-up; women-only batches add a
   little for women. Ties: free first, then shorter.
4. Skill gap = what the course teaches minus what people in their occupation usually know.
5. When fewer than TOP_N options are within reach, the nearest farther ones fill in, marked
   `farther` so nobody is told something is close when it is not.

Adapted from the team's SkillCall engine (github.com/sakshamagrawalcode-cpu/SIH,
backend/app/engine.py): course types, business support only for own work, and only facts found
in the dataset are ever spoken.
"""

from dataclasses import dataclass, field, replace

from core import sample_data
from core.sample_data import AGE_RANGE, EDUCATION_ORDER, TRAVEL_KM, Centre, Course, Dataset

WEIGHTS = {"fit": 0.35, "demand": 0.20, "reach": 0.20, "wish": 0.15, "step": 0.10}
WOMEN_BONUS = 0.03
TOP_N = 3
DEFAULT_TRAVEL_KM = 30  # when the travel answer is missing
DEMAND_SCORE = {"high": 1.0, "medium": 0.6, "low": 0.3}
UNKNOWN = {"", "skipped", "unknown", "not_said", "none_of_these"}


@dataclass(frozen=True)
class Profile:
    """What the call found out, as the interview stores it (answer values)."""

    occupation: str | None = None  # NCO code
    age: str | None = None
    gender: str | None = None
    education: str | None = None
    travel: str | None = None
    physical: str | None = None
    lean: str | None = None  # job | own_work | unsure
    district: str | None = None  # district code from the PIN code

    @classmethod
    def from_answers(cls, answers: dict) -> "Profile":
        def get(key):
            value = answers.get(key)
            return None if value is None or str(value) in UNKNOWN else str(value)

        return cls(
            occupation=get("occupation") or get("trades"),
            age=get("q_age"),
            gender=get("q_gender"),
            education=get("q_education"),
            travel=get("q_travel"),
            physical=get("q_physical"),
            lean=get("q_lean"),
            district=get("q_district"),
        )


@dataclass(frozen=True)
class Option:
    course: Course
    centre: Centre | None
    score: float
    parts: dict[str, float]
    reasons: tuple[tuple[str, dict], ...]
    gap: tuple[str, ...]
    loan_scheme: str | None = None
    farther: bool = False
    fit: str = "same_trade"  # same_trade | near_trade | any_trade
    rank: int = field(default=0, compare=False)


def recommend(profile: Profile, data: Dataset | None = None, top_n: int = TOP_N) -> list[Option]:
    """The best `top_n` options for this caller (fewer, or none, when nothing fits)."""
    data = data or sample_data.load()
    occupation = data.occupations.get(profile.occupation or "")
    if occupation is None:
        return []
    near, far = [], []
    for course in data.courses:
        fit = _fit(course, occupation.nco_code, occupation.near)
        if fit is None or not _eligible(course, profile):
            continue
        close, farther = _centres(course, occupation.sector, profile, data)
        if close:
            near.append(
                max((_option(course, fit, c, profile, data) for c in close), key=_order_key)
            )
        elif farther:
            far.append(_option(course, fit, farther[0], profile, data, farther=True))
        elif profile.district is None:  # no PIN code: the course without a centre yet
            near.append(_option(course, fit, None, profile, data))
    ranked = sorted(near, key=_sort_key)[:top_n]
    ranked += sorted(far, key=_sort_key)[: top_n - len(ranked)]
    return [replace(o, rank=i) for i, o in enumerate(ranked, 1)]


def _sort_key(o: Option):
    return (-o.score, o.course.fee_inr, o.course.hours, o.course.course_id)


def _order_key(o: Option):
    return (o.score, -(o.centre.distance_km if o.centre else 0))


def _fit(course: Course, code: str, near: tuple[str, ...]) -> str | None:
    if code in course.nco_codes:
        return "same_trade"
    if course.kind == "startup" and "*" in course.nco_codes:
        return "any_trade"
    # a certificate is only for your own trade, and trade-specific business help (such as PM
    # Vishwakarma) only for people already in that trade
    if course.kind == "upskill" and set(near) & set(course.nco_codes):
        return "near_trade"
    return None


def _eligible(course: Course, p: Profile) -> bool:
    if p.age in AGE_RANGE:
        youngest, oldest = AGE_RANGE[p.age]
        if oldest < course.min_age or youngest > course.max_age:
            return False
    if p.education in EDUCATION_ORDER and EDUCATION_ORDER.index(
        p.education
    ) < EDUCATION_ORDER.index(course.min_education):
        return False
    if p.physical == "some" and course.heavy_work:
        return False
    return not (p.lean == "job" and course.kind == "startup")


def _limit(p: Profile) -> int:
    return TRAVEL_KM.get(p.travel or "", DEFAULT_TRAVEL_KM)


def _centres(course: Course, sector: str, p: Profile, data: Dataset):
    """(centres within reach, farther centres nearest first) that teach this course."""
    teaching = [c for c in data.centres if course.sector in c.sectors]
    if p.district is None:
        return [], []
    local = [c for c in teaching if c.district_code == p.district]
    close = [c for c in local if c.distance_km <= _limit(p)]
    if p.travel == "hostel":
        state = data.district_state.get(p.district)
        close += [
            c
            for c in teaching
            if c.hostel
            and c.district_code != p.district
            and data.district_state.get(c.district_code) == state
        ]
    farther = sorted((c for c in local if c not in close), key=lambda c: c.distance_km)
    return close, farther


def _option(
    course: Course,
    fit: str,
    centre: Centre | None,
    p: Profile,
    data: Dataset,
    farther: bool = False,
) -> Option:
    occupation = data.occupations[p.occupation or ""]
    sector = (
        occupation.sector
        if course.sector in ("rpl", "vishwakarma", "entrepreneurship")
        else (course.sector)
    )
    level = data.demand_level(p.district, sector)
    parts = {
        "fit": {"same_trade": 1.0, "any_trade": 0.7, "near_trade": 0.6}[fit],
        "demand": DEMAND_SCORE[level],
        "reach": _reach(centre, p, farther),
        "wish": _wish(course, p.lean),
        "step": {"upskill": 1.0 if fit == "same_trade" else 0.8, "certificate": 0.6}.get(
            course.kind, 0.5
        ),
    }
    score = sum(WEIGHTS[k] * v for k, v in parts.items())
    women = p.gender == "female" and centre is not None and centre.women_batches
    if women:
        score += WOMEN_BONUS

    reasons: list[tuple[str, dict]] = []
    if fit == "same_trade":
        reasons.append(("same_trade", {}))
    elif fit == "near_trade":
        near = next(c for c in occupation.near if c in course.nco_codes)
        reasons.append(("near_trade", {"occupation": data.occupations[near].title_en}))
    loan = None
    if course.kind == "certificate":
        reasons.append(("certificate", {}))
    if course.kind == "startup":
        loan = course.scheme if course.scheme == "PM-VISHWAKARMA" else occupation.loan_scheme
        reasons.append(("own_work", {"loan": data.schemes[loan].name_en}))
    elif p.lean in ("own_work", "unsure") and occupation.loan_scheme:
        loan = occupation.loan_scheme
    if course.placement:
        reasons.append(("placement", {}))
    if course.fee_inr == 0:
        reasons.append(("free", {}))
    limit = _limit(p)
    if centre is None:
        reasons.append(("centre_unknown", {}))
    elif farther:
        reasons.append(("farther", {"km": centre.distance_km, "limit": limit}))
    elif centre.district_code != p.district:
        reasons.append(("hostel", {"centre": centre.name_en}))
    else:
        reasons.append(("near_you", {"km": centre.distance_km, "limit": limit}))
    if centre is not None and centre.hostel and p.travel == "hostel":
        reasons.append(("has_hostel", {}))
    if women:
        reasons.append(("women_batch", {}))
    if level == "high":
        reasons.append(("demand", {"sector": data.sectors[sector].title_en}))
    wage = data.sectors[sector]
    reasons.append(("wage", {"min": wage.wage_min, "max": wage.wage_max}))

    known = {s.lower() for s in occupation.typical_skills}
    gap = tuple(s for s in course.skills if s.lower() not in known)
    return Option(
        course=course,
        centre=centre,
        score=round(score, 4),
        parts=parts,
        reasons=tuple(reasons),
        gap=gap,
        loan_scheme=loan,
        farther=farther,
        fit=fit,
    )


def _reach(centre: Centre | None, p: Profile, farther: bool) -> float:
    if centre is None:
        return 0.5
    if farther:
        return 0.1
    if centre.district_code != p.district:  # a hostel elsewhere in the state
        return 0.6
    return 1.0 - 0.5 * min(1.0, centre.distance_km / _limit(p))


def _wish(course: Course, lean: str | None) -> float:
    if lean == "job":
        if course.kind == "certificate":
            return 0.7
        return 1.0 if course.placement else 0.5
    if lean == "own_work":
        if course.kind == "startup":
            return 1.0
        if course.kind == "certificate":
            return 0.7
        return 0.4 if course.placement else 0.8
    return 0.6


REASON_EN = {
    "same_trade": "Same trade as your work",
    "near_trade": "A near trade: {occupation}",
    "certificate": "Government certificate for the skills you already have",
    "own_work": "Helps you start your own work; loan help: {loan}",
    "placement": "Placement support after the course",
    "free": "Free",
    "near_you": "Centre about {km} km away (you can go up to {limit} km)",
    "farther": "Centre about {km} km away: farther than the {limit} km you said",
    "hostel": "Stay in the hostel at {centre}",
    "has_hostel": "Hostel available",
    "centre_unknown": "Centre to be confirmed (no PIN code)",
    "women_batch": "Women-only batches",
    "demand": "Many openings nearby in {sector}",
    "wage": "Typical pay Rs {min}-{max} a month (sample)",
}


def reason_text(code: str, params: dict) -> str:
    return REASON_EN[code].format(**params)


def as_dict(option: Option, data: Dataset | None = None) -> dict:
    """An option as plain JSON for the console and the database."""
    data = data or sample_data.load()
    c, centre = option.course, option.centre
    scheme = data.schemes.get(c.scheme)
    loan = data.schemes.get(option.loan_scheme or "")
    return {
        "rank": option.rank,
        "course_id": c.course_id,
        "kind": c.kind,
        "title": c.title_en,
        "nsqf_level": c.nsqf_level,
        "hours": c.hours,
        "fee_inr": c.fee_inr,
        "placement": c.placement,
        "scheme": scheme.name_en if scheme else c.scheme,
        "loan": loan.name_en if loan else None,
        "centre": centre.name_en if centre else None,
        "centre_id": centre.centre_id if centre else None,
        "distance_km": centre.distance_km if centre else None,
        "hostel": centre.hostel if centre else None,
        "farther": option.farther,
        "fit": option.fit,
        "score": option.score,
        "parts": option.parts,
        "reasons": [reason_text(code, params) for code, params in option.reasons],
        "skill_gap": list(option.gap),
        "sample": True,
    }
