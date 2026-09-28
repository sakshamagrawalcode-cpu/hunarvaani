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
