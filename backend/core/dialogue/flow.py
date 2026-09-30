"""The keypad interview as a pure state machine, independent of any telephony provider.

An adapter (Exotel WebSocket, Plivo XML, the simulator) asks for the next action, carries it
out, and feeds back what happened: a key, a timeout, or a finished recording. Every reply
comes with a list of effects for the adapter to persist. Nothing here touches I/O.

Rules from the build spec:
- the call starts with the language menu (P05, one line per language; skipped when only one is
  offered); the greeting (P01) and everything after it play in the chosen language;
- every question waits `timeout` seconds; after a timeout (P16 "no answer") or a wrong key
  (P29 "that key is not an option") it asks the same question again, as often as needed: the
  call never skips a question and never hangs up for lack of an answer (the language menu just
  plays again, because no language is chosen yet);
- 9 at any menu deletes the caller's data, blocks the number, plays P18 and hangs up;
- the PIN code question (P31) collects up to 6 digits ended by # (a wrong entry is asked again
  with P32, like any other question); the caller may press * to skip it. 9 and 0 are ordinary
  digits there, so they do not delete or flag while a PIN is typed;
- 0 at any menu flags the call for a human (P19) and repeats the question;
- silence at the greeting plays P02 ("can you hear us? press 1; press 9 if you did not call"),
  then P16 + P02 until the caller answers or hangs up;
- after the work story the caller hears what we heard (P21) and up to three occupations we
  think it is (P13: keys 1-3, the next key = none of these); if the story was unclear or too
  short, or none is right, they tell it again in more detail (P23), up to MAX_STORY_ATTEMPTS
  tries in all, then choose from the keypad trade list (P14);
- once the occupation is known the interview asks for the training / livelihood options
  (`Offer`): the adapter runs the recommender and calls `on_options`. With options, P34 says
  what we noted and the options (keys 1-3, the next key = none of these), then P33 says goodbye;
  with none (or if their voice cannot be made), the call ends with the summary (P15);
- with `review`, after the keypad questions the caller hears what we saved (P35, one piece per
  answer, P36): 1 = all correct, 2 = change something (P37 names each answer with its key),
  then that one question is asked again and the review repeats;
- with `closing`, the call ends with the reference number said twice ("REF", filled in by the
  adapter), where to go and the documents to take (P39).
"""

from dataclasses import asdict, dataclass, field, fields

from core.dialogue.prompts import LANGUAGE_KEYS, in_language
from core.geo import valid_pin

GLOBAL_KEYS = "90"
MAX_STORY_ATTEMPTS = 3


@dataclass(frozen=True)
class Ask:
    step: str
    prompts: tuple[str, ...]
    valid: str
    timeout: int
    digits: int = 0  # > 0: collect up to this many digits (ended by #) and answer with on_digits


@dataclass(frozen=True)
class Record:
    step: str
    prompts: tuple[str, ...]
    max_seconds: int = 60
    finish_key: str = "#"


@dataclass(frozen=True)
class Hangup:
    prompts: tuple[str, ...] = ()


@dataclass(frozen=True)
class Offer:
    """Find the caller's options now, then call `Interview.on_options`."""

    step: str = "offer"


Action = Ask | Record | Hangup | Offer


@dataclass(frozen=True)
class Effect:
    kind: str
    data: dict = field(default_factory=dict)


EDUCATION = {
    "1": "none",
    "2": "upto_5th",
    "3": "upto_8th",
    "4": "10th",
    "5": "12th",
    "6": "iti_or_diploma",
    "7": "graduate",
}
TRAVEL = {"1": "village", "2": "10km", "3": "30km", "4": "district_hq", "5": "hostel"}
LEAN = {"1": "job", "2": "own_work", "3": "unsure"}
TRADES = {"1": "9211", "2": "7531", "3": "7411", "4": "7112", "5": "7422"}
AGE = {"1": "under_18", "2": "18_25", "3": "26_35", "4": "36_45", "5": "46_60", "6": "over_60"}
GENDER = {"1": "female", "2": "male", "3": "other", "4": "not_said"}
PHYSICAL = {"1": "none", "2": "some"}
PIN_DIGITS = 6

