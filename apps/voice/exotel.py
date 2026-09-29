"""Exotel Voicebot adapter: one two-way WebSocket per call runs the whole interview.

Wire format (proven on the team's SIH bridge): JSON text frames; audio is base64 raw PCM,
16-bit mono little-endian at the call's sample rate (8000 Hz). We send `media` chunks that are
multiples of 320 bytes, `clear` to cut playback, and `mark` after each prompt.
"""

import asyncio
import base64
import json
import logging
import math
import re
import struct
import warnings
import wave
from datetime import datetime, timezone
from pathlib import Path

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool

from core import dynprompt, interview_store, story_job
from core.config import Settings
from core.dialogue.flow import Ask, Hangup, Interview
from core.dialogue.prompts import audio_dir_name
from core.phone import last4

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    import audioop

log = logging.getLogger("exotel")
_DYN_NAME = re.compile(r"^[0-9a-f]{8,64}$")
CHUNK_MS = 200
START_TIMEOUT = 15


class CallEnded(Exception):
    pass


def beep(rate: int, seconds: float = 0.4, freq: int = 1000) -> bytes:
    n = int(rate * seconds)
    return b"".join(
        struct.pack("<h", int(6000 * math.sin(2 * math.pi * freq * i / rate))) for i in range(n)
    )


class PromptAudio:
    """Pre-rendered prompt WAVs as raw PCM at the call's sample rate, Hindi as fallback."""

    def __init__(self, audio_dir: Path):
        self.dir = audio_dir
        self._cache: dict[tuple[str, str, int], bytes] = {}

    def pcm(self, prompt_id: str, language: str, rate: int) -> bytes:
        key = (prompt_id, language, rate)
        if key not in self._cache:
            self._cache[key] = self._load(prompt_id, language, rate)
        return self._cache[key]

    def _load(self, prompt_id: str, language: str, rate: int) -> bytes:
        if prompt_id.startswith(dynprompt.PREFIX):
            name = prompt_id[len(dynprompt.PREFIX) :]
            path = self.dir / "dyn" / f"{name}.wav"
            if not (_DYN_NAME.match(name) and path.is_file()):
                log.warning("missing generated prompt %s", prompt_id)
                return b""
            return self._read(path, rate)
        for folder in dict.fromkeys((audio_dir_name(language), "hi")):
            path = self.dir / folder / f"{prompt_id}.wav"
            if path.is_file():
                break
        else:
            log.warning("no audio for %s; render it with scripts/render_prompts.py", prompt_id)
            return b""
        return self._read(path, rate)

    @staticmethod
    def _read(path: Path, rate: int) -> bytes:
        with wave.open(str(path)) as w:
            if w.getnchannels() != 1 or w.getsampwidth() != 2:
                log.warning("%s is not 16-bit mono; re-render it", path)
                return b""
            frames, src_rate = w.readframes(w.getnframes()), w.getframerate()
        if src_rate != rate:
            frames = audioop.ratecv(frames, 2, 1, src_rate, rate, None)[0]
        return frames


