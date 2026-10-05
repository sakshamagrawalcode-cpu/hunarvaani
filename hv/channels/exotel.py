"""Phone line through Exotel's Voicebot applet: one two-way WebSocket per call.

Wire format: JSON text frames. Audio is base64 raw PCM, 16-bit mono little-endian at the call's
rate (8000 Hz). We send `media` chunks (multiples of 320 bytes), `clear` to cut playback and a `mark`
after each prompt. Key presses arrive as `dtmf` events. A key pressed during a prompt cuts it short.
"""

import asyncio
import base64
import json
import logging

import numpy as np
from starlette.websockets import WebSocket, WebSocketDisconnect

from ..audio import PromptBank, resample, rms, silence
from ..config import settings
from ..engine import Hangup
from ..prompts import Part

log = logging.getLogger("hv.exotel")
CHUNK_MS = 100
LEAD_SECONDS = 1.0  # send up to 1 s ahead of real time
INTER_DIGIT = 5.0


def _digit(data: dict) -> str | None:
    d = data.get("dtmf") or {}
    for v in (d.get("digit"), d.get("digits"), data.get("digit"), data.get("digits")):
        if v is not None and str(v).strip():
            return str(v).strip()[0]
    return None


class ExotelChannel:
    name = "phone"
    can_type = False

    def __init__(self, ws: WebSocket, bank: PromptBank):
        self.ws, self.bank = ws, bank
        self.rate = 8000
        self.stream_sid: str | None = None
        self.caller: str | None = None
        self.started = asyncio.Event()
        self.ended = asyncio.Event()
        self.keys_q: asyncio.Queue = asyncio.Queue()
        self.recording: bytearray | None = None
        self.voice_at: float | None = None
        self.last_voice: float | None = None
        self.player: asyncio.Task | None = None
        self.lock = asyncio.Lock()
        self.device_pin = settings.phone_pincode  # the line's district (each district can run its own number)

    # incoming ----------------------------------------------------------------------------------
    async def reader(self) -> None:
        loop = asyncio.get_running_loop()
        try:
            while True:
                msg = await self.ws.receive()
                if msg["type"] == "websocket.disconnect":
                    break
                if not msg.get("text"):
                    continue
                try:
                    data = json.loads(msg["text"])
                except json.JSONDecodeError:
                    continue
                event = str(data.get("event", "")).lower()
                if event == "start":
                    start = data.get("start") or {}
                    self.stream_sid = data.get("stream_sid") or start.get("stream_sid")
                    self.caller = start.get("from")
                    self.rate = int((start.get("media_format") or {}).get("sample_rate") or 8000)
                    log.info("call started, %d Hz", self.rate)
                    self.started.set()
                elif event == "media" and self.recording is not None:
                    chunk = base64.b64decode((data.get("media") or {}).get("payload") or "")
                    self.recording.extend(chunk)
                    if rms(chunk) >= settings.vad_threshold:
                        now = loop.time()
                        self.voice_at = self.voice_at or now
                        self.last_voice = now
                elif event == "dtmf":
                    digit = _digit(data)
                    if digit:
                        await self.keys_q.put(digit)
                elif event == "stop":
                    log.info("call stopped: %s", (data.get("stop") or {}).get("reason"))
                    break
        except WebSocketDisconnect:
            pass
        finally:
            self.ended.set()
            self.started.set()
            await self.keys_q.put(None)

    # outgoing ----------------------------------------------------------------------------------
    async def send(self, obj: dict) -> None:
        if self.ended.is_set():
            raise Hangup("caller hung up")
        async with self.lock:
            try:
                await self.ws.send_text(json.dumps(obj))
            except Exception as exc:
                self.ended.set()
                raise Hangup("connection lost") from exc

    async def stop_playback(self) -> None:
        if self.player and not self.player.done():
            self.player.cancel()
            try:
                await self.player
            except (asyncio.CancelledError, Hangup):
                pass
        if self.stream_sid and not self.ended.is_set():
            await self.send({"event": "clear", "stream_sid": self.stream_sid})

    async def _stream(self, pcm: bytes, name: str) -> None:
        chunk = self.rate * 2 * CHUNK_MS // 1000
        if len(pcm) % chunk:
            pcm += b"\x00" * (chunk - len(pcm) % chunk)
        loop = asyncio.get_running_loop()
        t0 = loop.time()
        for i, pos in enumerate(range(0, len(pcm), chunk)):
            payload = base64.b64encode(pcm[pos:pos + chunk]).decode()
            await self.send({"event": "media", "stream_sid": self.stream_sid, "media": {"payload": payload}})
            ahead = t0 + (i + 1) * CHUNK_MS / 1000 - loop.time()
            if ahead > LEAD_SECONDS:
                await asyncio.sleep(ahead - LEAD_SECONDS)
        await self.send({"event": "mark", "stream_sid": self.stream_sid, "mark": {"name": name}})

    async def play(self, parts: list[Part], lang: str, beep: bool = False) -> float:
        """Start playing; returns how long the audio lasts (seconds)."""
        await self.started.wait()
        await self.stop_playback()
        keys = [x.key for x in parts] + (["beep"] if beep else [])
        x = self.bank.join(lang, keys, self.rate)
        if len(x) == 0:
            return 0.0
        self.player = asyncio.create_task(self._stream(x.tobytes(), "+".join(keys)[:60]))
        return len(x) / self.rate

    def _drain(self) -> None:
        while not self.keys_q.empty():
            if self.keys_q.get_nowait() is None:
                raise Hangup("caller hung up")

    async def _key(self, timeout: float) -> str | None:
        try:
            k = await asyncio.wait_for(self.keys_q.get(), timeout)
        except asyncio.TimeoutError:
            return None
        if k is None:
            raise Hangup("caller hung up")
        return k

    # the channel interface -----------------------------------------------------------------------
    async def say(self, parts: list[Part], lang: str) -> None:
        duration = await self.play(parts, lang)
        if self.ended.is_set():
            raise Hangup("caller hung up")
        await asyncio.sleep(duration)

    async def keys(self, parts, lang, allowed, timeout):
        self._drain()
        duration = await self.play(parts, lang)
        key = await self._key(duration + timeout)
        if key is not None:
            await self.stop_playback()  # barge-in: a key cuts the prompt short
        return key

    async def digits(self, parts, lang, count, timeout):
        self._drain()
        duration = await self.play(parts, lang)
        got = ""
        wait = duration + timeout
        while len(got) < count:
            k = await self._key(wait)
            if k is None:
                break
            if not got:
                await self.stop_playback()
            if k == "#":
                break
            if k.isdigit():
                got += k
            wait = INTER_DIGIT
        return got or None

    async def text(self, parts, lang, field):
        return None

    async def speech(self, parts, lang, max_seconds):
        """Play the question and a beep, then record until the caller stops talking."""
        self._drain()
        duration = await self.play(parts, lang, beep=True)
        await asyncio.sleep(duration)
        loop = asyncio.get_running_loop()
        self.recording, self.voice_at, self.last_voice = bytearray(), None, None
        t0 = loop.time()
        while not self.ended.is_set():
            await asyncio.sleep(0.1)
            now = loop.time()
            if self.voice_at and now - (self.last_voice or now) >= settings.silence_seconds:
                break
            if not self.voice_at and now - t0 >= 10:  # nothing said
                break
            if now - t0 >= max_seconds:
                break
            if not self.keys_q.empty():  # a key ends the answer early
                break
        pcm, self.recording = bytes(self.recording or b""), None
        if self.ended.is_set():
            raise Hangup("caller hung up")
        if not self.voice_at:
            return None
        x = np.frombuffer(pcm[: len(pcm) // 2 * 2], dtype=np.int16)
        x = np.concatenate([silence(self.rate, 200), x])
        return resample(x, self.rate, 16000).tobytes()

    async def talk(self, parts, lang, allowed: str, labels: list[str], max_seconds: float):
        """Play the question and a beep, then record until the caller stops talking. A key press
        answers instead (1 = yes / first option ...). -> ("audio", pcm16k) | ("key", k) | ("none", None)"""
        self._drain()
        duration = await self.play(parts, lang, beep=True)
        loop = asyncio.get_running_loop()
        end_of_prompt = loop.time() + duration
        while loop.time() < end_of_prompt:  # a key during the question answers it at once
            if not self.keys_q.empty():
                break
            await asyncio.sleep(0.05)
        if not self.keys_q.empty():
            await self.stop_playback()
            k = await self._key(0.1)
            return ("key", k) if k else ("none", None)
        self.recording, self.voice_at, self.last_voice = bytearray(), None, None
        t0 = loop.time()
        while not self.ended.is_set():
            await asyncio.sleep(0.1)
            now = loop.time()
            if self.voice_at and now - (self.last_voice or now) >= settings.silence_seconds:
                break
            if not self.voice_at and now - t0 >= 10:
                break
            if now - t0 >= max_seconds or not self.keys_q.empty():
                break
        pcm, self.recording = bytes(self.recording or b""), None
        if self.ended.is_set():
            raise Hangup("caller hung up")
        if not self.keys_q.empty():
            k = await self._key(0.1)
            return ("key", k) if k else ("none", None)
        if not self.voice_at:
            return "none", None
        x = np.frombuffer(pcm[: len(pcm) // 2 * 2], dtype=np.int16)
        x = np.concatenate([silence(self.rate, 200), x])
        return "audio", resample(x, self.rate, 16000).tobytes()

    async def show(self, kind: str, payload: dict) -> None:
        return None

    async def end(self, reason: str) -> None:
        if not self.ended.is_set():
            try:
                await self.stop_playback()
            except Hangup:
                pass