# step -> (prompt, key -> value, next step); q_lean's next step depends on the recording consent
QUESTIONS = {
    "q_age": ("P25", AGE, "q_gender"),
    "q_gender": ("P26", GENDER, "q_education"),
    "q_education": ("P09", EDUCATION, "q_travel"),
    "q_travel": ("P10", TRAVEL, "q_physical"),
    "q_physical": ("P27", PHYSICAL, "q_pin"),
    "q_lean": ("P11", LEAN, None),
    "trades": ("P14", TRADES, "summary"),
}
# key in the change menu (P37) -> the question asked again
CHANGE = {
    "1": "q_age",
    "2": "q_gender",
    "3": "q_education",
    "4": "q_travel",
    "5": "q_physical",
    "6": "q_pin",
    "7": "q_lean",
}
REVIEWED = ("q_age", "q_gender", "q_education", "q_travel", "q_physical")
CLOSING = ("REF", "P39")  # REF: "your reference number is ... once more ..." (see the adapter)

CONSENTS = {
    "consent_recording": ("P06", "recording", "consent_share"),
    "consent_share": ("P07", "share", "consent_research"),
    "consent_research": ("P08", "research", "q_age"),
}


@dataclass
class Interview:
    languages: list[str] = field(default_factory=lambda: ["hi-IN"])
    timeout: int = 8
    state: str = "language"
    attempts: int = 0
    opening_warned: bool = False
    keypad_only: bool = False
    language: str = "hi-IN"
    readback_prompts: list[str] = field(default_factory=list)
    candidates: list[str] = field(default_factory=list)
    story_attempts: int = 0
    education: str = ""
    occupation: str = ""
    answers: dict = field(default_factory=dict)  # step -> value, for the recommender
    options: list[str] = field(default_factory=list)  # course ids said on the call
    options_prompts: list[str] = field(default_factory=list)
    review: bool = False  # read the answers back and let the caller change one
    closing: bool = False  # reference number + where to go + documents at the end
    changing: bool = False  # answering a question again from the review

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Interview":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    def _menu(self) -> dict[str, str]:
        """Key -> language for the languages on offer (keys stay fixed: Marathi is always 3)."""
        return {k: code for k, code in LANGUAGE_KEYS.items() if code in self.languages}

    def start(self) -> Action:
        return self._goto(self.state)

    def on_key(self, digit: str) -> tuple[Action, list[Effect]]:
        if self.state in ("ended", "story", "offer"):
            return self._action(), []
        if self.state == "q_pin":
            return self.on_digits(digit)
        if digit == "9":
            self.state = "ended"
            return Hangup(("P18",)), [Effect("delete_and_block")]
        if digit == "0":
            return self._action(prefix=("P19",)), [Effect("human_flag", {"step": self.state})]

        if self.state == "opening":
            return (self._goto("safe_to_talk"), []) if digit == "1" else self._invalid(True)

        if self.state == "safe_to_talk":
            if digit == "1":
                return self._goto("consent_recording"), []
            if digit == "2":
                self.state = "ended"
                return Hangup(("P04",)), [Effect("callback_tomorrow")]
            return self._invalid(wrong_key=True)

        if self.state == "language":
            choices = self._menu()
            if digit not in choices:
                return self._invalid(wrong_key=True)
            self.language = choices[digit]
            return self._goto("opening"), [Effect("language", {"code": self.language})]

        if self.state == "readback":
            return self._readback(digit)

        if self.state == "options":
            return self._choose(digit)

        if self.state == "review":
            if digit == "1":
                return self._after_profile(), [Effect("review", {"ok": True})]
            if digit == "2":
                return self._goto("change"), []
            return self._invalid(wrong_key=True)

        if self.state == "change":
            if digit not in CHANGE:
                return self._invalid(wrong_key=True)
            self.changing = True
            return self._goto(CHANGE[digit]), [Effect("review", {"change": CHANGE[digit]})]

        if self.state in CONSENTS:
            if digit not in "12":
                return self._invalid(wrong_key=True)
            return self._consent(granted=digit == "1")

        if self.state in QUESTIONS:
            prompt, options, _ = QUESTIONS[self.state]
            if digit not in options:
                return self._invalid(wrong_key=True)
            step = self.state
            if step == "q_education":
                self.education = options[digit]
            elif step == "trades":
                self.occupation = options[digit]
            self.answers[step] = options[digit]
            effect = Effect("answer", {"step": step, "key": digit, "value": options[digit]})
            return self._after_question(step), [effect]

        return self._action(), []

    def on_digits(self, entry: str) -> tuple[Action, list[Effect]]:
        """The whole PIN code entry ("*" skips it); anything but 6 digits is asked again."""
        if self.state != "q_pin":
            return self._action(), []
        if entry == "*":
            self.answers["q_pin"] = "skipped"
            return self._after_question("q_pin"), [Effect("skipped", {"step": "q_pin"})]
        if not valid_pin(entry):
            self.attempts += 1
            return self._action(prefix=("P32",)), []
        self.answers["q_pin"] = entry
        effect = Effect("answer", {"step": "q_pin", "key": "", "value": entry})
        return self._after_question("q_pin"), [effect]

    def on_options(
        self, courses: list[str], prompts: list[str] | tuple[str, ...], details: list[dict]
    ) -> tuple[Action, list[Effect]]:
        """After `Offer`: the recommended course ids (best first), the prompts that say them,
        and their details for the database. No courses or no prompts: end with the summary."""
        if self.state != "offer":
            return self._action(), []
        spoken = bool(courses and prompts)
        effects = [Effect("recommendations", {"options": details, "spoken": spoken})]
        if not spoken:
            self.state = "ended"
            return Hangup(("P15", *self._closing())), effects if details else []
        self.options, self.options_prompts = list(courses)[:3], list(prompts)
        return self._goto("options"), effects

    def _choose(self, digit: str) -> tuple[Action, list[Effect]]:
        none_key = str(len(self.options) + 1)
        if digit == none_key:
            rank, course = None, None
        elif digit.isdigit() and 1 <= int(digit) <= len(self.options):
            rank, course = int(digit), self.options[int(digit) - 1]
        else:
            return self._invalid(wrong_key=True)
        self.answers["interest"] = course or "none"
        self.state = "ended"
        return Hangup(("P33", *self._closing())), [
            Effect("interest", {"rank": rank, "course_id": course}),
            Effect("answer", {"step": "interest", "key": digit, "value": course or "none"}),
        ]

    def on_timeout(self) -> tuple[Action, list[Effect]]:
        if self.state == "opening" and not self.opening_warned:
            self.opening_warned = True  # first silence: "can you hear us?" (P02)
            return self._action(), []
        return self._invalid()

    def on_recording(
        self,
        path: str | None,
        seconds: float,
        candidates: list[str] | None = None,
        readback: list[str] | tuple[str, ...] | None = None,
        details: dict | None = None,
        heard: list[str] | tuple[str, ...] = (),
        understood: bool = True,
    ) -> tuple[Action, list[Effect]]:
        """After the story.

        `heard` plays back what we heard (P21), `readback` asks about the top two occupations.
        `understood` is False when the story could not be processed in time (not the caller's
        fault), so the caller is not asked to tell it again.
        """
        if self.state != "story":
            return self._action(), []
        self.story_attempts += 1
        again = "story" if self.story_attempts < MAX_STORY_ATTEMPTS else "trades"
        if not path:
            return self._goto(again, ("P22",)), [Effect("story_empty")]
        data = {"path": path, "seconds": round(seconds, 1), **(details or {})}
        effects = [Effect("story_recorded", data)]
        if candidates and readback:
            self.candidates = list(candidates)[:3]
            self.readback_prompts = list(heard) + list(readback)
            return self._goto("readback"), effects
        if not understood:
            return self._goto("trades"), effects
        unclear = tuple(heard) + ("P24",) if heard else ("P22",)
        return self._goto(again, unclear), effects

    def _none_key(self) -> str:
        return str(len(self.candidates) + 1)

    def _readback(self, digit: str) -> tuple[Action, list[Effect]]:
        choice = int(digit) - 1 if digit.isdigit() and digit != "0" else None
        if digit == self._none_key():
            effect = Effect(
                "readback", {"key": digit, "confirmed": None, "candidates": self.candidates}
            )
            again = self.story_attempts < MAX_STORY_ATTEMPTS
            return self._goto("story" if again else "trades"), [effect]
        if choice is None or not 0 <= choice < len(self.candidates):
            return self._invalid(wrong_key=True)
        code = self.candidates[choice]
        self.occupation = code
        self.answers["occupation"] = code
        return self._goto("summary"), [
            Effect("readback", {"key": digit, "confirmed": code, "candidates": self.candidates}),
            Effect("answer", {"step": "occupation", "key": digit, "value": code}),
        ]

    def _invalid(self, wrong_key: bool = False) -> tuple[Action, list[Effect]]:
        """No key or a wrong key: say so and ask the same question again, however many times."""
        self.attempts += 1
        if self.state == "language":  # no language yet: just play the menu again
            return self._action(), []
        return self._action(prefix=("P29",) if wrong_key else ("P16",)), []

    def _consent(self, granted: bool) -> tuple[Action, list[Effect]]:
        prompt, kind, nxt = CONSENTS[self.state]
        effects = [Effect("consent", {"kind": kind, "granted": granted, "prompt_id": prompt})]
        if kind == "recording" and not granted:
            self.keypad_only = True
            effects.append(Effect("keypad_only"))
        return self._goto(nxt), effects

    def _closing(self) -> tuple[str, ...]:
        return CLOSING if self.closing else ()

    def _after_profile(self) -> Action:
        """After the keypad questions (and their review): the spoken story or the trade list."""
        return self._goto("trades" if self.keypad_only else "story")

    def review_pieces(self) -> tuple[str, ...]:
        """One short prerendered piece per saved answer, in the order they were asked."""
        pieces = [f"V_{step}_{self.answers[step]}" for step in REVIEWED if step in self.answers]
        pin = self.answers.get("q_pin", "")
        if valid_pin(pin):
            pieces += ["V_pin", *(f"D{d}" for d in pin)]
        else:
            pieces.append("V_pin_none")
        if "q_lean" in self.answers:
            pieces.append(f"V_q_lean_{self.answers['q_lean']}")
        return tuple(pieces)

    def _after_question(self, step: str) -> Action:
        if self.changing:  # answered again from the review: back to the review
            self.changing = False
            return self._goto("review")
        if step == "q_lean":
            return self._goto("review") if self.review else self._after_profile()
        if step == "q_pin":
            return self._goto("q_lean")
        return self._goto(QUESTIONS[step][2])

    def _goto(self, state: str, prefix: tuple[str, ...] = ()) -> Action:
        self.state = state
        self.attempts = 0
        if state == "language" and len(self._menu()) < 2:
            menu = self._menu()
            if menu:
                self.language = next(iter(menu.values()))
            return self._goto("opening", prefix)
        if state == "summary":  # the occupation is known: look for options first
            self.state = "offer"
            return Offer()
        if state == "q_age" and not self.changing:  # why we ask, said once before the first
            prefix = prefix + ("P28",)
        return self._action(prefix)

    def _action(self, prefix: tuple[str, ...] = ()) -> Action:
        s = self.state
        if s == "opening":
            if self.opening_warned:
                return Ask(s, prefix + ("P02",), "1" + GLOBAL_KEYS, self.timeout)
            return Ask(s, prefix + ("P01",), "1" + GLOBAL_KEYS, self.timeout)
        if s == "safe_to_talk":
            return Ask(s, prefix + ("P03",), "12" + GLOBAL_KEYS, self.timeout)
        if s == "language":
            menu = self._menu()
            lines = tuple(in_language("P05", code) for code in menu.values())
            return Ask(s, prefix + lines, "".join(menu) + GLOBAL_KEYS, self.timeout)
        if s in CONSENTS:
            return Ask(s, prefix + (CONSENTS[s][0],), "12" + GLOBAL_KEYS, self.timeout)
        if s == "q_pin":
            valid = "0123456789*#"
            return Ask(s, prefix + ("P31",), valid, self.timeout, digits=PIN_DIGITS)
        if s in QUESTIONS:
            prompt, options, _ = QUESTIONS[s]
            return Ask(s, prefix + (prompt,), "".join(options) + GLOBAL_KEYS, self.timeout)
        if s == "story":
            return Record(s, prefix + ("P12" if self.story_attempts == 0 else "P23",))
        if s == "review":
            prompts = prefix + ("P35", *self.review_pieces(), "P36")
            return Ask(s, prompts, "12" + GLOBAL_KEYS, self.timeout)
        if s == "change":
            return Ask(s, prefix + ("P37",), "".join(CHANGE) + GLOBAL_KEYS, self.timeout)
        if s == "offer":
            return Offer()
        if s == "options":
            valid = "123"[: len(self.options)] + str(len(self.options) + 1)
            return Ask(s, prefix + tuple(self.options_prompts), valid + GLOBAL_KEYS, self.timeout)
        if s == "readback":
            valid = "123"[: len(self.candidates)] + self._none_key()
            prompts = prefix + tuple(self.readback_prompts)
            return Ask(s, prompts, valid + GLOBAL_KEYS, self.timeout)
        return Hangup()
