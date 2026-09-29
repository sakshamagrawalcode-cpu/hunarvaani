# HunarVaani
Missed call → free callback → voice/keypad interview → NSQF-based training and job options.
Team Cognify.

## Run it locally (Windows, Docker Desktop running)

```powershell
copy .env.example .env          # first time only, then fill in your keys
python scripts\gen_secrets.py   # fills PHONE_HASH_SECRET and PHONE_ENC_KEY in .env
docker compose -f infra/docker-compose.yml up -d --build
curl.exe http://localhost:8000/health   # {"ok":true}
curl.exe http://localhost:8000/ready    # db, pgvector and redis all true
docker compose -f infra/docker-compose.yml logs worker
docker compose -f infra/docker-compose.yml down
```

`.env` holds secrets and is never committed.

## Database and occupation data (Step 4)

A brand-new database applies `db/*.sql` on first start. If the `pgdata` volume already exists,
apply them yourself (safe to repeat), then load the 16 seed occupations with embeddings:

```powershell
docker compose -f infra/docker-compose.yml build worker
docker compose -f infra/docker-compose.yml run --rm worker python scripts/init_db.py
docker compose -f infra/docker-compose.yml run --rm worker python scripts/seed_nco.py
curl.exe http://localhost:8000/ready    # nco_rows should be 16
```

The first `seed_nco.py` run downloads the multilingual-e5-base model (about 1 GB) into a
Docker volume, so later runs are fast. The api service needs a restart only for code changes.

## Tests

```powershell
pip install -r requirements-dev.txt
pytest
ruff check .
```

## Layout

```
apps/voice/    FastAPI: Plivo webhooks, IVR XML, calls page
apps/worker/   callback queue, transcription, search
core/          config, dialogue, search
data/          NCO seed data
audio/hi/      pre-rendered Hindi prompts (8 kHz)
scripts/       secrets, prompt rendering, seeding, measurement
infra/         Dockerfile, docker-compose.yml
tests/         unit tests
docs/          measurements, honesty table
```

## Voice prompts (Step 5)

The 20 Hindi prompts (P01–P20) live in `core/dialogue/prompts.py`. Render them on your laptop (needs
ffmpeg on PATH and `SARVAM_API_KEY` in `.env`; `SARVAM_SPEAKER` is optional):

```powershell
python scripts\render_prompts.py --dry-run    # prints the text, no API calls
python scripts\render_prompts.py --only P01   # renders one prompt as a test
python scripts\render_prompts.py              # renders every missing prompt (18 files)
docker compose -f infra/docker-compose.yml up -d --build
curl.exe -o test.wav http://localhost:8000/audio/hi/P01.wav
```

P13 and P15 contain placeholders and are rendered during the call (Steps 9 and 10).
Files land in `audio/hi/` and are served at `/audio/hi/<id>.wav`.

## Public address for Plivo (Step 6)

Plivo must reach your api over HTTPS. A free Cloudflare quick tunnel does this for testing
(real callers are served only from the server in Step 12):

```powershell
docker compose -f infra/docker-compose.yml --profile tunnel up -d tunnel
python scripts\set_public_url.py --from-tunnel    # writes PUBLIC_BASE_URL into .env, checks /health
docker compose -f infra/docker-compose.yml up -d api worker
```

Open `<that address>/audio/hi/P01.wav` on your phone with Wi-Fi off. The address changes every
time the tunnel restarts, so repeat the last two commands after a restart.
Stop it with `docker compose -f infra/docker-compose.yml --profile tunnel stop tunnel`.

## Missed call and free callback (Step 7)

Flow: someone dials the Plivo number → `POST /pv/answer` checks Plivo's V3 signature, rejects the
call (so the caller pays nothing) and queues a callback → the worker dials back after
`CALLBACK_DELAY_SECONDS` → Plivo fetches `/pv/ivr/start` (plays P01 for now; Step 8 adds the menus)
→ `/pv/hangup` records the duration.

Rules: Indian mobiles only; at most `MAX_TRIGGERS_PER_DAY` per number per IST day;
`DAILY_CALL_BUDGET` callbacks per day in total; nothing is dialled during `QUIET_HOURS`
(those callbacks wait until the window ends); blocked numbers are ignored; a repeated
CallUUID is ignored. Numbers are stored only as an HMAC hash plus a Fernet-encrypted copy,
and logs show only the last four digits.

Setup once the Plivo account exists:

