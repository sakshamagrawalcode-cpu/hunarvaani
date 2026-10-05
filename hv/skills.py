"""Skills worth learning: small or moderate skill gaps that open better-paid or higher-level work.

For every course the person can actually take (it passes the gates), code works out which of its
skills the person does not have yet. A course is worth suggesting as a "skill tip" when:
  * the gap is small (same trade, a step up) or moderate (a neighbouring trade), not a new career;
  * learning is short (at most MAX_WEEKS of training);
  * it pays more than their current work, or is a higher NSQF level in their own trade.
Value = pay gain + level gain + closeness, minus learning time. All numbers come from the dataset.
"""

import re

from .data import Data
from .policy import Policy
from .profile import Profile
from .ranker import gate_value, rank

MAX_WEEKS = 12
STOP = {"and", "the", "for", "with", "work", "basic", "of", "to", "in", "on", "skills", "making"}


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", text.lower()) if len(w) >= 4 and w not in STOP}


def held_skills(data: Data, p: Profile) -> set[str]:
    have = {s.lower() for s in p.skills}
    for c in p.occupation_codes + ([p.family_code] if p.family_code and p.continue_family else []):
        if c in data.occupations:
            have |= {s.lower() for s in data.occupations[c].skills}
    return have


def gap_for(skills: tuple[str, ...], have: set[str]) -> list[str]:
    """Course skills the person does not have yet. A skill counts as held when all its key words appear
    in skills they already have ('machine stitching' does not cover 'industrial sewing machine')."""
    held_words = set().union(*(_words(h) for h in have)) if have else set()
    out = []
    for s in skills:
        w = _words(s)
        if s.lower() in have or (w and w <= held_words):
            continue
        out.append(s)
    return out


def skill_advice(data: Data, p: Profile, pol: Policy | None = None, limit: int = 3) -> list[dict]:
    if not p.district:
        return []
    have = held_skills(data, p)
    mine = set(p.occupation_codes)
    near = {n for c in mine if c in data.occupations for n in data.occupations[c].near}
    cur_sectors = [data.occupations[c].sector for c in p.occupation_codes if c in data.occupations]
    cur_sector = cur_sectors[0] if cur_sectors else None
    cur = data.sectors.get(cur_sector) if cur_sector else None
    pay_now = cur.wage_max if cur else 0
    out: dict[str, dict] = {}
    for o in rank(data, p, keep_dropped=True, policy=pol):
        c = o.course
        if c.course_id in out or c.kind == "certificate":
            continue
        if gate_value(o.gates) < 0.5:
            continue
        codes = set(c.nco_codes)
        sector = data.course_sector(c)
        if codes & mine:
            gap_size = "small"
        elif codes & near or (cur_sector and sector == cur_sector):
            gap_size = "moderate"
        else:
            continue  # a whole new trade is not a "small skill to learn"
        gap = gap_for(c.skills, have)[:3]
        weeks = max(1, round(c.hours / 40))
        if not gap or weeks > MAX_WEEKS:
            continue
        s = data.sectors.get(sector)
        pay_after = s.wage_max if s else 0
        pay_gain = pay_after - pay_now if pay_now else 0
        level_gain = max(0, c.nsqf_level - 3) if gap_size == "small" else 0
        if pay_gain <= 0 and level_gain <= 0:
            continue
        value = pay_gain / 1000 + level_gain + (1.0 if gap_size == "small" else 0.5) - weeks / 8
        out[c.course_id] = {
            "skills": gap, "course_id": c.course_id, "course": c.title_en, "sector": sector,
            "sector_name": s.title_en if s else sector, "gap": gap_size, "weeks": weeks, "hours": c.hours,
            "nsqf_level": c.nsqf_level, "pay_now": [cur.wage_min, cur.wage_max] if cur else None,
            "pay_after": [s.wage_min, s.wage_max] if s else None, "pay_gain": pay_gain,
            "centre": o.centre.name_en, "distance_km": o.centre.distance_km, "value": round(value, 2),
        }
    return sorted(out.values(), key=lambda x: x["value"], reverse=True)[:limit]
