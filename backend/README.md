# backend: the voice API, the worker and the shared logic (Python 3.11)

| Folder | What |
|---|---|
| `apps/voice/` | FastAPI server: Exotel Voicebot WebSocket (the live call), prompt audio, `/calls`, the console's JSON API (`console_api.py`), serving `frontend/dist` |
| `apps/worker/` | background worker: understands the work story (speech-to-text, occupation search, read-back audio) and places callbacks |
| `core/dialogue/` | the interview as a pure state machine (`flow.py`), all prompts in 3 languages (`prompts.py`), the closing summary |
| `core/search/` | occupation search: words callers use + BM25 + multilingual meaning match |
| `core/` (other files) | database writes, Sarvam speech-to-text / text-to-speech, callbacks, dialers, phone privacy (hash + encryption), settings |
| `tests/` | unit and integration tests (`pytest` from the repo root) |
| `requirements*.txt` | Python packages (`-dev` for tests, `-nlp` for the worker's model) |

Imports are `from core ...` and `from apps ...`: the backend folder is on the Python path
(`PYTHONPATH=/app/backend` in Docker, `pythonpath = ["backend"]` for pytest; the scripts in
`scripts/` add it themselves).
