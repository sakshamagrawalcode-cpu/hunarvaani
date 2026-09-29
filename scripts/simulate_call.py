"""Talk to the interview from the terminal, exactly as Exotel's Voicebot would.

Run it inside the api container (it already has the websockets library):
  docker compose -f infra/docker-compose.yml exec api python scripts/simulate_call.py

After each prompt it shows the text (in the language you picked) and waits for you:
  a digit (0-9), several digits, * or #   -> pressed as keys
  Enter on an empty line                  -> stay silent (tests the timeout)
  q                                       -> hang up
At the work-story prompt it asks how many seconds to "speak", then presses # for you.
"""

import argparse
import asyncio
import base64
import json
import math
import os
import struct
import sys
import uuid

import websockets

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.dialogue.prompts import LANGUAGE_KEYS, PROMPTS, split_language  # noqa: E402

RATE = 8000


def tone_frames(seconds: float):
    frame = b"".join(
        struct.pack("<h", int(3000 * math.sin(2 * math.pi * 220 * i / RATE))) for i in range(160)
    )
    payload = base64.b64encode(frame).decode()
    return [{"event": "media", "media": {"payload": payload}}] * int(seconds * 50)


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--caller", default="919876543210", help="caller number to pretend to be")
    ap.add_argument("--url", default="ws://localhost:8000/exotel/ws/")
    args = ap.parse_args()
    token = os.environ.get("EXOTEL_WS_TOKEN", "")
    if not token:
        sys.exit("EXOTEL_WS_TOKEN is empty. Run scripts/gen_secrets.py and restart the api.")

    events: asyncio.Queue = asyncio.Queue()
    async with websockets.connect(args.url + token) as ws:

        async def receive():
            try:
                async for raw in ws:
                    msg = json.loads(raw)
                    if msg.get("event") == "mark":
                        await events.put(("prompt", msg["mark"]["name"]))
            except websockets.ConnectionClosed:
                pass
            await events.put(("end", None))

        async def send(obj) -> bool:
            try:
                await ws.send(json.dumps(obj))
                return True
            except websockets.ConnectionClosed:
                return False

        reader = asyncio.create_task(receive())
        sid = f"sim-{uuid.uuid4()}"
        await send({"event": "connected"})
        await send(
            {
                "event": "start",
                "stream_sid": sid,
                "start": {
                    "stream_sid": sid,
                    "call_sid": sid,
                    "from": args.caller,
                    "media_format": {"encoding": "raw/slin", "sample_rate": str(RATE)},
                },
            }
        )
        print(f"call connected as {args.caller[-4:].rjust(10, 'x')}")
        print("answer each question within the IVR timeout (8 s by default)\n")

        language = "hi-IN"
        while True:
            kind, name = await events.get()
            if kind == "end":
                print("\n[call ended by the server]")
                break
            if not name:
                continue
            for full in name.split("+"):
                pid, pinned = split_language(full)
                text = PROMPTS[pinned or language].get(pid, "(generated during the call)")
                print(f"  {full}: {text}")
            if name == "P17":  # "one moment" while the worker listens; not a question
                continue
            if name.endswith("P12"):
                try:
                    raw = await asyncio.to_thread(input, "seconds to speak (Enter = 3)> ")
                except EOFError:
                    raw = ""
                seconds = float(raw.strip() or 3)
                # The server streams prompts up to 1 s ahead, so the mark arrives before the beep
                # has finished; then send audio in real time (20 ms frames) like a phone does.
                await asyncio.sleep(1.5)
                for frame in tone_frames(seconds):
                    await send(frame)
                    await asyncio.sleep(0.02)
                await send({"event": "dtmf", "dtmf": {"digit": "#"}})
                print(f"  [spoke {seconds:g} s, pressed #]")
                continue
            try:
                line = (await asyncio.to_thread(input, "keys> ")).strip()
            except EOFError:
                line = "q"
            if line.lower() == "q":
                await send({"event": "stop"})
                break
            if "P05@" in name and line[:1] in LANGUAGE_KEYS:
                language = LANGUAGE_KEYS[line[:1]]
            for digit in line:
                if digit in "0123456789*#":
                    if not await send({"event": "dtmf", "dtmf": {"digit": digit}}):
                        print("\n[call already ended: the server timed out waiting for a key]")
                        reader.cancel()
                        return
        reader.cancel()


if __name__ == "__main__":
    asyncio.run(main())
