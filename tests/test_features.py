"""Mood-adapted questions, skills worth learning, and the card file."""

import asyncio
import tempfile
import unittest
from pathlib import Path

from hv.card import card_svg, delete_card, load_card, qr_payload, save_card
from hv.channels.script import ScriptChannel
from hv.config import settings
from hv.data import get_data
from hv.engine import Conversation
from hv.questions import BANK
from hv.llm import LLM
from hv.profile import Profile
from hv.skills import gap_for, skill_advice
from hv.store import Store
from hv.stt import STT

DATA = get_data()


def conversation(answers, store, moods=None):
    ch = ScriptChannel(answers)
    conv = Conversation(ch, DATA, LLM(DATA, real=False), STT(real=False), store)
    if moods:
        conv.profile.moods = list(moods)
    return conv, ch


class MoodTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "t.db")
        settings.cards_dir = Path(self.tmp.name) / "cards"

    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()

    def test_wording_follows_mood(self):
        conv, _ = conversation([], self.store)
        self.assertEqual(conv.variant("ask_aspiration"), "ask_aspiration")
        conv.profile.moods = ["upset"]
        self.assertEqual(conv.variant("ask_aspiration"), "ask_aspiration_soft")
        conv.profile.moods = ["hopeful", "neutral"]
        self.assertEqual(conv.variant("ask_aspiration"), "ask_aspiration_hope")
        conv.profile.moods = ["worried"]
        self.assertEqual(conv.variant("ask_family"), "ask_family_soft")

    def test_upset_caller_gets_a_shorter_softer_call(self):
        story = "मेरी नौकरी चली गई, बहुत परेशान हूँ। मैं पाँच साल से बिजली का काम करता था।"
        answers = {"lang_hi": "1", "consent": "1", "consent_ai": "1", "returning": "2", "ask_name": "रवि",
                   "ask_story": story, "say_age": "तीस साल", "say_gender": "पुरुष", "say_education": "दसवीं",
                   "say_travel": "बीस किलोमीटर", "review_ok": "हाँ", "choose_prompt": "1", "confirm_choice": "1",
                   "set_pin": "1357", "set_pin_again": "1357", "tf_press_2": "1"}
        ch = ScriptChannel(answers, device_pin="411001", default="")
        conv = Conversation(ch, DATA, LLM(DATA, real=False), STT(real=False), self.store)
        self.assertEqual(asyncio.run(conv.run()), "completed")
        self.assertIn("empathy_upset", ch.heard)
        self.assertIn("keys_soft_intro", ch.heard)
        self.assertNotIn("ask_family", ch.heard)
        self.assertNotIn("ask_family_soft", ch.heard)
        followups = [x for x in conv.plan_log if not BANK[x["question"]].required]
        self.assertLessEqual(len(followups), 2)  # fewer questions for someone who is upset


class SkillsTest(unittest.TestCase):
    def test_tailor_gets_a_step_up_in_her_trade(self):
        p = Profile(age=32, gender="female", district="MH-PUN", education="10th", occupation_codes=[7531],
                    years=4, radius_km=15)
        advice = skill_advice(DATA, p)
        self.assertTrue(advice)
        self.assertEqual(advice[0]["gap"], "small")
        self.assertTrue(advice[0]["skills"])
        self.assertLessEqual(advice[0]["weeks"], 12)

    def test_moderate_gap_needs_better_pay(self):
        p = Profile(age=30, gender="male", district="MH-PUN", education="10th", occupation_codes=[9112], radius_km=15)
        for a in skill_advice(DATA, p):
            self.assertTrue(a["gap"] == "small" or a["pay_gain"] > 0)

    def test_nothing_without_work_or_district(self):
        self.assertEqual(skill_advice(DATA, Profile(district="MH-PUN")), [])
        self.assertEqual(skill_advice(DATA, Profile(occupation_codes=[7531])), [])

    def test_gap_ignores_skills_already_held(self):
        self.assertEqual(gap_for(("machine stitching", "pattern cutting"), {"machine stitching"}), ["pattern cutting"])


class CardTest(unittest.TestCase):
    def test_card_has_id_and_no_pin_and_is_deleted_on_erase(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings.cards_dir = Path(tmp)
            svg = card_svg("123456782", "आशा <b>", "Pune", "Advanced Tailoring", ["pattern cutting"])
            self.assertIn("1234-5678-2", svg)
            self.assertIn("&lt;b&gt;", svg)  # names are escaped
            self.assertEqual(qr_payload("123456782"), "HUNARVAANI:123456782")
            save_card("123456782", svg)
            self.assertIsNotNone(load_card("123456782"))
            delete_card("123456782")
            self.assertIsNone(load_card("123456782"))


if __name__ == "__main__":
    unittest.main()
