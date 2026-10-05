"""The dynamic parts: policy file, evidence-based emphasis, trade-off question, learning, policy API."""

import asyncio
import base64
import json
import random
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from hv import policy as policy_mod
from hv.channels.script import ScriptChannel
from hv.data import get_data
from hv.emphasis import belief, multiplier
from hv.engine import Conversation
from hv.learn import fit_choice_weights, fit_gates, propose
from hv.llm import LLM
from hv.policy import FACTORS, Policy, PolicyError, PolicyStore, ahp_weights
from hv.profile import Profile
from hv.ranker import radius, rank, tradeoff
from hv.store import Store
from hv.stt import STT

DATA = get_data()


def ev(factor, strength, quote="", intensity=0.5):
    return {"factor": factor, "strength": strength, "quote": quote, "intensity": intensity, "source": "llm"}


class PolicyTest(unittest.TestCase):
    def test_weights_are_normalised_and_bounded(self):
        p = Policy({"base_weights": {k: 10 for k in FACTORS}})
        self.assertAlmostEqual(sum(p.weights.values()), 100, places=1)
        with self.assertRaises(PolicyError):
            Policy({"base_weights": {"aspiration": 0, **{k: 10 for k in FACTORS[1:]}}})
        with self.assertRaises(PolicyError):
            Policy({"gates": {"work_base": 1.5}})
        with self.assertRaises(PolicyError):
            Policy({"emphasis": {"label_logit": {"insists": 0.1, "prefers": 0.6, "neutral": 0, "doesnt_care": -1,
                                                 "tradeoff_win": 1, "tradeoff_lose": -1}}})

    def test_district_override(self):
        p = Policy({"district_overrides": {"MH-PUN": {"base_weights": {"demand": 60}}}})
        self.assertGreater(p.for_district("MH-PUN").weights["demand"], p.weights["demand"])
        self.assertIs(p.for_district("MH-NAG"), p)

    def test_ahp_recovers_consistent_weights(self):
        w = [30, 20, 15, 15, 10, 10]
        m = [[a / b for b in w] for a in w]
        got, cr = ahp_weights(m)
        self.assertLess(abs(got["aspiration"] - 30), 0.5)
        self.assertLess(cr, 0.01)
        m[0][1], m[1][0] = 9, 1 / 9  # an inconsistent answer raises the ratio
        self.assertGreater(ahp_weights(m)[1], 0.0)

    def test_store_saves_versions_and_reloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            ps = PolicyStore(Path(tmp))
            self.assertEqual(ps.active().version, "default-1")
            raw = ps.active().to_dict()
            raw["base_weights"]["income"] = 40
            v = ps.save(raw, "officer1", "more weight on pay").version
            self.assertEqual(ps.active().version, v)
            self.assertEqual(ps.history()[-1]["actor"], "officer1")
            (Path(tmp) / "proposed").mkdir()
            (Path(tmp) / "proposed" / "p1.json").write_text(json.dumps({"policy": Policy().to_dict()}))
            self.assertEqual(len(ps.proposals()), 1)
            ps.activate("p1.json", "officer2")
            self.assertEqual(ps.proposals(), [])


