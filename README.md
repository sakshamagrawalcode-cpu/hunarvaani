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

The 18 Hindi prompts live in `core/dialogue/prompts.py`. Render them on your laptop (needs
ffmpeg on PATH and `SARVAM_API_KEY` in `.env`; `SARVAM_SPEAKER` is optional):

```powershell
python scripts\render_prompts.py --dry-run    # prints the text, no API calls
python scripts\render_prompts.py --only P01   # renders one prompt as a test
python scripts\render_prompts.py              # renders every missing prompt (16 files)
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
docker compose -f infra/docker-compose.yml up -d api
```

Open `<that address>/audio/hi/P01.wav` on your phone with Wi-Fi off. The address changes every
time the tunnel restarts, so repeat the last two commands after a restart.
Stop it with `docker compose -f infra/docker-compose.yml --profile tunnel stop tunnel`.
