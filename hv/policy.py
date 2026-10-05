"""The ranking policy: every number the ranker uses, in one versioned JSON file instead of code.

Who changes it and how:
  - officers edit it (or set the base weights by an AHP pairwise survey), per district if needed;
  - scripts/learn.py proposes new values from logged choices and verified outcomes;
  - nothing goes live without an officer activating it, and every version is kept (config/history/).
All values are checked against safe bounds before they are used.
"""

import copy
import json
import threading
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .config import ROOT

FACTORS = ("aspiration", "skill", "demand", "access", "completion", "income")
CONFIG = ROOT / "config"

DEFAULT: dict = {
    "version": "default-1",
    "base_weights": {"aspiration": 25, "skill": 20, "demand": 20, "access": 15, "completion": 10, "income": 10},
    "emphasis": {
        # evidence -> belief (log-odds style); belief -> multiplier m between min and max (neutral = 1)
        "label_logit": {"insists": 2.0, "prefers": 0.6, "neutral": 0.0, "doesnt_care": -1.2,
                        "tradeoff_win": 1.5, "tradeoff_lose": -0.75},
        "intensifier_bonus": 0.5,  # added when the quote has words like "only", "never", "सिर्फ", "फक्त"
        "max_belief": 4.0,
        "scale": 2.0,  # how fast belief saturates
        "min": 0.5,
        "max": 3.0,
    },
    "gates": {
        "capacity_by_age": [[18, 5], [35, 5], [45, 4], [55, 3], [65, 2]],  # interpolated between points
        "health_penalty": {"none": 0, "some": 1, "severe": 2},
        "work_base": 0.2,  # gate = work_base ** (load above capacity)
        "default_radius_km": 25,
        "radius_exponent": 0.55,  # radius = default / m_access ** exponent (insists -> ~15 km)
        "min_radius_km": 5,
        "distance_halflife": 1.0,  # score halves for every extra radius (x halflife) beyond the radius
        "residential_km": 30,
        "drop_below": 0.05,
        "rejected_factor": 0.1,  # a kind of work the person said no to keeps only this share of its score
        "unrelated_factor": 0.5,  # work unrelated to anything the person does or wants (once they said it)
    },
    "tradeoff": {"enabled": True, "max_questions": 1, "min_pull": 0.03, "max_score_gap": 0.12},
    # guided follow-up questions (hv/questions.py): which question to ask next is decided by how much
    # each possible answer would change the top options (value), plus the LLM's suggestion
    "questions": {"max_followups": 4, "min_value": 0.15, "llm_hint_bonus": 0.2, "top_n": 3,
                  "lead_after": 2},
    "sector_load": {
        "construction": 5, "agriculture": 4, "metal": 4, "logistics": 4, "livestock": 3, "automotive": 3,
        "electrical": 3, "food": 3, "care": 3, "facility": 3, "apparel": 2, "handicraft": 2, "beauty": 2,
        "retail": 2, "electronics": 2, "vishwakarma": 2, "rpl": 2, "entrepreneurship": 1, "it_ites": 1},
    # work that has been forced on caste lines: never offered by default, only when the person's own
    # work or wish includes it (sanitation, tanning, cobbling)
    "consent_only_codes": [9613, 7535, 7536],
    "learning": {"min_choices": 200, "min_outcomes": 300, "l2": 0.5, "max_weight_change": 10,
                 "max_gender_gap": 0.05},
    "district_overrides": {},
}

BOUNDS = {
    ("emphasis", "min"): (0.2, 0.99), ("emphasis", "max"): (1.01, 5.0), ("emphasis", "scale"): (0.5, 10.0),
    ("emphasis", "max_belief"): (1.0, 10.0), ("emphasis", "intensifier_bonus"): (0.0, 2.0),
    ("gates", "work_base"): (0.01, 0.95), ("gates", "default_radius_km"): (3, 100),
    ("gates", "radius_exponent"): (0.0, 2.0), ("gates", "min_radius_km"): (1, 50),
    ("gates", "distance_halflife"): (0.2, 5.0), ("gates", "residential_km"): (5, 200),
    ("gates", "drop_below"): (0.0, 0.5), ("tradeoff", "min_pull"): (0.0, 1.0),
    ("gates", "rejected_factor"): (0.0, 1.0), ("gates", "unrelated_factor"): (0.0, 1.0), ("questions", "max_followups"): (0, 10),
    ("questions", "min_value"): (0.0, 1.0), ("questions", "llm_hint_bonus"): (0.0, 1.0),
    ("questions", "top_n"): (1, 5), ("questions", "lead_after"): (0, 10),
    ("tradeoff", "max_score_gap"): (0.0, 1.0),
}


class PolicyError(ValueError):
    pass


