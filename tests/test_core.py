"""Core tests (no GPU): ranker gates, labels checks, IDs and PINs, a full conversation."""

import asyncio
import tempfile
import unittest
from pathlib import Path

from hv.channels.script import ScriptChannel
from hv.data import get_data
from hv.engine import Conversation
from hv.identity import hash_pin, check_pin, new_id, valid_id
from hv.labels import quote_found, validate
from hv.llm import LLM
from hv.profile import Profile
from hv.ranker import rank
from hv.store import Store
from hv.stt import STT

DATA = get_data()
SUNITA_STORY = ("मैं खेत में मज़दूरी करती हूँ और पाँच साल से घर पर सिलाई भी करती हूँ। 5 साल। मैं सिलाई ही सीखनी "
                "चाहती हूँ, पर घर छोड़कर नहीं जा सकती, बच्चे हैं। घुटने में दर्द रहता है।")


def sunita(**kw) -> Profile:
    p = Profile(language="hi", age=48, gender="female", pin="411001", district="MH-PUN", education="upto_5th",
                health="some", cannot_leave_home=True, lean="either", occupation_codes=[7531], years=5,
                aspiration_codes=[7531], emphasis={"access": "insists", "aspiration": "insists"})
    for k, v in kw.items():
        setattr(p, k, v)
    return p


class RankerTest(unittest.TestCase):
    def test_top_options_fit_her_life(self):
        opts = rank(DATA, sunita())
        self.assertTrue(3 <= len(opts) <= 5)
        for o in opts:
            self.assertLessEqual(o.centre.distance_km, 30, "no residential centre for someone who cannot leave home")
            self.assertLessEqual(DATA.load(o.course), 3, "no heavy work for a 48-year-old with knee pain")
        self.assertIn("R7531", [o.course.course_id for o in opts], "RPL for her 5 years of tailoring")

    def test_gates_drop_heavy_and_far_work(self):
        every = {(o.course.course_id, o.centre.centre_id): o for o in rank(DATA, sunita(), keep_dropped=True)}
        construction = [o for o in every.values() if DATA.load(o.course) == 5]
        self.assertTrue(construction)
        self.assertTrue(all("work_capacity" in o.dropped_by for o in construction))
        far = [o for o in every.values() if o.centre.distance_km > 30]
        self.assertTrue(all(o.gates["distance"] == 0 for o in far))

    def test_young_person_can_do_heavy_work(self):
        p = Profile(age=22, gender="male", district="MH-PUN", education="10th", occupation_codes=[7112],
                    years=3, lean="job", radius_km=30, hostel_ok=True)
        ids = [o.course.course_id for o in rank(DATA, p)]
        self.assertTrue(any(DATA.load(c) >= 4 for c in DATA.courses if c.course_id in ids))

    def test_rpl_needs_a_skill_already_held(self):
        p = sunita(occupation_codes=[], aspiration_codes=[7531])
        self.assertNotIn("certificate", [o.course.kind for o in rank(DATA, p)])

    def test_emphasis_changes_the_order(self):
        far_ok = sunita(cannot_leave_home=False, emphasis={"income": "insists"}, radius_km=30, hostel_ok=True, age=30,
                        health="none")
        near = sunita()
        self.assertNotEqual([o.course.course_id for o in rank(DATA, far_ok)],
                            [o.course.course_id for o in rank(DATA, near)])


class LabelsTest(unittest.TestCase):
    def test_codes_outside_our_list_are_rejected(self):
        lab = validate({"occupation_codes": [7531, 1234], "emphasis": [], "mood": "neutral"}, "सिलाई", DATA)
        self.assertEqual(lab.occupation_codes, [7531])
        self.assertTrue(lab.rejected)

    def test_emphasis_needs_a_real_quote(self):
        raw = {"occupation_codes": [], "mood": "neutral", "emphasis": [
            {"factor": "access", "strength": "insists", "quote": "घर छोड़कर नहीं जा सकती"},
            {"factor": "income", "strength": "insists", "quote": "मुझे बहुत पैसा चाहिए"}]}
        lab = validate(raw, SUNITA_STORY, DATA)
        self.assertEqual([e["factor"] for e in lab.emphasis], ["access"])

    def test_quote_matching_tolerates_small_spelling_changes(self):
        self.assertTrue(quote_found("घर छोड़कर नहीं जा सकती", "पर घर छोड़कर नहीं जा सकते बच्चे हैं"))
        self.assertFalse(quote_found("ज़्यादा पैसा", SUNITA_STORY))

    def test_fake_labeller_reads_sunita(self):
        lab = LLM(DATA, real=False).label(SUNITA_STORY)
        self.assertIn(7531, lab.occupation_codes)
        self.assertEqual(lab.years, 5)
        self.assertTrue(lab.cannot_leave_home)
        self.assertEqual(lab.health, "some")
        self.assertIn(("access", "insists"), [(e["factor"], e["strength"]) for e in lab.emphasis])


