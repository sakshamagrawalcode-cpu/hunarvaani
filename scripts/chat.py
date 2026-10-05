"""Talk to HunarVaani in the terminal (no phone, no microphone): keys and typed answers.

  python scripts/chat.py            # uses HV_MODELS from .env (fake or real LLM)
Spoken questions accept typed text instead of speech; press Enter on an empty line for silence.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hv.config import settings  # noqa: E402
from hv.data import get_data  # noqa: E402
from hv.engine import Conversation  # noqa: E402
from hv.llm import LLM  # noqa: E402
from hv.store import Store  # noqa: E402
from hv.stt import STT  # noqa: E402


class TerminalChannel:
    name = "terminal"
    can_type = True
    device_pin = settings.device_pincode or "411001"  # the "kiosk" location for this terminal

    async def _input(self, prompt: str) -> str:
        return (await asyncio.to_thread(input, prompt)).strip()

    def _print(self, parts) -> None:
        print("\n  " + " ".join(x.text for x in parts if x.text))

    async def say(self, parts, lang):
        self._print(parts)

    async def keys(self, parts, lang, allowed, timeout):
        self._print(parts)
        return (await self._input(f"  key [{allowed}]> "))[:1] or None

    async def digits(self, parts, lang, count, timeout):
        self._print(parts)
        return await self._input(f"  {count} digits> ") or None

    async def speech(self, parts, lang, max_seconds):
        self._print(parts)
        return await self._input("  (speak by typing)> ")

    async def talk(self, parts, lang, allowed, labels, max_seconds):
        self._print(parts)
        shown = [k for k in allowed if k not in "09"]
        hint = "  ".join(f"{k}={lab}" for k, lab in zip(shown, labels)) if labels else ""
        if hint:
            print(f"    ({hint})")
        got = await self._input("  say (type it)> ")
        if not got:
            return "none", None
        return ("key", got) if len(got) == 1 and got in allowed else ("text", got)

    async def text(self, parts, lang, field):
        self._print(parts)
        return await self._input(f"  {field}> ")

    async def show(self, kind, payload):
        if kind == "options":
            for i, o in enumerate(payload["items"], 1):
                print(f"    {i}. {o['course']} @ {o['centre']} ({o['distance_km']} km) score {o['score']} "
                      f"(plain {o['raw']}) gates {o['gates']} why {o['reasons']}")
        elif kind == "card":
            print(f"    CARD: {payload['name']} · {payload['district']} · ID {payload['hv_id']}")
        elif kind == "review":
            print(f"    REVIEW: name={payload['name']} age={payload['age']} studies={payload['education']} "
                  f"travel={payload['travel_km']} km work={payload['work']} wants={payload['wants']} "
                  f"gender={payload['gender']}")


if __name__ == "__main__":
    data = get_data()
    print(f"models: {settings.models}, LLM: {settings.llm_model}")
    reason = asyncio.run(Conversation(TerminalChannel(), data, LLM(data), STT(), Store(settings.db_path)).run())
    print(f"\n[session ended: {reason}]")
