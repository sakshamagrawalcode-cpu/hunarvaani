"""Learn the ranking policy from real use, then PROPOSE it. Nothing goes live without an officer.

1. Base weights from choices (conditional logit). People are offered 3-5 options and pick one; the
   weights that best explain their picks, pulled towards the current weights (L2) and limited to a few
   points of change per round.
2. Gate strength from verified outcomes. How much less likely are people to finish when the work is
   one level above their capacity, or the centre is one radius beyond their limit? (log-linear fit of
   completion rate, which matches the gate shape base ** x)
3. Fairness check: the new policy is blocked if it widens the gap between women and men in how often
   the top option is in a better-paid sector.
"""

import math

import numpy as np

from .data import Data
from .policy import FACTORS, Policy
from .profile import Profile
from .ranker import rank


def fit_choice_weights(sets: list[dict], prior: dict[str, float], l2: float = 0.5, iters: int = 800,
                       lr: float = 0.5, temperature: float = 8.0) -> dict[str, float]:
    """sets: [{"options": [{"factors": {...}, "multipliers": {...}}, ...], "chosen": i}].
    Utility of option j = temperature * sum_k beta_k * m_k * f_jk, beta_k = exp(theta_k) > 0."""
    if not sets:
        return dict(prior)
    xs, ys = [], []
    for s in sets:
        f = np.array([[o["factors"][k] for k in FACTORS] for o in s["options"]], dtype=float)
        m = np.array([s["options"][0].get("multipliers", {}).get(k, 1.0) for k in FACTORS], dtype=float)
        xs.append(f * m)
        ys.append(s["chosen"])
    theta0 = np.log(np.array([prior[k] for k in FACTORS], dtype=float) / 100 * len(FACTORS))
    theta = theta0.copy()
    for _ in range(iters):
        beta = np.exp(theta)
        grad = np.zeros_like(theta)
        for x, y in zip(xs, ys):
            u = temperature * x @ beta
            p = np.exp(u - u.max())
            p /= p.sum()
            grad += temperature * (x[y] - p @ x) * beta
        grad = grad / len(xs) - l2 * (theta - theta0)
        theta += lr * grad
    w = np.exp(theta)
    return {k: float(v) for k, v in zip(FACTORS, 100 * w / w.sum())}


def _decay_fit(x: np.ndarray, done: np.ndarray, min_count: int = 30) -> float | None:
    """Slope of log2(completion rate) against x, from rate per rounded x (weighted least squares).
    The gates are of the form gate = base ** x, so this slope maps straight onto them."""
    levels = np.round(x * 2) / 2
    xs, ys, ws = [], [], []
    for lv in np.unique(levels):
        mask = levels == lv
        n, rate = int(mask.sum()), float(done[mask].mean())
        if n >= min_count and rate > 0:
            xs.append(lv)
            ys.append(math.log2(rate))
            ws.append(n)
    if len(xs) < 2:
        return None
    xs_, ys_, ws_ = np.array(xs), np.array(ys), np.array(ws, dtype=float)
    xm, ym = np.average(xs_, weights=ws_), np.average(ys_, weights=ws_)
    return float(np.sum(ws_ * (xs_ - xm) * (ys_ - ym)) / np.sum(ws_ * (xs_ - xm) ** 2))


def fit_gates(rows: list[dict], current: dict) -> dict:
    """New work_base and distance_halflife from verified completions. Returns only what the data supports."""
    out = {}
    done = np.array([r["completed"] for r in rows], dtype=float)
    slope = _decay_fit(np.array([r.get("over_load", 0) for r in rows], dtype=float), done)
    if slope is not None and slope < 0:
        out["work_base"] = round(min(0.95, max(0.01, 2 ** slope)), 3)
    slope = _decay_fit(np.array([r.get("excess_ratio", 0) for r in rows], dtype=float), done)
    if slope is not None and slope < 0:
        out["distance_halflife"] = round(min(5.0, max(0.2, -1 / slope)), 2)
    return {k: v for k, v in out.items() if k in current}


def gender_gap(data: Data, profiles: list[Profile], pol: Policy) -> float:
    """|share of women whose top option is in a better-paid sector - same for men|."""
    wages = sorted(s.wage_max for s in data.sectors.values())
    median = wages[len(wages) // 2]
    share = {}
    for g in ("female", "male"):
        tops = [rank(data, p, 1, policy=pol) for p in profiles if p.gender == g]
        tops = [t[0] for t in tops if t]
        if tops:
            share[g] = sum(data.wage_max(data.course_sector(o.course)) >= median for o in tops) / len(tops)
    return abs(share.get("female", 0) - share.get("male", 0)) if len(share) == 2 else 0.0


def propose(data: Data, pol: Policy, sets: list[dict], outcomes: list[dict], profiles: list[Profile]) -> dict:
    learn = pol.learning
    report: dict = {"choices": len(sets), "outcomes": len(outcomes), "changes": {}, "blocked": []}
    new = pol.to_dict()
    if len(sets) >= learn["min_choices"]:
        fitted = fit_choice_weights(sets, pol.weights, learn["l2"])
        cap = learn["max_weight_change"]
        for k in FACTORS:
            v = min(pol.weights[k] + cap, max(pol.weights[k] - cap, fitted[k]))
            new["base_weights"][k] = round(max(1.0, v), 2)
        report["changes"]["base_weights"] = {k: [pol.weights[k], new["base_weights"][k]] for k in FACTORS}
    else:
        report["blocked"].append(f"weights: need {learn['min_choices']} choices, have {len(sets)}")
    if len(outcomes) >= learn["min_outcomes"]:
        g = fit_gates(outcomes, pol.gates)
        new["gates"].update(g)
        report["changes"]["gates"] = {k: [pol.gates[k], v] for k, v in g.items()}
    else:
        report["blocked"].append(f"gates: need {learn['min_outcomes']} verified outcomes, have {len(outcomes)}")
    if not report["changes"]:
        return {"ok": False, "report": report}
    candidate = Policy(new)
    before, after = gender_gap(data, profiles, pol), gender_gap(data, profiles, candidate)
    report["gender_gap"] = {"before": round(before, 3), "after": round(after, 3)}
    if after > learn["max_gender_gap"] and after > before:
        report["blocked"].append("fairness: the new weights widen the gender gap in better-paid options")
        return {"ok": False, "report": report}
    return {"ok": True, "report": report, "policy": candidate.to_dict()}
