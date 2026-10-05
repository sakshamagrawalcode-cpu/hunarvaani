"""Gated personal ranker: Score = G x sum(w * m * f) / sum(w * m).

G  gates (0..1, multiplied): work capacity, distance, eligibility, plus the person's own "no" to a
   kind of work and the longest training they can give. Any gate near 0 drops the option.
w  base weight per factor, from the active policy (officers set it, by district if needed)
m  the person's emphasis on that factor: a running score from evidence (hv/emphasis.py)
f  fit 0..1 on six factors: aspiration, skill, demand, access, completion, income
Every constant (weights, gate steepness, age bands, radius rule) lives in the policy (hv/policy.py).

Every number that reaches the caller comes from the dataset; the LLM never ranks.
"""

from dataclasses import dataclass, field

from .data import EDUCATION_ORDER, Centre, Course, Data
from .emphasis import multiplier
from .policy import FACTORS, POLICIES, Policy
from .profile import Profile


@dataclass
class Option:
    course: Course
    centre: Centre
    score: float
    raw: float  # score before gates (what a plain weighted sum would give)
    gates: dict[str, float]
    factors: dict[str, float]
    reasons: list[str]  # factor keys, e.g. ["aspiration", "access"]
    skill_gap: list[str]
    dropped_by: list[str] = field(default_factory=list)
    weights: dict[str, float] = field(default_factory=dict)  # w * m used for this person
    policy: str = ""
    multipliers: dict[str, float] = field(default_factory=dict)
    over_load: float = 0.0  # physical load above the person's capacity (for learning the gate)
    excess_ratio: float = 0.0  # distance beyond the radius, in radii (for learning the gate)

    def summary(self) -> dict:
        return {"course_id": self.course.course_id, "course": self.course.title_en, "kind": self.course.kind,
                "centre_id": self.centre.centre_id, "centre": self.centre.name_en,
                "distance_km": self.centre.distance_km, "hours": self.course.hours, "fee_inr": self.course.fee_inr,
                "scheme": self.course.scheme, "score": round(self.score, 3), "raw": round(self.raw, 3),
                "gates": {k: round(v, 3) for k, v in self.gates.items()},
                "factors": {k: round(v, 3) for k, v in self.factors.items()},
                "reasons": [REASON[r] for r in self.reasons], "reason_keys": self.reasons,
                "skill_gap": self.skill_gap, "dropped_by": self.dropped_by,
                "weights": {k: round(v, 3) for k, v in self.weights.items()}, "policy": self.policy,
                "multipliers": self.multipliers, "over_load": round(self.over_load, 3),
                "excess_ratio": round(self.excess_ratio, 3)}


def _edu_ok(have: str | None, need: str) -> bool:
    if not have:
        return True  # unknown: do not block, an officer checks documents at enrolment
    try:
        return EDUCATION_ORDER.index(have) >= EDUCATION_ORDER.index(need)
    except ValueError:
        return True


def radius(p: Profile, pol: Policy) -> float:
    """Daily travel radius: a keypad answer wins; otherwise it shrinks as access emphasis grows."""
    if p.radius_km:
        return float(p.radius_km)
    g = pol.gates
    m = multiplier(p, "access", pol)
    r = g["default_radius_km"] / (m ** g["radius_exponent"])
    if p.cannot_leave_home:
        r = min(r, g["default_radius_km"] * 0.6)
    return max(g["min_radius_km"], round(r, 1))


class Ctx:
    """Everything about the person that does not depend on the course, computed once per ranking
    (the guided conversation ranks dozens of "what if" profiles per question, so this matters)."""

    def __init__(self, data: Data, p: Profile, pol: Policy):
        self.radius = radius(p, pol)
        self.capacity = pol.capacity(p.age, p.health)
        self.mult = {k: multiplier(p, k, pol) for k in FACTORS}
        w = {k: pol.weights[k] * self.mult[k] for k in FACTORS}
        total = sum(w.values())
        self.weights = {k: v / total for k, v in w.items()}
        self.top_wage = max(data.wage_max(s) for s in data.sectors) or 1
        self.mine = set(p.occupation_codes)
        self.near_mine = {n for c in self.mine if c in data.occupations for n in data.occupations[c].near}
        self.asp = set(p.aspiration_codes)
        self.near_asp = {n for c in self.asp if c in data.occupations for n in data.occupations[c].near}
        self.named = self.mine | self.asp
        self.near_named = self.near_mine | self.near_asp
        wanted = {data.occupations[c].sector for c in self.named if c in data.occupations}
        if p.aspiration_sector:
            wanted.add(p.aspiration_sector)
        self.wanted_sectors = wanted | set(p.confirmed_sectors)
        self.held = self.mine | ({p.family_code} if p.family_code and p.continue_family else set())
        have = {s.lower() for s in p.skills}
        for c in p.occupation_codes:
            if c in data.occupations:
                have |= {s.lower() for s in data.occupations[c].skills}
        self.have = have


