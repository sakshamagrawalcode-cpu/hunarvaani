"""Kiosk tablet channel: the browser page talks to the engine over one WebSocket.

Server -> page (JSON): say / ask / show / end.
Page -> server: {"type": "answer", "value": "..."} for keys, digits, typed text or typed speech;
binary frames of 16 kHz 16-bit mono PCM while the mic is on, then {"type": "speech_end"}.
"""

import asyncio
import json
import logging

from starlette.websockets import WebSocket, WebSocketDisconnect

from ..audio import PromptBank
from ..engine import Hangup
from ..prompts import Part

log = logging.getLogger("hv.kiosk")
WAIT = 600.0  # a helper-run kiosk can take its time


class KioskChannel:
    name = "kiosk"
    can_type = True

    def __init__(self, ws: WebSocket, bank: PromptBank):
        self.ws, self.bank = ws, bank
        self.inbox: asyncio.Queue = asyncio.Queue()
        self.closed = False
        self.device_pin = ""  # this kiosk's location, set once on the device and sent when it connects
        self.hello = asyncio.Event()

    async def reader(self) -> None:
        try:
            while True:
                msg = await self.ws.receive()
                if msg["type"] == "websocket.disconnect":
                    break
                if msg.get("bytes") is not None:
                    await self.inbox.put(("audio", msg["bytes"]))
                elif msg.get("text") is not None:
                    try:
                        data = json.loads(msg["text"])
                    except json.JSONDecodeError:
                        continue
                    if data.get("type") == "hello":
                        pin = str(data.get("device_pin") or "")
                        self.device_pin = pin if pin.isdigit() and len(pin) == 6 else ""
                        self.hello.set()
                        continue
                    await self.inbox.put(("json", data))
        except WebSocketDisconnect:
            pass
        finally:
            self.closed = True
            self.hello.set()
            await self.inbox.put(("closed", None))

    async def send(self, obj: dict) -> None:
        if self.closed:
            raise Hangup("kiosk closed")
        try:
            await self.ws.send_text(json.dumps(obj, ensure_ascii=False))
        except Exception as exc:
            self.closed = True
            raise Hangup("kiosk closed") from exc

    def _audio(self, parts: list[Part], lang: str) -> list[str]:
        return [f"/audio/{lang}/{x.key}.wav" for x in parts if self.bank.has(lang, x.key)]

    def _payload(self, parts: list[Part], lang: str) -> dict:
        return {"text": " ".join(x.text for x in parts if x.text), "audio": self._audio(parts, lang),
                "complete_audio": all(self.bank.has(lang, x.key) for x in parts), "lang": lang,
                "keys": [x.key for x in parts], "parts": [{"key": x.key, "text": x.text} for x in parts]}

    async def _answer(self, timeout: float = WAIT) -> tuple[str, object]:
        try:
            kind, value = await asyncio.wait_for(self.inbox.get(), timeout)
        except asyncio.TimeoutError:
            return "timeout", None
        if kind == "closed":
            raise Hangup("kiosk closed")
        return kind, value

    async def ready(self) -> None:
        """Wait (briefly) for the page's hello, which carries the kiosk's location."""
        try:
            await asyncio.wait_for(self.hello.wait(), 3)
        except asyncio.TimeoutError:
            pass

    async def say(self, parts: list[Part], lang: str) -> None:
        await self.send({"type": "say", **self._payload(parts, lang)})

    async def _ask(self, mode: str, parts: list[Part], lang: str, **extra) -> str | None:
        await self.send({"type": "ask", "mode": mode, **extra, **self._payload(parts, lang)})
        while True:
            kind, value = await self._answer()
            if kind == "timeout":
                return None
            if kind == "json" and value.get("type") == "answer":
                return str(value.get("value", ""))

    async def keys(self, parts, lang, allowed, timeout):
        return await self._ask("keys", parts, lang, allowed=allowed)

    async def digits(self, parts, lang, count, timeout):
        return await self._ask("digits", parts, lang, count=count, secret=count == 4)

    async def text(self, parts, lang, field):
        return await self._ask("text", parts, lang, field=field)

    async def speech(self, parts, lang, max_seconds):
        await self.send({"type": "ask", "mode": "speech", "max_seconds": max_seconds, **self._payload(parts, lang)})
        audio = bytearray()
        while True:
            kind, value = await self._answer()
            if kind == "timeout":
                return bytes(audio) or None
            if kind == "audio":
                audio.extend(value)
            elif kind == "json" and value.get("type") == "speech_end":
                log.info("kiosk speech: %.1f s of audio", len(audio) / 32000)
                return bytes(audio) or None
            elif kind == "json" and value.get("type") == "answer":
                return str(value.get("value", ""))  # typed instead of spoken

    async def talk(self, parts, lang, allowed: str, labels: list[str], max_seconds: float):
        """A spoken question. The person speaks (the page records by itself after the question and
        stops when they pause) or taps one of the buttons. -> ("audio", pcm) | ("key", k) | ("text", s) | ("none", None)"""
        await self.send({"type": "ask", "mode": "talk", "allowed": allowed, "labels": list(labels),
                         "max_seconds": max_seconds, **self._payload(parts, lang)})
        audio = bytearray()
        while True:
            kind, value = await self._answer()
            if kind == "timeout":
                return ("audio", bytes(audio)) if audio else ("none", None)
            if kind == "audio":
                audio.extend(value)
            elif kind == "json" and value.get("type") == "speech_end":
                log.info("kiosk speech: %.1f s of audio", len(audio) / 32000)
                return ("audio", bytes(audio)) if audio else ("none", None)
            elif kind == "json" and value.get("type") == "answer":
                v = str(value.get("value", "")).strip()
                if len(v) == 1 and v in allowed:
                    return "key", v
                return ("text", v) if v else ("none", None)

    async def show(self, kind: str, payload: dict) -> None:
        await self.send({"type": "show", "kind": kind, "data": payload})

    async def end(self, reason: str) -> None:
        if not self.closed:
            try:
                await self.ws.send_text(json.dumps({"type": "end", "reason": reason}))
            except Exception:
                pass