def _merge(base: dict, extra: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def validate(p: dict) -> dict:
    """Check every value against safe bounds; normalise weights to sum to 100."""
    unknown = set(p) - set(DEFAULT)
    if unknown:
        raise PolicyError(f"unknown keys: {sorted(unknown)}")
    w = p["base_weights"]
    if set(w) != set(FACTORS) or any(not isinstance(v, (int, float)) or v < 1 or v > 100 for v in w.values()):
        raise PolicyError("base_weights: one value 1..100 for each of " + ", ".join(FACTORS))
    total = sum(w.values())
    p["base_weights"] = {k: round(100 * v / total, 2) for k, v in w.items()}
    for (section, key), (lo, hi) in BOUNDS.items():
        v = p[section][key]
        if not isinstance(v, (int, float)) or not lo <= v <= hi:
            raise PolicyError(f"{section}.{key} = {v!r} must be between {lo} and {hi}")
    ages = p["gates"]["capacity_by_age"]
    if not ages or any(len(a) != 2 or not 1 <= a[1] <= 5 for a in ages) or ages != sorted(ages):
        raise PolicyError("gates.capacity_by_age: sorted [age, capacity 1..5] pairs")
    if any(not 1 <= v <= 5 for v in p["sector_load"].values()):
        raise PolicyError("sector_load values must be 1..5")
    if any(not isinstance(c, int) for c in p["consent_only_codes"]):
        raise PolicyError("consent_only_codes: a list of NCO codes")
    logits = p["emphasis"]["label_logit"]
    if not logits["insists"] > logits["prefers"] > logits["neutral"] > logits["doesnt_care"]:
        raise PolicyError("emphasis.label_logit must keep insists > prefers > neutral > doesnt_care")
    for code, ov in p.get("district_overrides", {}).items():
        if set(ov) - {"base_weights", "emphasis", "gates", "tradeoff", "questions"}:
            raise PolicyError(f"district {code}: only base_weights, emphasis, gates, tradeoff, questions "
                              "can be overridden")
    return p


class Policy:
    def __init__(self, raw: dict | None = None):
        merged = _merge(DEFAULT, raw or {})
        self.raw = validate(merged)
        self.version = self.raw["version"]
        self.weights: dict[str, float] = self.raw["base_weights"]
        self.emphasis: dict = self.raw["emphasis"]
        self.gates: dict = self.raw["gates"]
        self.tradeoff: dict = self.raw["tradeoff"]
        self.questions: dict = self.raw["questions"]
        self.sector_load: dict[str, int] = self.raw["sector_load"]
        self.learning: dict = self.raw["learning"]
        self.consent_only: set[int] = set(self.raw["consent_only_codes"])

    def for_district(self, code: str | None) -> "Policy":
        ov = self.raw.get("district_overrides", {}).get(code or "")
        if not ov:
            return self
        raw = _merge(self.raw, ov)
        raw["version"] = f"{self.version}+{code}"
        return Policy(raw)

    def capacity(self, age: int | None, health: str) -> float:
        pts = np.array(self.gates["capacity_by_age"], dtype=float)
        cap = float(np.interp(age or 30, pts[:, 0], pts[:, 1]))
        return max(1.0, cap - self.gates["health_penalty"].get(health, 0))

    def to_dict(self) -> dict:
        return copy.deepcopy(self.raw)


class PolicyStore:
    """config/policy.json is the active policy (reloaded when the file changes);
    config/history/ keeps every version; config/proposed/ holds learned proposals waiting for approval."""

    def __init__(self, folder: Path = CONFIG):
        self.folder = folder
        self.path = folder / "policy.json"
        self._lock = threading.Lock()
        self._mtime = None
        self._policy = Policy()

    def active(self) -> Policy:
        with self._lock:
            mtime = self.path.stat().st_mtime if self.path.exists() else None
            if mtime != self._mtime:
                self._policy = Policy(json.loads(self.path.read_text(encoding="utf-8"))) if mtime else Policy()
                self._mtime = mtime
            return self._policy

    def save(self, raw: dict, actor: str, note: str = "") -> Policy:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        raw = dict(raw, version=f"{stamp}-{actor}")
        policy = Policy(raw)  # raises PolicyError if anything is out of bounds
        (self.folder / "history").mkdir(parents=True, exist_ok=True)
        body = json.dumps(policy.to_dict(), indent=1, ensure_ascii=False)
        (self.folder / "history" / f"{policy.version}.json").write_text(body, encoding="utf-8")
        log = self.folder / "history" / "log.jsonl"
        with log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"version": policy.version, "actor": actor, "note": note, "at": stamp}) + "\n")
        self.path.write_text(body, encoding="utf-8")
        return self.active()

    def history(self) -> list[dict]:
        log = self.folder / "history" / "log.jsonl"
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()]

    def proposals(self) -> list[dict]:
        folder = self.folder / "proposed"
        return [json.loads(p.read_text(encoding="utf-8")) | {"file": p.name}
                for p in sorted(folder.glob("*.json"))] if folder.exists() else []

    def activate(self, file: str, actor: str) -> Policy:
        path = self.folder / "proposed" / Path(file).name
        proposal = json.loads(path.read_text(encoding="utf-8"))
        policy = self.save(proposal["policy"], actor, f"activated proposal {path.name}")
        path.rename(path.with_suffix(".activated"))
        return policy


def ahp_weights(matrix: list[list[float]]) -> tuple[dict[str, float], float]:
    """Base weights from an officer's pairwise survey (Saaty's AHP).

    matrix[i][j] = how much more important factor i is than factor j (1..9, and 1/x the other way),
    in FACTORS order. Returns (weights summing to 100, consistency ratio; above 0.1 means re-ask)."""
    a = np.array(matrix, dtype=float)
    n = len(FACTORS)
    if a.shape != (n, n) or np.any(a <= 0):
        raise PolicyError(f"need a {n}x{n} matrix of positive numbers")
    vals, vecs = np.linalg.eig(a)
    k = int(np.argmax(vals.real))
    w = np.abs(vecs[:, k].real)
    w = w / w.sum()
    ci = (vals[k].real - n) / (n - 1)
    cr = ci / 1.24  # Saaty's random index for n = 6
    return {f: round(float(x) * 100, 2) for f, x in zip(FACTORS, w)}, round(float(cr), 3)


POLICIES = PolicyStore()
