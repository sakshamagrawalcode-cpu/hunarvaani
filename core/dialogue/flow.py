"""The keypad interview as a pure state machine, independent of any telephony provider.

An adapter (Exotel WebSocket, Plivo XML, the simulator) asks for the next action, carries it
out, and feeds back what happened: a key, a timeout, or a finished recording. Every reply
comes with a list of effects for the adapter to persist. Nothing here touches I/O.

Rules from the build spec:
- every question waits `timeout` seconds; after a timeout or a wrong key it plays P16 and asks
  once more, then records "skipped" and moves on (a skipped consent counts as "no");
- 9 at any menu deletes the caller's data, blocks the number, plays P18 and hangs up;
- 0 at any menu flags the call for a human (P19) and repeats the question;
- silence at the opening plays P02 once ("press 9 if you did not call"), then hangs up;
- right after the opening the caller picks a language (skipped when only one is offered);
  every later prompt plays in that language.
"""

from dataclasses import asdict, dataclass, field, fields

from core.dialogue.prompts import LANGUAGE_KEYS, in_language

GLOBAL_KEYS = "90"


@dataclass(frozen=True)
class Ask:
    step: str
    prompts: tuple[str, ...]
    valid: str
    timeout: int


@dataclass(frozen=True)
class Record:
    step: str
    prompts: tuple[str, ...]
    max_seconds: int = 60
    finish_key: str = "#"


@dataclass(frozen=True)
class Hangup:
    prompts: tuple[str, ...] = ()


Action = Ask | Record | Hangup


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

QUESTIONS = {
    "q_education": ("P09", EDUCATION, "q_travel"),
    "q_travel": ("P10", TRAVEL, "q_lean"),
    "q_lean": ("P11", LEAN, None),
    "trades": ("P14", TRADES, "summary"),
}
CONSENTS = {
    "consent_recording": ("P06", "recording", "consent_share"),
    "consent_share": ("P07", "share", "consent_research"),
    "consent_research": ("P08", "research", "q_education"),
}


@dataclass
class Interview:
    languages: list[str] = field(default_factory=lambda: ["hi-IN"])
    timeout: int = 8
    state: str = "opening"
    attempts: int = 0
    opening_warned: bool = False
    keypad_only: bool = False
    language: str = "hi-IN"
    readback_prompt: str = ""
    candidates: list[str] = field(default_factory=list)
    education: str = ""
    occupation: str = ""

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
        return self._action()

    def on_key(self, digit: str) -> tuple[Action, list[Effect]]:
        if self.state in ("ended", "story"):
            return self._action(), []
        if digit == "9":
            self.state = "ended"
            return Hangup(("P18",)), [Effect("delete_and_block")]
        if digit == "0":
            return self._action(prefix=("P19",)), [Effect("human_flag", {"step": self.state})]

        if self.state == "opening":
            return (self._goto("language"), []) if digit == "1" else self.on_timeout()

        if self.state == "safe_to_talk":
            if digit == "1":
                return self._goto("consent_recording"), []
            if digit == "2":
                self.state = "ended"
                return Hangup(("P04",)), [Effect("callback_tomorrow")]
            return self._invalid()

        if self.state == "language":
            choices = self._menu()
            if digit not in choices:
                return self._invalid()
            self.language = choices[digit]
            return self._goto("safe_to_talk"), [Effect("language", {"code": self.language})]

        if self.state == "readback":
            return self._readback(digit)

        if self.state in CONSENTS:
            if digit not in "12":
                return self._invalid()
            return self._consent(granted=digit == "1")

        if self.state in QUESTIONS:
            prompt, options, _ = QUESTIONS[self.state]
            if digit not in options:
                return self._invalid()
            step = self.state
            if step == "q_education":
                self.education = options[digit]
            elif step == "trades":
                self.occupation = options[digit]
            effect = Effect("answer", {"step": step, "key": digit, "value": options[digit]})
            return self._after_question(step), [effect]

        return self._action(), []

    def on_timeout(self) -> tuple[Action, list[Effect]]:
        if self.state == "opening":
            if not self.opening_warned:
                self.opening_warned = True
                return self._action(), []
            self.state = "ended"
            return Hangup(), [Effect("no_response")]
        return self._invalid()

    def on_recording(
        self,
        path: str | None,
        seconds: float,
        candidates: list[str] | None = None,
        prompt: str | None = None,
        details: dict | None = None,
    ) -> tuple[Action, list[Effect]]:
        """After the story: read back the top two occupations if the search was confident."""
        if self.state != "story":
            return self._action(), []
        if not path:
            return self._goto("trades"), [Effect("story_empty")]
        data = {"path": path, "seconds": round(seconds, 1), **(details or {})}
        effects = [Effect("story_recorded", data)]
        if candidates and prompt:
            self.candidates = list(candidates)[:2]
            self.readback_prompt = prompt
            return self._goto("readback"), effects
        return self._goto("trades"), effects

    def _readback(self, digit: str) -> tuple[Action, list[Effect]]:
        choice = {"1": 0, "2": 1}.get(digit)
        if digit == "3":
            effect = Effect(
                "readback", {"key": "3", "confirmed": None, "candidates": self.candidates}
            )
            return self._goto("trades"), [effect]
        if choice is None or choice >= len(self.candidates):
            return self._invalid()
        code = self.candidates[choice]
        self.occupation = code
        return self._goto("summary"), [
            Effect("readback", {"key": digit, "confirmed": code, "candidates": self.candidates}),
            Effect("answer", {"step": "occupation", "key": digit, "value": code}),
        ]

    def _invalid(self) -> tuple[Action, list[Effect]]:
        if self.attempts == 0:
            self.attempts = 1
            return self._action(prefix=("P16",)), []
        step = self.state
        skipped = [Effect("skipped", {"step": step})]
        if step == "safe_to_talk":
            return self._goto("consent_recording"), skipped
        if step == "language":
            return self._goto("safe_to_talk"), skipped
        if step == "readback":
            return self._goto("trades"), skipped
        if step in CONSENTS:
            action, effects = self._consent(granted=False)
            return action, skipped + effects
        return self._after_question(step), skipped

    def _consent(self, granted: bool) -> tuple[Action, list[Effect]]:
        prompt, kind, nxt = CONSENTS[self.state]
        effects = [Effect("consent", {"kind": kind, "granted": granted, "prompt_id": prompt})]
        if kind == "recording" and not granted:
            self.keypad_only = True
            effects.append(Effect("keypad_only"))
        return self._goto(nxt), effects

    def _after_question(self, step: str) -> Action:
        if step == "q_lean":
            return self._goto("trades" if self.keypad_only else "story")
        return self._goto(QUESTIONS[step][2])

    def _goto(self, state: str) -> Action:
        self.state = state
        self.attempts = 0
        if state == "language" and len(self._menu()) < 2:
            menu = self._menu()
            if menu:
                self.language = next(iter(menu.values()))
            return self._goto("safe_to_talk")
        if state == "summary":
            self.state = "ended"
            return Hangup(("P15",))
        return self._action()

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
        if s in QUESTIONS:
            prompt, options, _ = QUESTIONS[s]
            return Ask(s, prefix + (prompt,), "".join(options) + GLOBAL_KEYS, self.timeout)
        if s == "story":
            return Record(s, prefix + ("P12",))
        if s == "readback":
            valid = "123"[: len(self.candidates)] + "3"
            return Ask(s, prefix + (self.readback_prompt,), valid + GLOBAL_KEYS, self.timeout)
        return Hangup()