def load(data: Data, course: Course, pol: Policy) -> int:
    level = pol.sector_load.get(data.course_sector(course), 3)
    return max(level, 4) if course.heavy_work else level


def gates(data: Data, p: Profile, course: Course, centre: Centre, pol: Policy,
          ctx: Ctx | None = None) -> dict[str, float]:
    ctx = ctx or Ctx(data, p, pol)
    g = pol.gates
    over = max(0.0, load(data, course, pol) - ctx.capacity)
    work = g["work_base"] ** over
    r = ctx.radius
    d = centre.distance_km
    distance = 1.0 if d <= r else 0.5 ** ((d - r) / (r * g["distance_halflife"]))
    residential = d > g["residential_km"]
    if residential and (p.cannot_leave_home or p.hostel_ok is False):
        distance = 0.0
    age = p.age or 30
    eligible = course.min_age <= age <= course.max_age and _edu_ok(p.education, course.min_education)
    restricted = set(course.nco_codes) & pol.consent_only
    if restricted and not restricted & (set(p.occupation_codes) | set(p.aspiration_codes)):
        eligible = False  # never suggested unless the person brings it up themselves
    if course.kind == "certificate":  # RPL certifies a skill the person already has
        eligible = eligible and bool(set(course.nco_codes) & ctx.held)
    # what the person said no to in the follow-up questions ("not this work", "no loan", ...)
    sector = data.course_sector(course)
    preference = g.get("rejected_factor", 0.1) if (sector in p.rejected_sectors or course.kind in p.rejected_kinds) else 1.0
    # the longest training they can give: longer courses fade out smoothly
    weeks = max(1, round(course.hours / 40))
    duration = 1.0
    if p.max_weeks and weeks > p.max_weeks:
        duration = 0.5 ** ((weeks - p.max_weeks) / max(1, p.max_weeks))
    # personalised: once the person has named the work they do or want, a course unrelated to both
    # keeps only part of its score, so related options come first (it can still fill a gap)
    codes = set(course.nco_codes)
    related = (bool(codes & (ctx.named | ctx.near_named)) or sector in ctx.wanted_sectors
               or (not codes and course.kind == "startup"))
    relevance = 1.0 if (not ctx.named and not p.aspiration_sector) or related else g.get("unrelated_factor", 0.5)
    return {"work_capacity": work, "distance": distance, "eligibility": 1.0 if eligible else 0.0,
            "preference": preference, "duration": round(duration, 4), "relevance": relevance}


def gate_value(g: dict[str, float]) -> float:
    out = 1.0
    for v in g.values():
        out *= v
    return out


def factors(data: Data, p: Profile, course: Course, centre: Centre, pol: Policy,
            ctx: Ctx | None = None) -> dict[str, float]:
    ctx = ctx or Ctx(data, p, pol)
    sector = data.course_sector(course)
    mine, near = ctx.mine, ctx.near_mine
    codes = set(course.nco_codes)

    # aspiration: what they want to do
    if p.aspiration_codes or p.aspiration_sector:
        if codes & ctx.asp or sector == p.aspiration_sector:
            asp = 1.0
        elif codes & ctx.near_asp:
            asp = 0.6
        else:
            asp = 0.2
    else:
        asp = 0.8 if codes & mine else 0.5

    # skill: what they already do
    if codes & mine:
        if course.kind == "certificate":
            skill = 1.0 if (p.years or 0) >= 2 else 0.6
        else:
            skill = 0.9
    elif codes & near:
        skill = 0.6
    elif not codes:  # "any trade" courses such as starting your own work
        skill = 0.5 if mine else 0.3
    else:
        skill = 0.2

    demand = {"high": 1.0, "low": 0.3}.get(data.demand.get((centre.district, sector), "medium"), 0.6)

    access = max(0.0, 1 - centre.distance_km / (2 * ctx.radius))
    if p.gender == "female" and centre.women_batches:
        access = min(1.0, access + 0.15)

    completion = max(0.1, 1 - course.hours / 600)
    if course.fee_inr == 0:
        completion = min(1.0, completion + 0.1)

    income = data.wage_max(sector) / ctx.top_wage
    if p.lean == "job" and course.placement:
        income = min(1.0, income + 0.2)
    if p.lean == "own_work" and course.kind == "startup":
        income = min(1.0, income + 0.3)
    if p.lean == "job" and course.kind == "startup":
        income *= 0.6

    return {"aspiration": asp, "skill": skill, "demand": demand, "access": access,
            "completion": completion, "income": income}