class EmphasisTest(unittest.TestCase):
    pol = Policy()

    def m(self, *evidence):
        return multiplier(Profile(evidence=list(evidence)), "access", self.pol)

    def test_order_and_bounds(self):
        ins, pre, neu, dc = (self.m(ev("access", s)) for s in ("insists", "prefers", "neutral", "doesnt_care"))
        self.assertTrue(ins > pre > neu == 1.0 > dc)
        self.assertLessEqual(self.m(*[ev("access", "insists", "only only", 1.0)] * 10), self.pol.emphasis["max"])
        self.assertGreaterEqual(self.m(*[ev("access", "doesnt_care")] * 10), self.pol.emphasis["min"])

    def test_intensity_intensifier_and_repetition_raise_it(self):
        base = self.m(ev("access", "prefers", "पास में हो"))
        self.assertGreater(self.m(ev("access", "prefers", "पास में हो", 1.0)), base)
        self.assertGreater(self.m(ev("access", "prefers", "सिर्फ पास में हो")), base)
        self.assertGreater(self.m(ev("access", "prefers", "पास में"), ev("access", "prefers", "नज़दीक")), base)

    def test_radius_shrinks_smoothly_with_access_emphasis(self):
        r = [radius(Profile(evidence=[ev("access", s)]), self.pol) for s in ("neutral", "prefers", "insists")]
        self.assertEqual(r[0], 25)
        self.assertTrue(r[0] > r[1] > r[2] >= 14)
        self.assertEqual(radius(Profile(radius_km=5, evidence=[ev("access", "insists")]), self.pol), 5)

    def test_capacity_is_interpolated(self):
        self.assertEqual(self.pol.capacity(30, "none"), 5)
        self.assertAlmostEqual(self.pol.capacity(50, "none"), 3.5)
        self.assertAlmostEqual(self.pol.capacity(50, "some"), 2.5)


class RankerPolicyTest(unittest.TestCase):
    def test_caste_linked_work_only_when_asked_for(self):
        p = Profile(age=30, gender="male", district="MH-PUN", education="10th", occupation_codes=[9112], years=2)
        ids = [o.course.course_id for o in rank(DATA, p, 5)]
        self.assertFalse([c for c in DATA.courses if c.course_id in ids and 9613 in c.nco_codes])
        p.aspiration_codes = [9613]
        every = rank(DATA, p, keep_dropped=True)
        self.assertTrue(any(9613 in o.course.nco_codes and o.gates["eligibility"] == 1 for o in every))

    def test_stricter_policy_changes_gate(self):
        p = Profile(age=50, health="some", district="MH-PUN", occupation_codes=[7112], years=10)
        soft = Policy({"gates": {"work_base": 0.9}})
        heavy = [o for o in rank(DATA, p, keep_dropped=True, policy=soft) if o.over_load >= 2]
        strict = [o for o in rank(DATA, p, keep_dropped=True, policy=Policy()) if o.over_load >= 2]
        self.assertGreater(max(o.score for o in heavy), max(o.score for o in strict))

    def test_tradeoff_detection(self):
        a = SimpleNamespace(score=0.70, weights={k: 1 / 6 for k in FACTORS},
                            factors={**{k: 0.5 for k in FACTORS}, "access": 0.9, "income": 0.3})
        b = SimpleNamespace(score=0.68, weights=a.weights, factors={**{k: 0.5 for k in FACTORS}, "access": 0.3, "income": 0.9})
        self.assertEqual(tradeoff([a, b], Policy()), ("access", "income"))
        b.score = 0.3
        self.assertIsNone(tradeoff([a, b], Policy()))


class TradeoffConversationTest(unittest.TestCase):
    def test_engine_asks_and_learns_from_the_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = (policy_mod.POLICIES.folder, policy_mod.POLICIES.path, policy_mod.POLICIES._mtime)
            policy_mod.POLICIES.folder, policy_mod.POLICIES.path = Path(tmp), Path(tmp) / "policy.json"
            policy_mod.POLICIES._mtime = "force-reload"
            try:
                raw = Policy().to_dict()
                raw["tradeoff"] = {"enabled": True, "max_questions": 1, "min_pull": 0.0, "max_score_gap": 1.0}
                policy_mod.POLICIES.save(raw, "test")
                store = Store(Path(tmp) / "t.db")
                from hv.config import settings
                settings.cards_dir = Path(tmp) / "cards"
                story = "मैं पाँच साल से बिजली का काम करता हूँ। 5 साल। नौकरी चाहिए, कमाई ज़रूरी है।"
                answers = {"lang_hi": "1", "consent": "1", "consent_ai": "1", "returning": "2", "ask_name": "Ravi",
                           "ask_story": story, "say_age": "30", "say_gender": "पुरुष", "say_education": "दसवीं",
                           "say_travel": "तीस किलोमीटर", "review_ok": "हाँ", "tf_press_2": "1", "choose_prompt": "1",
                           "confirm_choice": "1", "set_pin": "1357", "set_pin_again": "1357"}
                ch = ScriptChannel(answers, device_pin="411001", default="")
                conv = Conversation(ch, DATA, LLM(DATA, real=False), STT(real=False), store)
                self.assertEqual(asyncio.run(conv.run()), "completed")
                self.assertIn("tradeoff_q", ch.heard)
                self.assertTrue(any(e.get("source") == "tradeoff" for e in conv.profile.evidence))
                store.db.close()
            finally:
                policy_mod.POLICIES.folder, policy_mod.POLICIES.path, policy_mod.POLICIES._mtime = old


