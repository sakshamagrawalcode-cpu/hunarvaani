"""The guided conversation: which question to ask next, and what each answer means.

After the first spoken answer (the person's story) the system already has a shortlist of options.
Every later question is chosen because its answer could change that shortlist:

  value(question) = how much the top options would change across the question's possible answers
                    (1 - overlap of the top-3 lists, averaged and maximum, simulated with the ranker)
                  + a bonus if the LLM, having read everything the person said, suggests this question

Questions whose answer would not change anything are not asked. Required details (age, gender,
studies, travel) are always asked, for eligibility and for the officer's record, but in the order
that matters most for this person. Follow-up questions alternate with them, so the call feels like a
conversation that keeps building on what the person said, and it narrows towards the best work
("from what you told us, tailoring could suit you: does that sound right?") instead of deciding at
the very end. Every number used here is in the policy file (policy.questions).
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from .data import Data
from .profile import Profile
from .ranker import rank
from .understand import (has, numbers, parse_age, parse_choice, parse_duration_weeks, parse_education,
                         parse_gender, parse_health, parse_name, parse_travel, parse_yes_no)

EDU_KEYS = {"1": "none", "2": "upto_5th", "3": "upto_8th", "4": "10th", "5": "12th", "6": "graduate"}
TRAVEL_KEYS = {"1": (5, False), "2": (15, False), "3": (30, False), "4": (30, True)}
HEALTH_KEYS = {"1": "none", "2": "some", "3": "severe"}
LEAN_KEYS = {"1": "job", "2": "own_work", "3": "either"}
GENDER_KEYS = {"1": "female", "2": "male", "3": "other"}
WEEKS_KEYS = {"1": 4, "2": 13, "3": 26}

JOB_WORDS = ["नौकरी", "job", "नोकरी", "सैलरी", "तनख्वाह", "तनख़्वाह", "पगार", "salary", "कंपनी", "company"]
OWN_WORDS = ["अपना काम", "खुद का", "ख़ुद का", "व्यवसाय", "business", "स्वतःचं", "स्वतःचा", "धंधा", "own work",
             "self employed", "खुद", "स्वतः"]
EITHER_WORDS = ["दोनों", "कोई भी", "both", "either", "दोन्ही", "काहीही", "anything"]


def evidence(p: Profile, factor: str, strength: str, quote: str, source: str = "question", intensity: float = 0.6):
    p.evidence.append({"field": f"emphasis.{factor}", "factor": factor, "strength": strength,
                       "intensity": intensity, "quote": quote[:120], "source": source})


@dataclass
class Question:
    key: str  # prompt key, also the id
    kind: str  # "slot" (one detail), "probe" (a follow-up that guides), "open" (free answer for the LLM)
    required: bool = False
    choices: str = ""  # keys / buttons that also answer it ("12" for yes/no)
    labels: str | None = None  # button labels (prompts.LABELS)
    expect: str = ""  # tells the LLM what answer we expect
    keypad: str | None = None  # keypad version of the question (fallback after two unclear answers)
    base: float = 0.0  # fixed value for questions that cannot be simulated (open questions)
    missing: Callable = lambda c: True  # is the detail still unknown?
    applicable: Callable = lambda c: True
    outcomes: Callable = lambda c: []  # possible answers, as changes to a copy of the profile
    from_key: Callable | None = None  # (conversation, key) -> applied?
    from_text: Callable | None = None  # (conversation, text, labels or None) -> applied?
    short_ok: bool = True  # a short answer read by the rules needs no LLM
    short_words: int = 5  # what counts as short; longer answers also go to the LLM (they may say more)


# ---- answer handlers ---------------------------------------------------------------------------
def _name_text(c, text, lab):
    name = (lab.name if lab and lab.name else None) or parse_name(text)
    if name:
        c.profile.name = name[:40]
        return True
    return False


def _age_text(c, text, lab):
    age = (lab.age if lab and lab.age else None) or parse_age(text)
    if age and 14 <= age <= 80:
        c.profile.age = age
        return True
    return False


def _age_key(c, k):  # the kiosk/keypad fallback sends two digits as text, handled in _age_text
    return False


def _gender_text(c, text, lab):
    g = (lab.gender if lab and lab.gender else None) or parse_gender(text)
    if g:
        c.profile.gender = g
        return True
    return False


def _gender_key(c, k):
    c.profile.gender = GENDER_KEYS[k]
    return True


def _edu_text(c, text, lab):
    e = (lab.education if lab and lab.education else None) or parse_education(text)
    if e:
        c.profile.education = e
        return True
    return False


def _edu_key(c, k):
    c.profile.education = EDU_KEYS[k]
    return True


def _travel_text(c, text, lab):
    pr = c.profile
    t = parse_travel(text)
    km = t["km"]
    if lab:
        if lab.max_travel_km:
            km = lab.max_travel_km
        elif lab.max_travel_minutes:
            speed = {"walk": 4, "cycle": 10, "bus": 20, "own_vehicle": 25}.get(lab.travel_mode or "bus", 20)
            km = max(1, round(lab.max_travel_minutes / 60 * speed))
        if lab.hostel_ok is not None:
            t["hostel_ok"] = lab.hostel_ok
        if lab.cannot_leave_home:
            t["cannot_leave_home"] = True
    if km is None and t["hostel_ok"] is None:
        return False
    pr.radius_km = int(min(200, km)) if km else (30 if t["hostel_ok"] else 10)
    if t["cannot_leave_home"]:
        pr.cannot_leave_home = True
    pr.hostel_ok = False if pr.cannot_leave_home else t["hostel_ok"] if t["hostel_ok"] is not None else False
    return True


def _travel_key(c, k):
    km, hostel = TRAVEL_KEYS[k]
    c.profile.radius_km = km
    c.profile.hostel_ok = False if c.profile.cannot_leave_home else hostel
    return True


def _health_text(c, text, lab):
    h = (lab.health if lab and lab.health else None) or parse_health(text)
    if h:
        c.profile.health = h
        c.health_asked = True
        return True
    return False


def _health_key(c, k):
    c.profile.health = HEALTH_KEYS[k]
    c.health_asked = True
    return True


def _lean_text(c, text, lab):
    choice = parse_choice(text, JOB_WORDS, OWN_WORDS, EITHER_WORDS)
    lean = (lab.lean if lab and lab.lean else None) or (LEAN_KEYS[str(choice)] if choice else None)
    if lean:
        c.profile.lean = lean
        return True
    return False


def _lean_key(c, k):
    c.profile.lean = LEAN_KEYS[k]
    return True


def _years_text(c, text, lab):
    years = lab.years if lab and lab.years is not None else None
    if years is None:
        nums = [v for v, _ in numbers(text) if 0 <= v <= 60]
        years = nums[0] if nums else None
    if years is not None:
        c.profile.years = years
        return True
    return False


def _choice(c, text, lab, first, second) -> int | None:
    if lab and lab.choice in (1, 2):
        return lab.choice
    return parse_choice(text, first, second)


GOAL_SAME = ["इसी", "अभी के", "यही काम", "same", "current", "याच", "सध्याच्या", "आगे बढ़", "आगे बढ", "पुढे", "grow"]
GOAL_NEW = ["नया", "नई", "new", "नवीन", "दूसरा", "दुसरं", "दुसरे", "कुछ और", "something else", "different"]


def _goal(c, n, quote):
    if n == 1:
        evidence(c.profile, "skill", "prefers", quote)
    else:
        evidence(c.profile, "aspiration", "prefers", quote)
        evidence(c.profile, "skill", "doesnt_care", quote)
    return True


def _goal_text(c, text, lab):
    n = _choice(c, text, lab, GOAL_SAME, GOAL_NEW)
    return _goal(c, n, text) if n else False


def _goal_key(c, k):
    return _goal(c, int(k), f"key {k}")


def _lead(c, yes: bool, quote: str):
    sector = c.lead_sector
    if not sector:
        return False
    pr = c.profile
    if yes:
        if sector not in pr.confirmed_sectors:
            pr.confirmed_sectors.append(sector)
        if not pr.aspiration_codes and not pr.aspiration_sector:
            pr.aspiration_sector = sector
        evidence(pr, "aspiration", "prefers", quote)
    elif sector not in pr.rejected_sectors:
        pr.rejected_sectors.append(sector)
        if pr.aspiration_sector == sector:
            pr.aspiration_sector = None
    return True


def _lead_text(c, text, lab):
    yes = lab.yes_no if lab and lab.yes_no is not None else parse_yes_no(text)
    return _lead(c, yes, text) if yes is not None else False


def _lead_key(c, k):
    return _lead(c, k == "1", f"key {k}")


HOME_WORDS = ["घर से", "घर पर", "घर में", "from home", "at home", "घरून", "घरी", "घरातून"]
OUT_WORDS = ["बाहर", "दुकान", "कंपनी", "फैक्ट्री", "फ़ैक्टरी", "outside", "factory", "shop", "office", "बाहेर", "कारखान"]


def _home(c, n, quote):
    pr = c.profile
    if n == 1:
        if pr.lean in (None, "either"):
            pr.lean = "own_work"
        evidence(pr, "access", "prefers", quote)
    else:
        if pr.lean is None:
            pr.lean = "job"
    return True


def _home_text(c, text, lab):
    n = _choice(c, text, lab, HOME_WORDS, OUT_WORDS)
    return _home(c, n, text) if n else False


def _home_key(c, k):
    return _home(c, int(k), f"key {k}")


def _weeks(c, weeks: int, quote: str):
    if weeks == 0:  # any length
        c.profile.max_weeks = None
        evidence(c.profile, "completion", "doesnt_care", quote)
    else:
        c.profile.max_weeks = max(1, min(104, weeks))
        if weeks <= 6:
            evidence(c.profile, "completion", "prefers", quote)
    c.duration_asked = True
    return True


def _weeks_text(c, text, lab):
    w = lab.training_weeks if lab and lab.training_weeks is not None else parse_duration_weeks(text)
    return _weeks(c, w, text) if w is not None else False


def _weeks_key(c, k):
    return _weeks(c, WEEKS_KEYS[k], f"key {k}")


SOON_WORDS = ["जल्दी", "तुरंत", "soon", "quick", "quickly", "लवकर", "जल्द", "अभी से", "fast"]
LEARN_WORDS = ["सीख", "अच्छे से", "learn", "शिकून", "शिकणं", "नीट", "आराम से", "पहले सीख"]


def _soon(c, n, quote):
    if n == 1:
        evidence(c.profile, "completion", "insists", quote)
        evidence(c.profile, "income", "prefers", quote)
    else:
        evidence(c.profile, "completion", "doesnt_care", quote)
    return True


def _soon_text(c, text, lab):
    n = _choice(c, text, lab, SOON_WORDS, LEARN_WORDS)
    return _soon(c, n, text) if n else False


def _soon_key(c, k):
    return _soon(c, int(k), f"key {k}")


def _yes_no_kind(kind: str, factor_if_yes: str):
    def apply(c, yes: bool, quote: str):
        pr = c.profile
        if yes:
            evidence(pr, factor_if_yes, "prefers", quote)
            if kind == "startup" and pr.lean in (None, "either"):
                pr.lean = "own_work"
            if kind in pr.rejected_kinds:
                pr.rejected_kinds.remove(kind)
        elif kind not in pr.rejected_kinds:
            pr.rejected_kinds.append(kind)
        return True

    def from_text(c, text, lab):
        yes = lab.yes_no if lab and lab.yes_no is not None else parse_yes_no(text)
        return apply(c, yes, text) if yes is not None else False

    def from_key(c, k):
        return apply(c, k == "1", f"key {k}")

    return from_text, from_key


_cert_text, _cert_key = _yes_no_kind("certificate", "skill")
_biz_text, _biz_key = _yes_no_kind("startup", "income")


# ---- simulated answers (for the value of a question) ------------------------------------------
def _set(**kw):
    def f(p: Profile):
        for k, v in kw.items():
            setattr(p, k, v)
    return f


def _ev(*items, **kw):
    def f(p: Profile):
        for factor, strength in items:
            evidence(p, factor, strength, "simulated")
        for k, v in kw.items():
            setattr(p, k, v)
    return f


def _append(attr: str, value):
    def f(p: Profile):
        getattr(p, attr).append(value)
    return f


def _lead_yes_sim(c):
    def f(p: Profile):
        if not p.aspiration_codes and not p.aspiration_sector:
            p.aspiration_sector = c.lead_sector
        evidence(p, "aspiration", "prefers", "simulated")
    return f


def _held_rpl(c) -> bool:
    held = set(c.profile.occupation_codes)
    return any(co.kind == "certificate" and set(co.nco_codes) & held for co in c.data.courses)


def _has_startup(c) -> bool:
    return any(co.kind == "startup" and c.data.centres_for(co, c.profile.district or "") for co in c.data.courses)


# ---- the bank ------------------------------------------------------------------------------------
BANK: dict[str, Question] = {q.key: q for q in [
    Question("ask_name", "slot", required=True, expect="the person's name",
             missing=lambda c: not c.profile.name, from_text=_name_text),
    Question("say_age", "slot", required=True, expect="age in years (a number)", keypad="ask_age",
             missing=lambda c: c.profile.age is None, from_text=_age_text,
             outcomes=lambda c: [_set(age=a) for a in (22, 40, 55)]),
    Question("say_gender", "slot", required=True, choices="123", labels="say_gender",
             expect="woman, man, or prefers not to say", keypad="ask_gender",
             missing=lambda c: c.profile.gender is None, from_text=_gender_text, from_key=_gender_key,
             outcomes=lambda c: [_set(gender="female"), _set(gender="male")]),
    Question("say_education", "slot", required=True, choices="123456", labels="say_education",
             expect="how far they studied (none / up to class 5 / up to 8 / 10th / 12th / graduate)",
             keypad="ask_education", missing=lambda c: c.profile.education is None,
             from_text=_edu_text, from_key=_edu_key,
             outcomes=lambda c: [_set(education=e) for e in ("none", "upto_8th", "10th", "graduate")]),
    Question("say_travel", "slot", required=True, choices="1234", labels="say_travel",
             expect="how far they can travel each day (km or minutes) and whether a hostel is possible",
             keypad="ask_travel", missing=lambda c: c.profile.radius_km is None,
             from_text=_travel_text, from_key=_travel_key,
             outcomes=lambda c: [_set(radius_km=5, hostel_ok=False), _set(radius_km=15, hostel_ok=False),
                                 _set(radius_km=30, hostel_ok=not c.profile.cannot_leave_home)]),
    Question("say_health", "slot", choices="123", labels="say_health",
             expect="any physical limits for heavy work or standing (none / a little / a lot)", keypad="ask_health",
             missing=lambda c: not c.health_asked and c.profile.health == "none",
             from_text=_health_text, from_key=_health_key,
             outcomes=lambda c: [_set(health="none"), _set(health="some"), _set(health="severe")]),
    Question("say_lean", "slot", choices="123", labels="say_lean",
             expect="salaried job, own work, or either", keypad="ask_lean",
             missing=lambda c: c.profile.lean is None, from_text=_lean_text, from_key=_lean_key,
             outcomes=lambda c: [_set(lean="job"), _set(lean="own_work"), _set(lean="either")]),
    Question("ask_aspiration", "open", base=0.35, expect="the work they would like to learn or do", short_ok=False,
             missing=lambda c: not (c.profile.aspiration_codes or c.profile.aspiration_sector)
             and c.profile.emphasis.get("aspiration") != "doesnt_care"),
    Question("ask_family", "open", base=0.12, expect="the work their family does (optional)", short_ok=False,
             missing=lambda c: c.profile.family_code is None and c.mood() != "upset"),
    Question("q_goal", "probe", choices="12", labels="q_goal", short_words=4,
             expect="choice 1 = grow in their current work, 2 = learn something new",
             applicable=lambda c: bool(c.profile.occupation_codes), from_text=_goal_text, from_key=_goal_key,
             outcomes=lambda c: [_ev(("skill", "prefers")), _ev(("aspiration", "prefers"), ("skill", "doesnt_care"))]),
    Question("q_lead", "probe", choices="12", labels="yes_no",
             expect="yes or no: does the suggested work suit them (if no, any work they name instead)",
             short_words=2, applicable=lambda c: c.lead_ready(), from_text=_lead_text, from_key=_lead_key,
             outcomes=lambda c: [_lead_yes_sim(c), _append("rejected_sectors", c.lead_sector or "")]),
    Question("q_home", "probe", choices="12", labels="q_home",
             expect="choice 1 = work from home, 2 = go out to a shop or company",
             applicable=lambda c: c.profile.lean in (None, "either") and not c.profile.cannot_leave_home,
             from_text=_home_text, from_key=_home_key,
             outcomes=lambda c: [_ev(("access", "prefers"), lean="own_work"), _set(lean="job")]),
    Question("q_duration", "probe", choices="123", labels="q_duration",
             expect="the longest training they can do (training_weeks; 0 = any length)",
             missing=lambda c: not c.duration_asked, from_text=_weeks_text, from_key=_weeks_key,
             outcomes=lambda c: [_set(max_weeks=4), _set(max_weeks=13), _set(max_weeks=None)]),
    Question("q_earn_soon", "probe", choices="12", labels="q_earn_soon",
             expect="choice 1 = must start earning soon, 2 = fine to learn properly first",
             from_text=_soon_text, from_key=_soon_key,
             outcomes=lambda c: [_ev(("completion", "insists"), ("income", "prefers")), _ev(("completion", "doesnt_care"))]),
    Question("q_certificate", "probe", choices="12", labels="yes_no",
             expect="yes or no: wants a government certificate for skills they already have",
             applicable=lambda c: _held_rpl(c) and "certificate" not in c.profile.rejected_kinds,
             from_text=_cert_text, from_key=_cert_key,
             outcomes=lambda c: [_ev(("skill", "prefers")), _append("rejected_kinds", "certificate")]),
    Question("q_own_business", "probe", choices="12", labels="yes_no",
             expect="yes or no: wants to start their own small business with support or a loan",
             applicable=lambda c: c.profile.lean in (None, "either", "own_work") and _has_startup(c)
             and "startup" not in c.profile.rejected_kinds,
             from_text=_biz_text, from_key=_biz_key,
             outcomes=lambda c: [_ev(("income", "prefers"), lean="own_work"), _append("rejected_kinds", "startup")]),
    Question("q_years", "probe", expect="years of experience in their work (a number)",
             applicable=lambda c: bool(c.profile.occupation_codes),
             missing=lambda c: c.profile.years is None, from_text=_years_text,
             outcomes=lambda c: [_set(years=1), _set(years=6)]),
]}

FOLLOW_UPS = [k for k, q in BANK.items() if q.kind in ("probe", "open")] + ["say_health", "say_lean"]


# ---- value of asking -------------------------------------------------------------------------------
def top_ids(data: Data, p: Profile, n: int, policy) -> list[str]:
    return [o.course.course_id for o in rank(data, p, n, policy=policy)]


def _jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if sa | sb else 1.0


def value(c, q: Question, now: list[str]) -> float:
    """How much the answer to q could change the top options (0 = not at all, 1 = completely)."""
    outs = q.outcomes(c)
    if not outs:
        return q.base
    pol = c.policy()
    n = pol.questions["top_n"]
    changes = []
    for change in outs:
        p = Profile.from_dict(c.profile.to_dict())
        change(p)
        changes.append(1 - _jaccard(top_ids(c.data, p, n, pol), now))
    return 0.5 * sum(changes) / len(changes) + 0.5 * max(changes)


@dataclass
class Plan:
    """What the engine asks next, with the reason (logged, and shown to officers)."""
    question: Question
    score: float
    why: str
    scores: dict = field(default_factory=dict)
