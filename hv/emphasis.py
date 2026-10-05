"""How strongly a person cares about each ranking factor, as a running score instead of a fixed label.

Each piece of evidence adds to a belief for that factor:
  LLM label (insists / prefers / neutral / doesnt_care) x (0.5 + intensity the LLM gave, 0..1)
  + a bonus if the quoted words include an intensifier ("only", "never", "सिर्फ", "फक्त", ...)
  + every repeat mention adds again
  + the trade-off question: the factor the person picks gains, the other loses.
belief -> multiplier m (smooth, bounded by the policy; neutral = 1):
  m = 1 + (max - 1) * tanh(belief / scale)   when belief >= 0
  m = 1 - (1 - min) * tanh(-belief / scale)  when belief < 0
"""

import math
import re

from .policy import FACTORS, Policy

INTENSIFIERS = {
    "hi": ["बिल्कुल", "सिर्फ", "सिर्फ़", "ही", "कभी नहीं", "ज़रूर", "जरूर", "बहुत", "हरगिज़"],
    "mr": ["फक्त", "अजिबात", "नक्की", "कधीच", "खूप", "मुळीच"],
    "en": ["only", "never", "must", "definitely", "really", "absolutely", "at all"],
}
_ALL = [w for words in INTENSIFIERS.values() for w in words]


def has_intensifier(quote: str) -> bool:
    q = f" {quote.lower()} "
    return any(re.search(rf"(^|\s){re.escape(w)}(\s|$)", q) for w in _ALL)


def evidence_for(profile, factor: str) -> list[dict]:
    items = [e for e in profile.evidence if e.get("factor") == factor or e.get("field") == f"emphasis.{factor}"]
    if not items and factor in profile.emphasis:  # a label set directly (older records, tests, officers)
        items = [{"factor": factor, "strength": profile.emphasis[factor], "quote": "", "source": "label"}]
    return items


def belief(profile, factor: str, pol: Policy) -> float:
    e = pol.emphasis
    total = 0.0
    for item in evidence_for(profile, factor):
        logit = e["label_logit"].get(item.get("strength", "neutral"), 0.0)
        intensity = item.get("intensity")
        scale = 0.5 + (intensity if isinstance(intensity, (int, float)) else 0.5)
        total += logit * scale
        if logit > 0 and has_intensifier(item.get("quote", "")):
            total += e["intensifier_bonus"]
    cap = e["max_belief"]
    return max(-cap, min(cap, total))


def multiplier(profile, factor: str, pol: Policy) -> float:
    b, e = belief(profile, factor, pol), pol.emphasis
    if b >= 0:
        return 1 + (e["max"] - 1) * math.tanh(b / e["scale"])
    return 1 - (1 - e["min"]) * math.tanh(-b / e["scale"])


def multipliers(profile, pol: Policy) -> dict[str, float]:
    return {f: round(multiplier(profile, f, pol), 3) for f in FACTORS}


def label_for(m: float) -> str:
    """Readable label for a multiplier (for the screen and the officer console)."""
    return "insists" if m >= 2 else "prefers" if m >= 1.25 else "doesnt_care" if m <= 0.85 else "neutral"


def add_tradeoff(profile, winner: str, loser: str, key: str) -> None:
    profile.evidence.append({"field": f"emphasis.{winner}", "factor": winner, "strength": "tradeoff_win",
                             "quote": f"chose {winner} over {loser} (key {key})", "source": "tradeoff"})
    profile.evidence.append({"field": f"emphasis.{loser}", "factor": loser, "strength": "tradeoff_lose",
                             "quote": f"chose {winner} over {loser} (key {key})", "source": "tradeoff"})
