"""A channel that answers from a script: used by the tests and the terminal demo.

answers: a list (answered in order) or a dict {question key: answer or [answers]}, so a test does not
depend on the order the guided conversation picks. With a dict, a question not in it gets `default`.
An answer can be text (what the person said), a key ("1"), bytes (audio) or "" (silence).
"""

from ..engine import Hangup
from ..prompts import Part


class ScriptChannel:
    name = "script"

    def __init__(self, answers, can_type: bool = True, device_pin: str = "", default: str = ""):
        self.by_key = answers if isinstance(answers, dict) else None
        self.answers = [] if self.by_key is not None else list(answers)
        self.can_type = can_type
        self.device_pin = device_pin
        self.default = default
        self.heard: list[str] = []  # every piece key the person would hear, in order
        self.asked: list[str] = []  # the question key of every question asked
        self.shown: list[tuple[str, dict]] = []
        self.turns = 0

    def _next(self, parts=None):
        self.turns += 1
        if self.turns > 400:
            raise Hangup("script loop")
        if self.by_key is not None:
            keys = [x.key for x in parts or []]
            self.asked.append(keys[-1] if keys else "")
            for k in reversed(keys):
                if k in self.by_key:
                    v = self.by_key[k]
                    if isinstance(v, list):
                        if not v:
                            continue
                        return v.pop(0) if len(v) > 1 else v[0]
                    return v
            if self.default is None:
                raise Hangup("script finished")
            return self.default
        if not self.answers:
            raise Hangup("script finished")
        return self.answers.pop(0)

    async def say(self, parts: list[Part], lang: str) -> None:
        self.heard += [x.key for x in parts]

    async def keys(self, parts, lang, allowed, timeout):
        self.heard += [x.key for x in parts]
        return self._next(parts)

    async def digits(self, parts, lang, count, timeout):
        self.heard += [x.key for x in parts]
        return self._next(parts)

    async def speech(self, parts, lang, max_seconds):
        self.heard += [x.key for x in parts]
        return self._next(parts)

    async def text(self, parts, lang, field):
        self.heard += [x.key for x in parts]
        return self._next(parts)

    async def talk(self, parts, lang, allowed, labels, max_seconds):
        self.heard += [x.key for x in parts]
        v = self._next(parts)
        if isinstance(v, (bytes, bytearray)):
            return ("audio", bytes(v)) if v else ("none", None)
        if v is None or v == "":
            return "none", None
        v = str(v)
        if len(v) == 1 and v in allowed:
            return "key", v
        return "text", v

    async def show(self, kind: str, payload: dict) -> None:
        self.shown.append((kind, payload))
