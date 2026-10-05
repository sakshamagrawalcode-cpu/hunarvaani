"""The conversation, written once and used by every channel (phone line, kiosk, terminal simulator).

Everything the person says is spoken: their name, age, studies, travel and their story. The flow:

  name -> "tell us about yourself" (the first real answer: the LLM labels work, wishes, limits, mood,
  and anything else they mention, so it is not asked again) -> guided follow-up questions, each
  chosen because its answer could change the shortlist (hv/questions.py), alternating with the
  required details, worded for the person's mood, checking the leading kind of work with them
  ("this work could suit you: does that sound right?") -> a review screen of everything understood,
  where any detail can be corrected -> top 3-5 options from the gated ranker -> skills worth learning
  -> HunarVaani ID, PIN (typed: a PIN is never spoken aloud) and the card.

The location comes from the device (each kiosk sets its PIN code once; the phone line has its own),
so people are not asked for it. The LLM only labels and suggests; code decides and checks.
"""

import asyncio
import itertools
import logging
from typing import Protocol

from .card import card_svg, delete_card, save_card
from .config import settings
from .data import Data
from .emphasis import add_tradeoff, label_for, multipliers
from .identity import pretty, valid_id, valid_pin
from .labels import Labels, apply
from .llm import LLM
from .policy import POLICIES
from .profile import Profile
from .prompts import T, Part, digits, labels as button_labels, language_menu, num, occ, p, ps, sector
from .questions import BANK, EDU_KEYS, GENDER_KEYS, Plan, Question, top_ids, value
from .ranker import Option, rank, radius, tradeoff
from .skills import skill_advice
from .store import Store
from .stt import STT
from .understand import has, numbers, parse_yes_no

log = logging.getLogger("hv.engine")

# keypad fallbacks (used only when a spoken answer was not understood twice)
EDUCATION = EDU_KEYS
TRAVEL = {"1": 5, "2": 15, "3": 30, "4": 30}
HEALTH = {"1": "none", "2": "some", "3": "severe"}
LEAN = {"1": "job", "2": "own_work", "3": "either"}
GENDER = GENDER_KEYS

TRADEOFF_WORDS = {
    "access": ["पास", "नज़दीक", "नजदीक", "घर", "near", "close", "home", "जवळ"],
    "income": ["कमाई", "पैसा", "पैसे", "पगार", "income", "pay", "money", "salary", "कमाई"],
    "aspiration": ["मनचाहा", "पसंद", "want", "like", "आवडीचं", "आवडीचे"],
    "skill": ["हुनर", "कौशल्य", "skill", "जो आता", "जे येतं"],
    "demand": ["नौकरियाँ", "नौकरी", "jobs", "नोकऱ्या", "नोकरी"],
    "completion": ["छोटा", "आसान", "short", "easy", "सोपा", "जल्दी"],
}
ORDINAL_WORDS = {1: ["पहला", "पहली", "पहिला", "पहिली", "first"], 2: ["दूसरा", "दूसरी", "दुसरा", "दुसरी", "second"],
                 3: ["तीसरा", "तीसरी", "तिसरा", "तिसरी", "third"], 4: ["चौथा", "चौथी", "fourth"],
                 5: ["पाँचवाँ", "पांचवा", "पाचवा", "fifth"]}
AGAIN_WORDS = ["फिर से", "दोबारा", "again", "पुन्हा", "repeat"]
REVIEW_FIELDS = {"1": "name", "2": "age", "3": "education", "4": "travel", "5": "work", "6": "gender", "7": "health"}
REVIEW_WORDS = {"name": ["नाम", "नाव", "name"], "age": ["उम्र", "वय", "age"],
                "education": ["पढ़ाई", "पढाई", "शिक्षण", "studies", "education", "school"],
                "travel": ["दूरी", "अंतर", "travel", "distance", "किलोमीटर"],
                "work": ["काम", "work", "job", "नौकरी"], "gender": ["महिला", "पुरुष", "gender", "woman", "man"],
                "health": ["तकलीफ", "तकलीफ़", "त्रास", "health", "दर्द", "शारीरिक"]}


class Hangup(Exception):
    """The person left (hung up, closed the kiosk, or never answered)."""


class Channel(Protocol):
    name: str
    can_type: bool  # kiosk: a helper can type a correction; phone: no

    async def say(self, parts: list[Part], lang: str) -> None: ...

    async def keys(self, parts: list[Part], lang: str, allowed: str, timeout: float) -> str | None: ...

    async def digits(self, parts: list[Part], lang: str, count: int, timeout: float) -> str | None: ...

    async def talk(self, parts: list[Part], lang: str, allowed: str, labels: list[str],
                   max_seconds: float) -> tuple[str, object]: ...

    async def show(self, kind: str, payload: dict) -> None: ...