class ExotelSession:
    def __init__(self, ws: WebSocket, settings: Settings, audio: PromptAudio, r):
        self.ws, self.settings, self.audio, self.r = ws, settings, audio, r
        self.keys: asyncio.Queue[str | None] = asyncio.Queue()
        self.started = asyncio.Event()
        self.ended = asyncio.Event()
        self.stream_sid: str | None = None
        self.call_sid: str | None = None
        self.caller: str | None = None
        self.rate = 8000
        self.language = "hi-IN"
        self.recording: bytearray | None = None
        self.max_record_bytes = 0
        self.voice_started: float | None = None
        self.last_voice: float | None = None
        self.player: asyncio.Task | None = None
        self._send_lock = asyncio.Lock()

    async def send(self, obj: dict) -> None:
        if self.ended.is_set():
            return
        async with self._send_lock:
            try:
                await self.ws.send_text(json.dumps(obj))
            except Exception:
                self._mark_ended()

    def _mark_ended(self) -> None:
        if not self.ended.is_set():
            self.ended.set()
            self.keys.put_nowait(None)
            self.started.set()

    async def reader(self) -> None:
        try:
            while True:
                try:
                    data = json.loads(await self.ws.receive_text())
                except (json.JSONDecodeError, TypeError):
                    continue
                event = data.get("event")
                if event == "start":
                    start = data.get("start") or {}
                    self.stream_sid = data.get("stream_sid") or start.get("stream_sid")
                    self.call_sid = start.get("call_sid") or data.get("call_sid")
                    self.caller = start.get("from")
                    fmt = start.get("media_format") or {}
                    self.rate = int(fmt.get("sample_rate") or 8000)
                    self.started.set()
                elif event == "media" and self.recording is not None:
                    payload = (data.get("media") or {}).get("payload")
                    if payload and len(self.recording) < self.max_record_bytes:
                        chunk = base64.b64decode(payload)
                        self.recording.extend(chunk)
                        even = chunk[: len(chunk) // 2 * 2]
                        if even and audioop.rms(even, 2) >= self.settings.vad_threshold:
                            now = asyncio.get_running_loop().time()
                            self.voice_started = self.voice_started or now
                            self.last_voice = now
                elif event == "dtmf":
                    digit = str((data.get("dtmf") or {}).get("digit") or "")
                    if digit:
                        self.keys.put_nowait(digit)
                elif event == "stop":
                    break
        except WebSocketDisconnect:
            pass
        except Exception:
            log.exception("websocket read error")
        finally:
            self._mark_ended()

    async def play(self, prompt_ids: tuple[str, ...], extra: bytes = b"") -> float:
        await self.stop_playback()
        pcm = b"".join(self.audio.pcm(p, self.language, self.rate) for p in prompt_ids) + extra
        if not pcm:
            if prompt_ids:
                mark = {"name": "+".join(prompt_ids)}
                await self.send({"event": "mark", "stream_sid": self.stream_sid, "mark": mark})
            return 0.0
        self.player = asyncio.create_task(self._stream(pcm, "+".join(prompt_ids)))
        return len(pcm) / (2 * self.rate)

    async def _stream(self, pcm: bytes, name: str) -> None:
        chunk = self.rate * 2 * CHUNK_MS // 1000
        if len(pcm) % chunk:
            pcm += b"\x00" * (chunk - len(pcm) % chunk)
        loop = asyncio.get_running_loop()
        started = loop.time()
        for i, pos in enumerate(range(0, len(pcm), chunk)):
            payload = base64.b64encode(pcm[pos : pos + chunk]).decode()
            await self.send(
                {"event": "media", "stream_sid": self.stream_sid, "media": {"payload": payload}}
            )
            ahead = started + (i + 1) * CHUNK_MS / 1000 - loop.time()
            if ahead > 1.0:
                await asyncio.sleep(ahead - 1.0)
        await self.send({"event": "mark", "stream_sid": self.stream_sid, "mark": {"name": name}})

    async def stop_playback(self) -> None:
        if self.player and not self.player.done():
            self.player.cancel()
            try:
                await self.player
            except asyncio.CancelledError:
                pass
            await self.send({"event": "clear", "stream_sid": self.stream_sid})

    def _drain_keys(self) -> None:
        while not self.keys.empty():
            self.keys.get_nowait()
        if self.ended.is_set():
            raise CallEnded

    async def _wait_key(self, seconds: float) -> str | None:
        if seconds <= 0:
            return None
        try:
            key = await asyncio.wait_for(self.keys.get(), seconds)
        except asyncio.TimeoutError:
            return None
        if key is None:
            raise CallEnded
        return key

    async def _sleep_unless_ended(self, seconds: float) -> None:
        try:
            await asyncio.wait_for(self.ended.wait(), seconds)
        except asyncio.TimeoutError:
            return
        raise CallEnded

    async def ask(self, action: Ask) -> str | None:
        self._drain_keys()
        loop = asyncio.get_running_loop()
        deadline = loop.time() + await self.play(action.prompts) + action.timeout
        key = await self._wait_key(deadline - loop.time())
        if key is not None:
            await self.stop_playback()
        return key

    async def record(self, action) -> tuple[bytes, bool, str]:
        """Record until #, silence after speech, no speech at all, or the time limit.

        Returns (pcm, caller_hung_up, why_it_stopped).
        """
        self._drain_keys()
        await self._sleep_unless_ended(await self.play(action.prompts, extra=beep(self.rate)))
        self._drain_keys()
        self.max_record_bytes = action.max_seconds * self.rate * 2
        self.voice_started = self.last_voice = None
        self.recording = bytearray()
        loop = asyncio.get_running_loop()
        started = loop.time()
        deadline = started + action.max_seconds
        silence = self.settings.record_silence_seconds
        no_speech = self.settings.record_no_speech_seconds
        hung_up, why = False, "time_limit"
        try:
            while True:
                now = loop.time()
                if now >= deadline:
                    break
                if self.last_voice is not None and now - self.last_voice >= silence:
                    why = "silence"
                    break
                if self.voice_started is None and now - started >= no_speech:
                    why = "no_speech"
                    break
                key = await self._wait_key(min(0.25, deadline - now))
                if key == action.finish_key:
                    why = "key"
                    break
        except CallEnded:
            hung_up, why = True, "hangup"
        pcm, self.recording = bytes(self.recording), None
        return pcm, hung_up, why

    async def _understand(self, call_id: str, path: str, language: str) -> dict | None:
        """Hand the story to the worker, play the 'one moment' filler, wait for the answer."""
        loop = asyncio.get_running_loop()
        started = loop.time()
        await run_in_threadpool(story_job.submit, self.r, call_id, path, language)
        await self.play(("P17",))
        result = await run_in_threadpool(
            story_job.wait_result, self.r, call_id, self.settings.story_wait_seconds
        )
        waited = loop.time() - started
        if result is None:
            log.info(
                "call %s: no search result after %.1f s; using the trade list", call_id[:8], waited
            )
        elif result.get("error"):
            log.warning("call %s: story processing failed: %s", call_id[:8], result["error"])
        else:
            log.info(
                "call %s: understood in %.1f s, %d words, top %s",
                call_id[:8],
                waited,
                len((result.get("transcript") or "").split()),
                result.get("scores"),
            )
        return result

    def _save_recording(self, call_id: str, pcm: bytes) -> str:
        folder = Path(self.settings.recordings_dir)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{call_id}-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}.wav"
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self.rate)
            w.writeframes(pcm)
        return str(path)

    async def _log(self, call_id: str, kind: str, payload: dict) -> None:
        await run_in_threadpool(interview_store.log_event, self.settings, call_id, kind, payload)

    async def _apply(self, call_id: str, effects) -> None:
        await run_in_threadpool(
            interview_store.apply_effects, self.settings, self.r, call_id, effects
        )

    async def run(self) -> None:
        reader = asyncio.create_task(self.reader())
        call_id = None
        try:
            await asyncio.wait_for(self.started.wait(), START_TIMEOUT)
            if self.ended.is_set():
                return
            call_id = await run_in_threadpool(
                interview_store.begin_call, self.settings, self.call_sid, self.caller
            )
            short = call_id[:8]
            log.info("call %s: started, caller %s", short, last4(self.caller))
            engine = Interview(
                second_language=self.settings.second_language,
                timeout=self.settings.ivr_timeout_seconds,
            )
            action = engine.start()
            while True:
                self.language = engine.language
                if isinstance(action, Hangup):
                    log.info("call %s: goodbye %s", short, "+".join(action.prompts) or "(silent)")
                    await self._sleep_unless_ended(await self.play(action.prompts) + 0.5)
                    break
                if isinstance(action, Ask):
                    log.info(
                        "call %s: asking %s (%s)", short, action.step, "+".join(action.prompts)
                    )
                    key = await self.ask(action)
                    if key is None:
                        log.info("call %s: %s timed out", short, action.step)
                        await self._log(call_id, "timeout", {"step": action.step})
                        action, effects = engine.on_timeout()
                    else:
                        log.info("call %s: %s key %s", short, action.step, key)
                        await self._log(call_id, "key", {"step": action.step, "digit": key})
                        action, effects = engine.on_key(key)
                    await self._apply(call_id, effects)
                    continue
                pcm, hung_up, why = await self.record(action)
                seconds = len(pcm) / (2 * self.rate)
                keep = pcm and why != "no_speech"
                path = await run_in_threadpool(self._save_recording, call_id, pcm) if keep else None
                log.info("call %s: story recorded, %.1f s, stopped by %s", short, seconds, why)
                result = {}
                if path and not hung_up:
                    result = await self._understand(call_id, path, engine.language) or {}
                scores = result.get("scores") or []
                details = {
                    "transcript": result.get("transcript"),
                    "top1": scores[0]["code"] if scores else None,
                    "top2": scores[1]["code"] if len(scores) > 1 else None,
                    "stt_ms": result.get("stt_ms"),
                    "search_ms": result.get("search_ms"),
                    "scores": scores,
                    "error": result.get("error"),
                }
                action, effects = engine.on_recording(
                    path, seconds, result.get("candidates"), result.get("prompt"), details
                )
                await self._apply(call_id, effects)
                if hung_up:
                    break
        except (CallEnded, asyncio.TimeoutError):
            if call_id:
                log.info("call %s: caller hung up", call_id[:8])
        except Exception:
            log.exception("call failed")
        finally:
            if self.player and not self.player.done():
                self.player.cancel()
            reader.cancel()
            if call_id:
                log.info("call %s: ended", call_id[:8])
                try:
                    await run_in_threadpool(interview_store.end_call, self.settings, call_id)
                except Exception:
                    log.exception("could not close the call record")
            try:
                await self.ws.close()
            except Exception:
                pass