class IdentityTest(unittest.TestCase):
    def test_ids_have_a_check_digit(self):
        for _ in range(200):
            i = new_id()
            self.assertTrue(valid_id(i))
            wrong = i[:8] + str((int(i[8]) + 1) % 10)
            self.assertFalse(valid_id(wrong))

    def test_pin_hash(self):
        salt, h = hash_pin("4321")
        self.assertTrue(check_pin("4321", salt, h))
        self.assertFalse(check_pin("1234", salt, h))


def run(answers, store, can_type=True, device_pin="411001"):
    ch = ScriptChannel(answers, can_type=can_type, device_pin=device_pin, default=None)
    conv = Conversation(ch, DATA, LLM(DATA, real=False), STT(real=False), store)
    reason = asyncio.run(conv.run())
    return conv, ch, reason


# answers by question key, so the tests do not depend on the order the guided conversation picks
START = {"lang_hi": "1", "consent": "हाँ", "consent_ai": "हाँ", "returning": "नहीं"}
SPOKEN = {"ask_name": "मेरा नाम सुनीता है", "ask_story": SUNITA_STORY, "say_age": "अड़तालीस साल",
          "say_gender": "महिला", "say_education": "पाँचवीं तक पढ़ी हूँ", "say_travel": "दस किलोमीटर तक, हॉस्टल नहीं",
          "say_health": "थोड़ी", "say_lean": "दोनों", "ask_aspiration": "", "ask_family": "",
          "q_goal": "इसी काम में आगे बढ़ना है", "q_lead_post": "हाँ", "q_home": "घर से", "q_duration": "तीन महीने",
          "q_earn_soon": "पहले सीखना ठीक है", "q_certificate": "हाँ", "q_own_business": "नहीं", "q_years": "पाँच साल"}
END = {"review_ok": "हाँ", "choose_prompt": "पहला", "confirm_choice": "हाँ", "tf_press_2": "1",
       "set_pin": "4321", "set_pin_again": "4321"}


def new_person(**changes):
    return {**START, **SPOKEN, **END, **changes}


class ConversationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "t.db")
        from hv.config import settings
        settings.cards_dir = Path(self.tmp.name) / "cards"

    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()

    def test_new_person_end_to_end(self):
        conv, ch, reason = run(new_person(), self.store)
        self.assertEqual(reason, "completed")
        person = self.store.person(conv.hv_id)
        self.assertEqual(person["name"], "सुनीता")
        self.assertEqual(person["district"], "MH-PUN")
        self.assertTrue(self.store.options(conv.hv_id)[0]["chosen"])
        self.assertEqual(self.store.check_pin(conv.hv_id, "4321"), "ok")
        self.assertTrue((Path(self.tmp.name) / "cards" / f"{conv.hv_id}.svg").exists())
        self.assertIn("never_money", ch.heard)
        self.assertIn("card", [k for k, _ in ch.shown])
        self.assertIn("review", [k for k, _ in ch.shown])
        self.assertEqual(self.store.find(district="MH-PUN", name="सुनी")[0]["hv_id"], conv.hv_id)

    def test_details_are_spoken_and_understood(self):
        conv, ch, _ = run(new_person(), self.store)
        pr = conv.profile
        self.assertEqual((pr.age, pr.gender, pr.education, pr.radius_km, pr.hostel_ok),
                         (48, "female", "upto_5th", 10, False))
        for typed in ("ask_age", "ask_education", "ask_travel", "ask_gender"):  # keypad versions not needed
            self.assertNotIn(typed, ch.heard)

    def test_location_comes_from_the_device(self):
        conv, ch, _ = run(new_person(), self.store, device_pin="411001")
        self.assertNotIn("ask_pincode", ch.heard)
        self.assertEqual(conv.profile.location_from, "device")
        conv, ch, _ = run(new_person(ask_pincode="411001"), self.store, device_pin="")
        self.assertIn("ask_pincode", ch.heard)
        self.assertEqual((conv.profile.district, conv.profile.location_from), ("MH-PUN", "asked"))

    def test_what_the_story_already_says_is_not_asked_again(self):
        story = "मेरी उम्र चालीस साल है, दसवीं पास हूँ। पाँच साल से बिजली का काम करता हूँ।"
        conv, ch, _ = run(new_person(ask_story=story, say_gender="पुरुष"), self.store)
        self.assertEqual((conv.profile.age, conv.profile.education), (40, "10th"))
        self.assertNotIn("say_age", ch.asked)
        self.assertNotIn("say_education", ch.asked)
        self.assertIn("say_travel", ch.asked)

    def test_follow_ups_are_chosen_by_what_could_change_the_shortlist(self):
        conv, _, _ = run(new_person(), self.store)
        plan = conv.plan_log
        self.assertTrue(plan)
        self.assertTrue(all("why" in x and "score" in x for x in plan))
        follow = [x for x in plan if not x["question"].startswith(("say_age", "say_gender", "say_education",
                                                                       "say_travel"))]
        for x in follow:  # a follow-up is only asked when its answer could change something
            self.assertGreaterEqual(x["score"], conv.policy().questions["min_value"])
        self.assertLessEqual(len(follow), conv.policy().questions["max_followups"])

    def test_review_lets_the_person_correct_a_detail(self):
        answers = new_person(review_ok=["नहीं", "हाँ"], review_which="उम्र", say_age=["अड़तालीस साल", "बावन साल"])
        conv, ch, reason = run(answers, self.store)
        self.assertEqual(reason, "completed")
        self.assertEqual(conv.profile.age, 52)
        self.assertEqual(ch.heard.count("review_ok"), 2)

    def test_unclear_answer_falls_back_to_the_keypad(self):
        conv, ch, _ = run(new_person(say_education="ब्लाब्ला", ask_education="4"), self.store)
        self.assertIn("ask_education", ch.heard)
        self.assertEqual(conv.profile.education, "10th")

    def test_saying_no_to_the_leading_work_drops_it(self):
        story = "मैं पहले फैक्ट्री में काम करता था, अब नौकरी चली गई। कुछ भी काम चाहिए।"
        conv, ch, _ = run(new_person(ask_story=story, say_gender="पुरुष", say_age="तीस साल",
                                     say_education="बारहवीं", say_travel="तीस किलोमीटर", q_lead_post="नहीं"),
                          self.store)
        if "q_lead" in [x["question"] for x in conv.plan_log]:
            rejected = conv.profile.rejected_sectors
            self.assertTrue(rejected)
            self.assertNotIn(rejected[0], [DATA.course_sector(o.course) for o in conv.options])

    def test_yes_with_a_polite_no_word_is_still_yes(self):
        conv, ch, reason = run(new_person(consent="हाँ, कोई बात नहीं", consent_ai="हो, हरकत नाही"), self.store)
        self.assertEqual(reason, "completed")
        self.assertTrue(conv.consent["ai_training"])

    def test_unclear_answers_never_end_the_call(self):
        answers = new_person(review_ok="उम्म", choose_prompt="पता नहीं", confirm_choice="हम्म", tf_press_2="उम्म")
        conv, ch, reason = run(answers, self.store, can_type=False)
        self.assertEqual(reason, "completed")
        self.assertIsNotNone(self.store.person(conv.hv_id))

    def test_person_is_saved_before_the_options(self):
        answers = new_person()
        answers.pop("choose_prompt")
        conv, ch, reason = run(answers, self.store)  # the script stops at the options, like a dropped call
        self.assertNotEqual(reason, "completed")
        self.assertIsNotNone(conv.hv_id)
        self.assertTrue(self.store.options(conv.hv_id))

    def test_travel_correction_can_undo_cannot_leave_home(self):
        answers = new_person(review_ok=["नहीं", "हाँ"], review_which="दूरी",
                             say_travel=["दस किलोमीटर, हॉस्टल नहीं", "तीस किलोमीटर, हॉस्टल में रह सकती हूँ"])
        conv, ch, reason = run(answers, self.store)
        self.assertEqual(reason, "completed")
        self.assertEqual((conv.profile.radius_km, conv.profile.hostel_ok, conv.profile.cannot_leave_home),
                         (30, True, False))

    def test_health_can_be_corrected_in_the_review(self):
        answers = new_person(review_ok=["नहीं", "हाँ"], review_which="7", say_health="ज़्यादा तकलीफ नहीं है")
        conv, ch, reason = run(answers, self.store)
        self.assertEqual(reason, "completed")
        self.assertEqual(conv.profile.health, "none")

    def test_returning_person_with_card_and_pin(self):
        conv, _, _ = run(new_person(), self.store)
        _, ch, reason = run({**START, "returning": "1", "ask_id": conv.hv_id, "ask_pin": "4321"}, self.store)
        self.assertEqual(reason, "completed")
        self.assertIn("welcome_back", ch.heard)

    def test_wrong_pin_locks_after_three_tries(self):
        conv, _, _ = run(new_person(), self.store)
        _, ch, reason = run({**START, "returning": "1", "ask_id": conv.hv_id, "ask_pin": ["0000", "1111", "2222"]},
                            self.store)
        self.assertEqual(reason, "PIN locked")

    def test_no_consent_ends_politely(self):
        _, ch, reason = run({"lang_hi": "2", "consent": "नाही"}, self.store)
        self.assertEqual(reason, "completed")
        self.assertIn("consent_no", ch.heard)

    def test_nine_twice_deletes(self):
        _, ch, reason = run({"lang_hi": "1", "consent": "1", "consent_ai": "9", "delete_confirm": "9"}, self.store)
        self.assertEqual(reason, "caller deleted their data")

    def test_phone_with_a_silent_story_still_completes(self):
        conv, ch, reason = run(new_person(ask_story="", ask_name=""), self.store, can_type=False)
        self.assertEqual(reason, "completed")
        self.assertTrue(conv.hv_id)


if __name__ == "__main__":
    unittest.main()