REASON = {
    "aspiration": "matches what you want to do",
    "skill": "builds on the work you already do",
    "demand": "this work is in demand in your district",
    "access": "close to home",
    "completion": "short and free, easy to finish",
    "income": "better pay",
}


def personal_weights(p: Profile, pol: Policy) -> dict[str, float]:
    """w * m for each factor, normalised to sum to 1."""
    w = {k: pol.weights[k] * multiplier(p, k, pol) for k in FACTORS}
    total = sum(w.values())
    return {k: v / total for k, v in w.items()}


def score_one(data: Data, p: Profile, course: Course, centre: Centre, pol: Policy,
              w: dict[str, float] | None = None, ctx: Ctx | None = None) -> Option:
    ctx = ctx or Ctx(data, p, pol)
    g = gates(data, p, course, centre, pol, ctx)
    f = factors(data, p, course, centre, pol, ctx)
    w = w or ctx.weights
    raw = sum(w[k] * f[k] for k in FACTORS)
    plain = sum(pol.weights[k] * f[k] for k in FACTORS) / sum(pol.weights.values())
    gate = gate_value(g)
    contrib = sorted(FACTORS, key=lambda k: w[k] * f[k], reverse=True)
    reasons = [k for k in contrib if f[k] >= 0.6][:2]
    gap = [s for s in course.skills if s.lower() not in ctx.have][:3]
    dropped = [k for k, v in g.items() if v < 0.5]
    r = ctx.radius
    return Option(course, centre, gate * raw, plain, g, f, reasons, gap, dropped, w, pol.version,
                  {k: round(v, 3) for k, v in ctx.mult.items()},
                  max(0.0, load(data, course, pol) - ctx.capacity),
                  max(0.0, (centre.distance_km - r) / r))


def rank(data: Data, p: Profile, limit: int = 5, keep_dropped: bool = False,
         policy: Policy | None = None) -> list[Option]:
    """Top options, at most one per course and at most two of the same kind, so the list mixes
    training, a certificate for skills already held (RPL) and own-work routes."""
    if not p.district:
        return []
    pol = (policy or POLICIES.active()).for_district(p.district)
    ctx = Ctx(data, p, pol)
    every: list[Option] = []
    for course in data.courses:
        for centre in data.centres_for(course, p.district):
            every.append(score_one(data, p, course, centre, pol, ctx.weights, ctx))
    every.sort(key=lambda o: o.score, reverse=True)
    if keep_dropped:
        return every
    picked: list[Option] = []
    seen: set[str] = set()
    kinds: dict[str, int] = {}
    for o in every:
        if o.score < pol.gates["drop_below"] or o.course.course_id in seen or kinds.get(o.course.kind, 0) >= 2:
            continue
        picked.append(o)
        seen.add(o.course.course_id)
        kinds[o.course.kind] = kinds.get(o.course.kind, 0) + 1
        if len(picked) >= limit:
            break
    return picked


def tradeoff(options: list[Option], pol: Policy) -> tuple[str, str] | None:
    """If the top two options are close and pull in opposite directions (A wins on one factor, B on
    another), return (factor A wins on, factor B wins on): worth asking the person which matters more."""
    t = pol.tradeoff
    if not t["enabled"] or len(options) < 2:
        return None
    a, b = options[0], options[1]
    if a.score - b.score > t["max_score_gap"]:
        return None
    pull = {k: a.weights.get(k, 0) * (a.factors[k] - b.factors[k]) for k in FACTORS}
    fa, fb = max(pull, key=pull.get), min(pull, key=pull.get)
    if pull[fa] >= t["min_pull"] and -pull[fb] >= t["min_pull"]:
        return fa, fb
    return None