class LearnTest(unittest.TestCase):
    def test_choices_that_favour_pay_raise_the_income_weight(self):
        rnd = random.Random(1)
        sets = []
        for _ in range(300):
            opts = [{"factors": {k: rnd.random() for k in FACTORS}, "multipliers": {k: 1.0 for k in FACTORS}}
                    for _ in range(4)]
            sets.append({"options": opts, "chosen": max(range(4), key=lambda i: opts[i]["factors"]["income"])})
        prior = Policy().weights
        fitted = fit_choice_weights(sets, prior, l2=0.1)
        self.assertGreater(fitted["income"], prior["income"] + 5)

    def test_gate_strength_from_outcomes(self):
        rnd = random.Random(2)
        rows = []
        for _ in range(3000):
            over = rnd.choice([0, 0, 1, 2])
            rows.append({"over_load": over, "excess_ratio": 0, "completed": int(rnd.random() < 0.8 * 0.4 ** over)})
        got = fit_gates(rows, Policy().gates)
        self.assertAlmostEqual(got["work_base"], 0.4, delta=0.1)

    def test_proposal_needs_enough_data(self):
        out = propose(DATA, Policy(), [], [], [])
        self.assertFalse(out["ok"])
        self.assertTrue(out["report"]["blocked"])


class PolicyApiTest(unittest.TestCase):
    def test_officer_edits_weights_and_runs_ahp(self):
        from hv.config import settings
        with tempfile.TemporaryDirectory() as tmp:
            settings.officer_user, settings.officer_password = "officer", "pw"
            old = (policy_mod.POLICIES.folder, policy_mod.POLICIES.path, policy_mod.POLICIES._mtime)
            policy_mod.POLICIES.folder, policy_mod.POLICIES.path = Path(tmp), Path(tmp) / "policy.json"
            policy_mod.POLICIES._mtime = "force-reload"
            try:
                from starlette.testclient import TestClient
                from hv.server import app
                c = TestClient(app)
                auth = {"Authorization": "Basic " + base64.b64encode(b"officer:pw").decode()}
                self.assertEqual(c.get("/api/policy").status_code, 401)
                r = c.post("/api/policy", headers=auth, json={"base_weights": {"income": 30}, "district": "MH-PUN"})
                self.assertTrue(r.json()["ok"])
                self.assertIn("MH-PUN", c.get("/api/policy", headers=auth).json()["active"]["district_overrides"])
                bad = c.post("/api/policy", headers=auth, json={"gates": {"work_base": 7}})
                self.assertEqual(bad.status_code, 400)
                w = [25, 20, 20, 15, 10, 10]
                r = c.post("/api/policy/ahp", headers=auth, json={"matrix": [[a / b for b in w] for a in w], "save": True})
                self.assertTrue(r.json()["saved"])
            finally:
                policy_mod.POLICIES.folder, policy_mod.POLICIES.path, policy_mod.POLICIES._mtime = old


if __name__ == "__main__":
    unittest.main()