class Conversation:
    def __init__(self, ch: Channel, data: Data, llm: LLM, stt: STT, store: Store):
        self.ch, self.data, self.llm, self.stt, self.store = ch, data, llm, stt, store
        self.profile = Profile()
        self.lang = "hi"
        self.sid = ""
        self.hv_id: str | None = None
        self.consent: dict = {}
        self.options: list[Option] = []
        self.advice: list[dict] = []
        self.chosen: int | None = None
        self.empathised: set[str] = set()
        self._acks = itertools.cycle(range(5))
        # the guided conversation
        self.asked: set[str] = set()
        self.health_asked = False
        self.duration_asked = False
        self.lead_sector: str | None = None
        self.llm_hint: str | None = None
        self.answers_after_story = 0
        self.last_kind = "slot"
        self.followups = 0
        self.plan_log: list[dict] = []

    # ------------------------------------------------------------------------------------------
    async def run(self) -> str:
        self.sid = self.store.start_session(self.ch.name)
        reason = "completed"
        try:
            await self._run()
        except Hangup as exc:
            reason = str(exc) or "left early"
        except asyncio.CancelledError:
            reason = "connection closed"
            raise
        finally:
            self.store.end_session(self.sid, reason, self.hv_id)
            log.info("session %s ended: %s", self.sid, reason)
        return reason

    async def _run(self) -> None:
        choice = await self.choice(language_menu(), "123", menu=True)
        self.lang = {"1": "hi", "2": "mr", "3": "en"}[choice]
        self.profile.language = self.lang
        await self.say(["greet", "keys_help"])
        if not await self.yes_no(self.parts(["consent"]), "consent", default=False):
            await self.say(["consent_no"])
            return
        self.consent = {"record_and_share": True,
                        "ai_training": await self.yes_no(self.parts(["consent_ai"]), "consent_ai", default=False)}
        returning = await self.yes_no(self.parts(["returning"]), "returning", default=False,
                                      yes_words=["कार्ड", "card", "नंबर है"],
                                      no_words=["पहली बार", "पहिल्यांदा", "first time", "नया", "नई"])
        if returning and await self.returning():
            return
        await self.new_person()

    # small helpers ----------------------------------------------------------------------------
    def parts(self, keys: list[str]) -> list[Part]:
        return ps(keys, self.lang)

    async def say(self, keys: list[str] | list[Part]) -> None:
        parts = [k if isinstance(k, Part) else p(k, self.lang) for k in keys]
        await self.ch.say(parts, self.lang)

    def log(self, kind: str, question: str, answer: str, labels: dict | None = None) -> None:
        if settings.log_turns:
            self.store.turn(self.sid, kind, question, answer, labels)

    async def ack(self) -> None:
        await self.say([f"ack_{next(self._acks)}"])

    async def choice(self, parts: list[Part], allowed: str, menu: bool = False, fatal: bool = True,
                     tries: int = 4) -> str | None:
        """One key from `allowed`. 0 = ask for a person, 9 = delete my data (asked twice).
        With fatal=False an unanswered question returns None instead of ending the call."""
        prefix: list[Part] = []
        for _ in range(tries):
            extra = "" if menu else "09"
            key = await self.ch.keys(prefix + parts, self.lang, allowed + extra, settings.key_timeout)
            if key and len(key) == 1 and key in allowed:
                self.log("key", parts[0].key, key)
                return key
            if key == "0":
                await self.officer_flag(parts[0].key)
                prefix = self.parts(["human_flag"])
                continue
            if key == "9":
                await self.delete_request()
                prefix = []
                continue
            prefix = self.parts(["no_answer" if key is None else "wrong_key"])
        if not fatal:
            return None
        raise Hangup("no answer")

    async def officer_flag(self, question: str) -> None:
        self.log("human", question, "0")
        self.store.audit("caller", "asked_for_officer", self.hv_id or "", f"session {self.sid}")

    async def delete_request(self) -> None:
        if await self.ch.keys(self.parts(["delete_confirm"]), self.lang, "0123456789", settings.key_timeout) == "9":
            if self.hv_id:
                self.store.delete_person(self.hv_id, "caller")
                delete_card(self.hv_id)
            self.log("delete", "delete_confirm", "9")
            await self.say(["deleted"])
            raise Hangup("caller deleted their data")

    async def number(self, keys: list[str], count: int, ok=lambda s: True, bad: str = "wrong_key",
                     tries: int = 3) -> str | None:
        prefix: list[str] = []
        for _ in range(tries):
            value_ = await self.ch.digits(self.parts(prefix + keys), self.lang, count, settings.key_timeout * 2)
            if value_ and value_.isdigit() and len(value_) == count and ok(value_):
                self.log("digits", keys[0], value_ if count != 4 else "****")
                return value_
            prefix = ["no_answer" if not value_ else bad]
        return None

    # speaking and listening -------------------------------------------------------------------
    async def transcribe(self, pcm: bytes) -> str:
        """Speech to text while a short "one moment" plays, so the line is never silent."""
        job = asyncio.create_task(asyncio.to_thread(self.stt.transcribe, pcm, self.lang))
        if self.stt.real:
            await self.say(["one_moment"])
        try:
            return (await job).strip()
        except Exception:  # never end the call because speech-to-text failed: ask again / use keys
            log.exception("speech-to-text failed")
            return ""

    async def talk(self, parts: list[Part], choices: str = "", labels_key: str | None = None,
                   labels: list[str] | None = None, optional: bool = False,
                   name: str = "") -> tuple[str | None, str]:
        """Ask by voice. The person speaks, or presses / taps one of `choices`.
        -> ("key", k) | ("text", what they said) | (None, "") if nothing usable after two tries."""
        allowed = choices + "09"
        shown = list(labels or (button_labels(labels_key, self.lang) if labels_key else ()))
        name = name or parts[-1].key
        prefix: list[Part] = []
        for _ in range(1 if optional else 2):
            kind, got = await self.ch.talk(prefix + parts, self.lang, allowed, shown, settings.max_speech_seconds)
            if kind == "key":
                if got and len(got) == 1 and got in choices:
                    self.log("key", name, got)
                    return "key", got
                if got == "0":
                    await self.officer_flag(name)
                    prefix = self.parts(["human_flag"])
                    continue
                if got == "9":
                    await self.delete_request()
                    prefix = []
                    continue
                prefix = self.parts(["wrong_key"])
                continue
            text = await self.transcribe(got) if kind == "audio" else (got or "").strip() if kind == "text" else ""
            if text:
                return "text", text
            prefix = self.parts(["didnt_hear"])
        return None, ""

    async def yes_no(self, parts: list[Part], name: str, default: bool = False,
                     yes_words: list[str] | None = None, no_words: list[str] | None = None) -> bool:
        """A yes/no question, answered by voice ("हाँ", "नहीं", ...) or with 1 / 2. If it stays unclear,
        `default` is used (never "yes" to consent), instead of ending the call."""
        prefix: list[Part] = []
        for _ in range(3):
            kind, got = await self.talk(prefix + parts, "12", "yes_no", name=name)
            if kind == "key":
                return got == "1"
            if kind is None:
                break
            yes = parse_yes_no(got)
            if yes is None and yes_words and has(got, yes_words):
                yes = True
            if yes is None and no_words and has(got, no_words):
                yes = False
            if yes is None and len(got.split()) > 2:
                yes = (await asyncio.to_thread(self.llm.label, got, name, self.llm_context(name))).yes_no
            if yes is not None:
                self.log("speech", name, got, {"yes_no": yes})
                return yes
            prefix = self.parts(["wrong_key"]) if self.ch.name == "phone" else self.parts(["didnt_hear"])
        self.log("unclear", name, f"default {default}")
        return default

    def llm_context(self, key: str) -> dict:
        q = BANK.get(key)
        text = T[key][2] if key in T else ""
        if key == "q_lead" and self.lead_sector:
            s = self.data.sectors.get(self.lead_sector)
            text = f"{T['q_lead_pre'][2]} {s.title_en if s else self.lead_sector}. {T['q_lead_post'][2]}"
        return {"question_text": text, "expect": q.expect if q else "their work, wishes and limits",
                "known": self.known_summary()}

    def known_summary(self) -> str:
        pr, occ_ = self.profile, self.data.occupations
        bits = [f"name={pr.name or '?'}", f"age={pr.age or '?'}", f"gender={pr.gender or '?'}",
                f"education={pr.education or '?'}", f"travel_km={pr.radius_km or '?'}",
                "work=" + (", ".join(occ_[c].title_en for c in pr.occupation_codes if c in occ_) or "?"),
                f"years={pr.years if pr.years is not None else '?'}",
                "wants=" + (", ".join(occ_[c].title_en for c in pr.aspiration_codes if c in occ_)
                            or pr.aspiration_sector or "?"),
                f"lean={pr.lean or '?'}", f"health={pr.health if self.health_asked else '?'}"]
        if pr.rejected_sectors or pr.rejected_kinds:
            bits.append("does not want=" + ", ".join(pr.rejected_sectors + pr.rejected_kinds))
        if self.asked:
            bits.append("already asked=" + ", ".join(sorted(self.asked)))
        return "; ".join(bits)

    async def understand(self, question: str, transcript: str, as_aspiration: bool = False,
                         as_family: bool = False) -> Labels:
        labels = await asyncio.to_thread(self.llm.label, transcript, question, self.llm_context(question))
        if as_aspiration and not labels.aspiration_codes:
            labels.aspiration_codes, labels.occupation_codes = labels.occupation_codes, []
        if as_family:
            labels.family_code = labels.family_code or (labels.occupation_codes[0] if labels.occupation_codes else None)
            labels.occupation_codes, labels.aspiration_codes = [], []
        apply(labels, self.profile, transcript)
        if labels.follow_up in BANK and labels.follow_up not in self.asked:
            self.llm_hint = labels.follow_up
        self.log("speech", question, transcript, labels.__dict__)
        await self.respond(labels)
        return labels

    async def respond(self, labels: Labels) -> None:
        """Empathy line the first time a mood shows up; otherwise a short rotating acknowledgement."""
        if labels.mood != "neutral" and labels.mood not in self.empathised:
            self.empathised.add(labels.mood)
            await self.say([f"empathy_{labels.mood}"])
        else:
            await self.ack()

    # returning person ---------------------------------------------------------------------------
    async def returning(self) -> bool:
        hv_id = await self.number(["ask_id"], 9, ok=lambda s: valid_id(s) and self.store.person(s) is not None,
                                  bad="id_not_found", tries=2)
        if not hv_id:
            await self.say(["id_not_found"])
            return False
        for _ in range(3):
            pin = await self.number(["ask_pin"], 4, tries=2)
            result = self.store.check_pin(hv_id, pin or "")
            if result == "ok":
                break
            if result == "locked":
                await self.say(["pin_locked"])
                raise Hangup("PIN locked")
            await self.say(["pin_wrong"])
        else:
            raise Hangup("PIN not entered")
        self.hv_id = hv_id
        person = self.store.person(hv_id)
        self.profile = Profile.from_dict(person["profile"])
        self.profile.language = self.lang
        self.store.audit("caller", "returned", hv_id, self.ch.name)
        saved = self.store.options(hv_id)
        await self.ch.show("person", {"hv_id": pretty(hv_id), "name": person["name"], "options": saved})
        await self.say(["welcome_back"])
        by_id = {c.course_id: c for c in self.data.courses}
        centres = {c.centre_id: c for c in self.data.centres}
        for o in saved:
            course, centre = by_id.get(o["course_id"]), centres.get(o["centre_id"])
            if course and centre:
                await self.say(self.option_parts(o["rank"], course, centre))
        await self.say(["officer_next", "never_money", "goodbye"])
        return True

    # new person ---------------------------------------------------------------------------------
    async def new_person(self) -> None:
        pr = self.profile
        await self.set_location()
        self.asked.add("ask_name")
        await self.ask(BANK["ask_name"])
        if not pr.district:
            await self.ask_pincode()
        kind, story = await self.talk(self.parts(["ask_story"]))
        if story:
            await self.understand("ask_story", story)
        await self.ch.show("profile", self.profile_view())
        await self.guided()
        await self.review()
        # saved now, so nothing is lost if the call drops while hearing the options
        self.hv_id = self.store.create_person(pr.name, pr.district, self.lang, self.ch.name, self.record(),
                                              self.consent)
        self.store.end_session(self.sid, "in progress", self.hv_id)
        await self.say(["thinking"])
        self.options = await asyncio.to_thread(rank, self.data, pr, settings.max_options)
        await self.ask_tradeoff()
        if self.options:
            self.store.save_options(self.sid, self.hv_id, [o.summary() for o in self.options])
        chosen = self.chosen = await self.present_options()
        if chosen:
            self.store.choose(self.hv_id, chosen)
        await self.skill_tips()
        self.store.update_profile(self.hv_id, self.record())
        await self.give_id_and_pin()
        await self.say(["documents", "officer_next", "never_money", "goodbye"])

    def record(self) -> dict:
        return {**self.profile.to_dict(), "skill_advice": self.advice, "question_plan": self.plan_log}

    async def set_location(self) -> None:
        """The location comes from the device: the kiosk's own PIN code (set once on the kiosk), the
        phone line's area, or DEVICE_PINCODE. Only if none is set is the person asked."""
        if hasattr(self.ch, "ready"):
            await self.ch.ready()
        pin = getattr(self.ch, "device_pin", "") or settings.device_pincode
        d = self.data.district_for_pin(pin) if pin else None
        if d:
            self.profile.pin, self.profile.district, self.profile.location_from = pin, d.code, "device"

    async def ask_pincode(self) -> None:
        pin = await self.number(["ask_pincode"], 6, ok=lambda s: self.data.district_for_pin(s) is not None,
                                bad="pincode_unknown")
        if pin:
            self.profile.pin = pin
            self.profile.district = self.data.district_for_pin(pin).code
            self.profile.location_from = "asked"

    # what to ask next: code looks at what is missing, what could change the shortlist, the mood ----
    def mood(self) -> str:
        """The latest mood the LLM heard (hopeful / worried / upset), or neutral."""
        for m in reversed(self.profile.moods[-2:]):
            if m != "neutral":
                return m
        return "neutral"

    def variant(self, key: str) -> str:
        """The wording of a spoken question that fits the mood."""
        mood = self.mood()
        if key == "ask_aspiration":
            return {"hopeful": "ask_aspiration_hope", "worried": "ask_aspiration_soft",
                    "upset": "ask_aspiration_soft"}.get(mood, "ask_aspiration")
        if key == "ask_family":
            return "ask_family_soft" if mood in ("worried", "upset") else "ask_family"
        return key

    def lead_ready(self) -> bool:
        """Time to check the leading kind of work with the person?"""
        s, pr = self.lead_sector, self.profile
        if not s or s in pr.confirmed_sectors or s in pr.rejected_sectors:
            return False
        if self.answers_after_story < self.policy().questions["lead_after"]:
            return False
        wanted = {self.data.occupations[c].sector for c in pr.aspiration_codes if c in self.data.occupations}
        return s != pr.aspiration_sector and s not in wanted  # already what they asked for: no need

    def next_question(self) -> Plan | None:
        pol = self.policy()
        qp = pol.questions
        now = top_ids(self.data, self.profile, qp["top_n"], pol)
        top = rank(self.data, self.profile, 1, policy=pol)
        self.lead_sector = self.data.course_sector(top[0].course) if top else None
        max_f = qp["max_followups"] if self.mood() != "upset" else min(2, qp["max_followups"])
        cands = [q for q in BANK.values() if q.key not in self.asked and q.missing(self) and q.applicable(self)]
        req = [q for q in cands if q.required]
        opt = [q for q in cands if not q.required and self.followups < max_f]
        scores, why = {}, {}
        for q in req + opt:
            v = value(self, q, now)
            hint = q.key == self.llm_hint
            scores[q.key] = v + (qp["llm_hint_bonus"] if hint else 0.0)
            why[q.key] = (("LLM suggested it; " if hint else "") +
                          (f"answer could change the top {qp['top_n']} by {v:.2f}" if q.outcomes(self) else
                           "open question") + ("; required detail" if q.required else ""))
        best_opt = max(opt, key=lambda q: scores[q.key], default=None)
        best_req = max(req, key=lambda q: scores[q.key], default=None)
        if best_opt and scores[best_opt.key] >= qp["min_value"] and (self.last_kind == "slot" or not best_req):
            q = best_opt
        elif best_req:
            q = best_req
        else:
            return None
        return Plan(q, scores[q.key], why[q.key], {k: round(v, 3) for k, v in scores.items()})

    async def guided(self) -> None:
        """Follow-up questions, each building on what the person has said so far."""
        intro = soft = False
        for _ in range(16):
            plan = await asyncio.to_thread(self.next_question)
            if not plan:
                break
            q = plan.question
            self.asked.add(q.key)
            self.plan_log.append({"question": q.key, "score": round(plan.score, 3), "why": plan.why,
                                  "mood": self.mood(), "lead": self.lead_sector})
            self.log("plan", q.key, plan.why, {"scores": plan.scores, "mood": self.mood()})
            if not q.required:
                self.followups += 1
                if not intro and q.kind == "probe":
                    intro = True
                    await self.say(["follow_intro"])
            elif not soft and self.mood() in ("worried", "upset"):
                soft = True
                await self.say(["keys_soft_intro"])
            await self.ask(q)
            self.last_kind = "slot" if q.kind == "slot" else "probe"
            self.answers_after_story += 1
            await self.ch.show("profile", self.profile_view())

    def question_parts(self, q: Question) -> list[Part]:
        if q.key == "q_lead":
            s = sector(self.lead_sector or "", self.lang, self.data)
            return self.parts(["q_lead_pre"]) + ([s] if s else []) + self.parts(["q_lead_post"])
        parts = self.parts([self.variant(q.key)])
        work = occ(self.profile.occupation_codes[0], self.lang, self.data) if self.profile.occupation_codes else None
        if work and q.key in ("q_goal", "q_certificate", "q_years"):  # build on what they said
            parts = self.parts(["q_ctx_work"]) + [work] + parts
        if q.choices == "12" and self.ch.name == "phone" and q.key != "q_lead":
            parts += self.parts(["or_press_12"])
        return parts

    async def ask(self, q: Question) -> bool:
        """Ask one question by voice and apply the answer. Short answers are read by the rules in a
        millisecond; longer ones go to the LLM (with what is known so far). Unclear twice: keypad."""
        kind, got = await self.talk(self.question_parts(q), q.choices, q.labels,
                                    optional=q.kind == "open", name=q.key)
        ok = False
        if kind == "key" and q.from_key:
            ok = q.from_key(self, got)
        elif kind == "text":
            if q.from_text and q.short_ok and len(got.split()) <= q.short_words:
                ok = q.from_text(self, got, None)
                if ok:
                    self.log("speech", q.key, got, {"read_by": "rules"})
                    await self.ack()
            if not ok:
                labels = await self.understand(q.key, got, as_aspiration=q.key == "ask_aspiration",
                                               as_family=q.key == "ask_family")
                ok = q.from_text(self, got, labels) if q.from_text else True
        # not understood: the keypad version, if the person said something unclear or the detail is
        # required; an optional question met with silence is simply skipped
        if not ok and q.keypad and (kind is not None or q.required):
            ok = await self.keypad_fallback(q)
        return ok

    async def keypad_fallback(self, q: Question) -> bool:
        if q.key == "say_age":
            age = await self.number(["ask_age"], 2, ok=lambda s: 14 <= int(s) <= 80)
            if age:
                self.profile.age = int(age)
            return bool(age)
        if q.from_key and q.choices:
            key = await self.choice(self.parts([q.keypad]), q.choices, fatal=q.required)
            return q.from_key(self, key) if key else False
        return False

    # the review: everything understood, shown and read back, any detail can be corrected ----------
    def review_view(self) -> dict:
        pr = self.profile
        d = self.data.districts.get(pr.district or "")
        occ_ = self.data.occupations
        edu = dict(zip(EDU_KEYS.values(), button_labels("say_education", self.lang)))
        gen = dict(zip(GENDER_KEYS.values(), button_labels("say_gender", self.lang)))
        return {"name": pr.name, "age": pr.age, "gender": gen.get(pr.gender or "", ""),
                "education": edu.get(pr.education or "", ""),
                "travel_km": round(radius(pr, self.policy())), "hostel_ok": pr.hostel_ok,
                "cannot_leave_home": pr.cannot_leave_home,
                "work": [occ_[c].title(self.lang) for c in pr.occupation_codes if c in occ_], "years": pr.years,
                "wants": [occ_[c].title(self.lang) for c in pr.aspiration_codes if c in occ_]
                or ([self.data.sectors[pr.aspiration_sector].title(self.lang)]
                    if pr.aspiration_sector in self.data.sectors else []),
                "health": dict(zip(("none", "some", "severe"), button_labels("say_health", self.lang))).get(pr.health, ""),
                "lean": pr.lean, "max_weeks": pr.max_weeks,
                "district": d.name(self.lang) if d else "", "location_from": pr.location_from,
                "labels": dict(zip(REVIEW_FIELDS.values(), button_labels("review_which", self.lang)))}

    def review_parts(self) -> list[Part]:
        pr, lang = self.profile, self.lang
        out = self.parts(["review_intro"])
        if pr.age:
            out += [p("rv_age_pre", lang), num(pr.age, lang), p("rv_age_post", lang)]
        if pr.education:
            out += [p("rv_edu", lang), p(f"edu_{pr.education}", lang)]
        out += [p("rv_travel_pre", lang), num(round(radius(pr, self.policy())), lang), p("rv_travel_post", lang)]
        if pr.hostel_ok and not pr.cannot_leave_home:
            out.append(p("rv_hostel", lang))
        if pr.health in ("some", "severe"):
            out.append(p(f"rv_health_{pr.health}", lang))
        work = [x for x in (occ(c, lang, self.data) for c in pr.occupation_codes[:2]) if x]
        if work:
            out += [p("rb_work", lang)] + work
            if pr.years:
                pre = p("years_pre", lang)
                out += ([pre] if pre.text else []) + [num(pr.years, lang), p("years_post", lang)]
        want = [x for x in (occ(c, lang, self.data) for c in pr.aspiration_codes[:1]) if x]
        if not want and pr.aspiration_sector:
            want = [x for x in [sector(pr.aspiration_sector, lang, self.data)] if x]
        if want:
            out += [p("rb_want", lang)] + want
        if pr.cannot_leave_home:
            out.append(p("rb_home", lang))
        return out

    async def review(self) -> None:
        for _ in range(4):
            await self.ch.show("review", self.review_view())
            if await self.yes_no(self.review_parts() + self.parts(["review_ok"]), "review_ok", default=True):
                self.log("review", "review_ok", "confirmed")
                return
            field = None
            for _ in range(2):
                kind, got = await self.talk(self.parts(["review_which"]), "1234567", "review_which", name="review_which")
                if kind == "key":
                    field = REVIEW_FIELDS.get(got)
                elif kind == "text":
                    field = next((f for f, words in REVIEW_WORDS.items() if has(got, words)), None)
                    if not field:
                        n = [v for v, _ in numbers(got) if 1 <= v <= 7]
                        field = REVIEW_FIELDS.get(str(n[0])) if n else None
                if field or kind is None:
                    break
            if not field:
                continue  # read it back again
            self.log("review", "review_which", field)
            await self.correct(field)

    async def correct(self, field: str) -> None:
        pr = self.profile
        if field == "work":
            kind, story = await self.talk(self.parts(["review_work"]))
            if story:
                pr.occupation_codes, pr.aspiration_codes, pr.aspiration_sector, pr.years = [], [], None, None
                await self.understand("ask_story", story)
            return
        key = {"name": "ask_name", "age": "say_age", "education": "say_education", "travel": "say_travel",
               "gender": "say_gender", "health": "say_health"}[field]
        attrs = {"name": ["name"], "age": ["age"], "education": ["education"], "gender": ["gender"],
                 "health": ["health"], "travel": ["radius_km", "hostel_ok", "cannot_leave_home"]}[field]
        old = {a: getattr(pr, a) for a in attrs}
        blank = {"name": "", "health": "none", "cannot_leave_home": False}
        for a in attrs:  # forget the old answer (also "cannot leave home", or travel could never change)
            setattr(pr, a, blank.get(a))
        if not await self.ask(BANK[key]):  # nothing understood: keep what we had
            for a, v in old.items():
                setattr(pr, a, v)

    def profile_view(self) -> dict:
        pr = self.profile
        d = self.data.districts.get(pr.district or "")
        return {"name": pr.name, "age": pr.age, "district": d.name_en if d else None,
                "work": [self.data.occupations[c].title_en for c in pr.occupation_codes if c in self.data.occupations],
                "wants": [self.data.occupations[c].title_en for c in pr.aspiration_codes if c in self.data.occupations]
                or ([pr.aspiration_sector] if pr.aspiration_sector else []),
                "years": pr.years, "radius_km": round(radius(pr, self.policy())) if pr.radius_km or pr.evidence else None,
                "cannot_leave_home": pr.cannot_leave_home, "education": pr.education, "gender": pr.gender,
                "education_label": dict(zip(EDU_KEYS.values(), button_labels("say_education", self.lang))).get(
                    pr.education or "", ""),
                "lead_label": self.data.sectors[self.lead_sector].title(self.lang)
                if self.lead_sector in self.data.sectors else "",
                "health": pr.health, "lean": pr.lean, "evidence": pr.evidence, "lead": self.lead_sector,
                "rejected": pr.rejected_sectors + pr.rejected_kinds,
                "emphasis": {k: f"{label_for(m)} ×{m:.2f}" for k, m in multipliers(pr, self.policy()).items()
                             if abs(m - 1) > 0.05}}

    def policy(self):
        return POLICIES.active().for_district(self.profile.district)

    async def ask_tradeoff(self) -> None:
        """When the top two options pull in opposite directions, ask which matters more, then re-rank."""
        pol = self.policy()
        for _ in range(pol.tradeoff["max_questions"]):
            pair = tradeoff(self.options, pol)
            if not pair:
                return
            fa, fb = pair
            parts = self.parts(["tradeoff_q", f"tf_{fa}", "tf_press_1", f"tf_{fb}", "tf_press_2"])
            kind, got = await self.talk(parts, "12", labels=[parts[1].text, parts[3].text])
            pick = got if kind == "key" else None
            if kind == "text":
                a, b = has(got, TRADEOFF_WORDS[fa]), has(got, TRADEOFF_WORDS[fb])
                pick = "1" if a and not b else "2" if b and not a else None
                if pick is None:
                    n = [v for v, _ in numbers(got) if v in (1, 2)]
                    pick = str(n[0]) if n else None
            if pick is None:  # unclear: no evidence, keep the ranking as it is
                self.log("tradeoff", f"{fa} vs {fb}", "unclear")
                return
            win, lose = (fa, fb) if pick == "1" else (fb, fa)
            add_tradeoff(self.profile, win, lose, pick)
            self.log("tradeoff", f"{fa} vs {fb}", win)
            self.options = await asyncio.to_thread(rank, self.data, self.profile, settings.max_options)

    # options ------------------------------------------------------------------------------------
    def option_parts(self, rank_no: int, course, centre) -> list[Part]:
        lang = self.lang
        out = [p("option_word", lang), num(rank_no, lang), p(f"kind_{course.kind}", lang)]
        mine = [c for c in course.nco_codes if c in self.profile.occupation_codes + self.profile.aspiration_codes]
        if course.kind == "certificate" and course.nco_codes:
            x = occ(course.nco_codes[0], lang, self.data)
        elif course.kind == "startup":  # toolkit / own-work courses cover many trades: name theirs, if any
            x = occ(mine[0], lang, self.data) if mine else None
        else:
            x = sector(self.data.course_sector(course), lang, self.data)
        if x:
            out.append(x)
        out += [p(f"ctype_{centre.type}", lang), p("km_pre", lang), num(centre.distance_km, lang),
                p("km_post", lang), num(max(1, round(course.hours / 40)), lang), p("weeks_post", lang)]
        if course.fee_inr == 0:
            out.append(p("free", lang))
        return out

    def _option_pick(self, text: str, n: int) -> str | None:
        if has(text, AGAIN_WORDS):
            return "8"
        for i, words in ORDINAL_WORDS.items():
            if i <= n and has(text, words):
                return str(i)
        nums = [v for v, _ in numbers(text) if 1 <= v <= n]
        return str(nums[0]) if nums else None

    async def present_options(self) -> int | None:
        if not self.options:
            await self.say(["no_options"])
            return None
        await self.ch.show("options", {"items": [o.summary() for o in self.options]})
        listing = self.parts(["options_intro"])
        for i, o in enumerate(self.options, 1):
            listing += self.option_parts(i, o.course, o.centre)
        n = len(self.options)
        allowed = "".join(str(i) for i in range(1, n + 1)) + "8"
        names = [o.course.title_en for o in self.options]
        prompt = listing
        for _ in range(4):
            kind, got = await self.talk(prompt + self.parts(["choose_prompt"]), allowed,
                                        labels=names + [{"hi": "सब फिर से", "mr": "सगळे पुन्हा"}.get(self.lang, "Again")])
            key = got if kind == "key" else self._option_pick(got, n) if kind == "text" else None
            if kind == "text":
                self.log("speech", "choose_prompt", got, {"picked": key})
            if key is None:
                key = await self.choice(self.parts(["choose_prompt"]), allowed, fatal=False, tries=2)
                if key is None:
                    return None  # no choice made; the options are saved and the officer follows up
            if key == "8":
                prompt = listing
                continue
            o = self.options[int(key) - 1]
            detail = self.option_parts(int(key), o.course, o.centre) + self.parts(["why_intro"])
            detail += self.parts([f"reason_{r}" for r in o.reasons])
            if o.skill_gap:
                detail += self.parts(["new_skills"])
            await self.ch.show("detail", {"rank": int(key), **o.summary()})
            if await self.yes_no(detail + self.parts(["confirm_choice"]), "confirm_choice", default=True):
                await self.say(["chosen"])
                return int(key)
            prompt = []
        return None

    async def skill_tips(self) -> None:
        """Skills worth learning: small or moderate gaps that lead to better pay or a higher level."""
        self.advice = await asyncio.to_thread(skill_advice, self.data, self.profile, self.policy())
        if not self.advice:
            return
        await self.ch.show("skills", {"items": self.advice})
        top = self.advice[0]
        parts = self.parts(["skill_tip_pre"])
        x = sector(top["sector"], self.lang, self.data)
        if x:
            parts.append(x)
        parts += self.parts(["skill_tip_mid"]) + [num(top["weeks"], self.lang)] + self.parts(["weeks_word", "skill_tip_post"])
        await self.say(parts)
        self.log("skills", "skill_tip", ", ".join(top["skills"]))

    def make_card(self) -> str:
        d = self.data.districts.get(self.profile.district or "")
        chosen = self.options[self.chosen - 1].course.title_en if self.chosen else ""
        skills = self.advice[0]["skills"][:3] if self.advice else []
        svg = card_svg(self.hv_id, self.profile.name, d.name_en if d else "", chosen, skills)
        save_card(self.hv_id, svg)
        self.store.audit("system", "card_created", self.hv_id, self.ch.name)
        return svg

    async def give_id_and_pin(self) -> None:
        spoken = digits(self.hv_id, self.lang)
        await self.say(self.parts(["your_id"]) + spoken + self.parts(["once_more"]) + spoken +
                       self.parts(["write_down"]))
        for _ in range(3):  # the PIN is typed, never spoken: anyone nearby could hear it
            first = await self.number(["set_pin"], 4, ok=valid_pin, tries=2)
            second = await self.number(["set_pin_again"], 4, ok=valid_pin, tries=2) if first else None
            if first and first == second:
                self.store.set_pin(self.hv_id, first)
                await self.say(["pin_saved"])
                break
            await self.say(["pin_mismatch"])
        d = self.data.districts.get(self.profile.district or "")
        svg = self.make_card()
        await self.ch.show("card", {"hv_id": pretty(self.hv_id), "raw_id": self.hv_id, "name": self.profile.name,
                                    "district": d.name(self.lang) if d else "", "language": self.lang,
                                    "svg": svg, "skills": self.advice})
        if self.ch.can_type:
            await self.say(["card_ready"])
