"""The officer console's live call: a phone call played in the officer's browser.

It speaks the kiosk page's WebSocket protocol (say / ask / show / end, answers, 16 kHz mic audio),
but the conversation runs as on the phone line: name "phone", nobody can type for the caller, and the
line's PIN code comes from the console (the "line" box) the way PHONE_PINCODE sets it for Exotel.
On top, every decision is sent as a `trace` message, so the officer sees, step by step, what was
heard, what the LLM labelled, why the next question was asked and why each option was ranked.
Records made this way are marked "phone-demo".
"""

from .kiosk import KioskChannel


class ConsoleChannel(KioskChannel):
    name = "phone"
    label = "phone-demo"
    can_type = False

    async def trace(self, step: dict) -> None:
        await self.send({"type": "trace", **step})