1. In `.env` fill `PLIVO_AUTH_ID`, `PLIVO_AUTH_TOKEN`, `PLIVO_NUMBER`.
2. Apply the new column: `docker compose -f infra/docker-compose.yml run --rm worker python scripts/init_db.py`
3. `docker compose -f infra/docker-compose.yml up -d --build api worker`
4. In the Plivo console create an Application: Answer URL `POST <PUBLIC_BASE_URL>/pv/answer`,
   Hangup URL `POST <PUBLIC_BASE_URL>/pv/hangup`, then attach the number to it.
   The URL must match `PUBLIC_BASE_URL` exactly, or every signature check fails with 403.
5. Give a missed call from a verified phone and watch
   `docker compose -f infra/docker-compose.yml logs -f api worker`.

Integration tests use a throwaway Postgres and Redis:
`TEST_DATABASE_URL=... TEST_REDIS_URL=... pytest` (they wipe that database).

## Interview over Exotel (Step 8)

The keypad interview lives in `core/dialogue/flow.py`, a provider-neutral state machine
(opening → safe to talk → language → 3 consents → education, travel, preference → work story
or trade list → end). Global keys: 9 deletes the caller's data (rows and story recordings) and
blocks the number, 0 flags the call for a human (P19). Timeouts and wrong keys repeat once with
P16, then skip.

Exotel runs it through the **Voicebot** applet: one two-way WebSocket per call at
`wss://<public address>/exotel/ws/<EXOTEL_WS_TOKEN>`. Callbacks use Exotel's
"connect a number to a flow" API and report back to `/exotel/status/<EXOTEL_WS_TOKEN>`.

Setup:

1. `python scripts\gen_secrets.py` (adds `EXOTEL_WS_TOKEN`), then fill `EXOTEL_SID`,
   `EXOTEL_API_KEY`, `EXOTEL_API_TOKEN`, `EXOTEL_CALLER_ID` (your ExoPhone) and `EXOTEL_APP_ID`
   (the number at the end of your flow's URL in App Bazaar). Use `api.in.exotel.com` for
   `EXOTEL_SUBDOMAIN` if your dashboard is `my.in.exotel.com`.
2. `python scripts\render_prompts.py` (renders the new P19).
3. `docker compose -f infra/docker-compose.yml run --rm worker python scripts/init_db.py`
4. `docker compose -f infra/docker-compose.yml up -d --build`
5. Tunnel: `python scripts\set_public_url.py --from-tunnel` prints the Voicebot URL; paste it
   into the Voicebot applet (Call Start), put a Hangup applet in Next, save.

Try it without a phone: `docker compose -f infra/docker-compose.yml exec api python scripts/simulate_call.py`
Try the callback: `python scripts\exotel_call_me.py 98XXXXXXXX`

## Work story understanding and read-back (Step 9)

After the beep the caller speaks; recording stops on #, 2.5 s of silence after speech, 12 s with
no speech, or 60 s. The api plays P17 ("एक पल रुकिए") and queues the recording for the worker,
which transcribes it with Sarvam Saaras (≤28 s pieces), searches the 16 occupations
(alias + BM25 + multilingual-e5 cosine), and renders P13 with Bulbul. If the answer arrives within
`STORY_WAIT_SECONDS` and the best score is ≥ 0.35, the caller hears the top two and confirms with
1 or 2 (3 = neither → trade list). Every read-back answer is stored as a labelled pair. The worker
also saves the transcript itself, so a story that takes longer than the wait is not lost.

After pulling this step, re-seed the occupations (new Hindi aliases) and rebuild:

```powershell
docker compose -f infra/docker-compose.yml up -d --build
docker compose -f infra/docker-compose.yml run --rm worker python scripts/seed_nco.py
docker compose -f infra/docker-compose.yml exec worker python scripts/calibrate_search.py
```

## Closing summary and calls page (Step 10)

Every completed interview ends with P15, rendered during the call from what was recorded
("धन्यवाद। हमने लिखा है: दसवीं पास, मोबाइल मिस्त्री। … हुनरवाणी कभी पैसे या ओटीपी नहीं माँगता।"); if
rendering fails the fixed P20 closing plays instead. Render P20 once with
`python scripts\render_prompts.py`.

The team's calls page is at `<PUBLIC_BASE_URL>/calls` (or `http://localhost:8000/calls`), behind
basic auth with `CALLS_PAGE_USER` / `CALLS_PAGE_PASSWORD` from `.env`. It shows the latest 50 calls:
answers, the caller's own words, the search's top two, the confirmed occupation, timings,
consents and flags. Numbers show only their last four digits.
