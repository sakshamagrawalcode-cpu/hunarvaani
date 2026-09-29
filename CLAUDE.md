# HunarVaani: start here (for a new Claude chat)

**What it is:** a phone-call (IVR) assistant for SIH problem statement 26097 (MoSJE, PM-AJAY GIA).
A caller on a keypad phone picks Hindi, English or Marathi, gives consent, answers short keypad
questions (age, gender, education, travel, physical difficulty, job or own work) and describes
their work in their own words; the system understands the occupation (59 NCO occupations),
says back what it heard and understood, the caller confirms, and a spoken summary ends the call.
The team sees every call on a React console. **Next: recommend NSQF training / livelihood
options from a sample dataset and say them on the call.**

## Read these (in this order)
1. `docs/HANDOFF.md`: everything: where things are, architecture, call flow with examples, what
   is built (section 5), **the plan with timeline (section 6)**, recommender design (7), laptop
   commands (8), rules (9).
2. `docs/PROBLEM_STATEMENT.md`: the SIH text and what we cover of it.
3. `frontend/README.md`, `backend/README.md`, `database/README.md`: what each folder holds.

## Current state (keep this block up to date)
- Done: A1 three languages · A2 "you said…" read-back + retell + polite prompts · A3 age, gender,
  physical difficulty, one "why we ask" (P28) · consents reviewed (P06–P08, simple words; P08 =
  "use without name/number to train our AI") · A4 59 occupations · A5 team console · folder
  layout frontend/ backend/ database/ · B2 live call view (three panels: conversation /
  processing / errors; schema 06 → run `init_db.py`) · language menu first, then the greeting ·
  P29 "wrong key" apology (render it: `python scripts\render_prompts.py`).
- **Next:** A6 = the user tests on real calls (prompts are rendered; needs Sarvam credits; rebuild, 3 calls,
  check `/console/`). Then A7 (district by PIN code) + A8 (sample NSQF dataset in
  `database/sample/`). Open question: demo region (proposed: Maharashtra + a few Hindi-belt
  districts).
- Blocked: outbound calls / callbacks (Exotel needs business KYC; the team has none).

## Links (no secrets here; secrets live only in the laptop's `.env`)
- Repo: https://github.com/sakshamagrawalcode-cpu/hunarvaani (branch `main`)
- Laptop: `C:\Projects\hunarvaani`, Windows 11, PowerShell, Docker Desktop, VS Code
- Exotel trial flow "sih idea" (App ID 1349182), number 09513886363 + PIN; Sarvam for speech
- Teammates' repos to reuse: https://github.com/sakshamagrawalcode-cpu/SIH (SkillCall,
  `backend/app/engine.py` for recommendations), https://github.com/asmit-1101/satyavaani

## How the user likes to work
- Simple language, short steps, exact PowerShell commands starting from `git pull`; wait for
  "done" and their results before the next step. They share logs and screenshots.
- They may ask which model / effort to use: Opus high for code steps, Sonnet medium for guidance.
- Never ask them to paste keys or passwords in chat; tell them to blur screenshots.
- Finish the prototype first (plan Phase A); extras (Phase B) only if time remains.
- **After finishing any step: update `docs/HANDOFF.md` (sections 5 and 6) and this block.**
- Only one Claude chat changes code at a time; `git pull` first.

## Working in the Claude cloud sandbox (tested recipe)
```bash
pip install -q --ignore-installed cryptography && pip install -q -r backend/requirements-dev.txt
B=/usr/lib/postgresql/16/bin; D=/tmp/hvpg; mkdir -p $D && chown nobody $D
su nobody -s /bin/bash -c "$B/initdb -D $D/data -U hv --auth=trust >/dev/null; $B/pg_ctl -D $D/data -o '-p 55432 -k /tmp' -l $D/pg.log start"
$B/psql -h 127.0.0.1 -p 55432 -U hv -d postgres -c "CREATE DATABASE hv_test"
$B/psql -h 127.0.0.1 -p 55432 -U hv -d hv_test -c "CREATE EXTENSION vector"
(cd /tmp && redis-server --port 56379 --dir /tmp --daemonize yes)
TEST_DATABASE_URL=postgresql://hv@127.0.0.1:55432/hv_test TEST_REDIS_URL=redis://127.0.0.1:56379/0 pytest -q
ruff check . && ruff format --check .
cd frontend && npm ci && npm run build      # strict TypeScript must pass
```
- Postgres and Redis stop between turns: restart them (`pg_ctl … start`, `redis-server …`).
- Blocked from the sandbox: Hugging Face (the e5 model) and Sarvam; no Docker daemon. Playwright's
  Chromium is at `/opt/pw-browsers` for console screenshots.
- Don't `pkill -f` a pattern that also appears in your own command line (it kills the shell).
- Commit with `set -o pipefail` and only after all tests pass; push to `main`.

## Things that bite on the laptop
- Prompt text changed → `python scripts\render_prompts.py` (re-renders only changed prompts; `--force` re-renders all and wastes Sarvam credits).
- Sarvam credits ran out on 29 Sep (HTTP 402). Without credits, calls still run but skip speech-to-text, the read-back and the spoken summary (keypad list + fixed goodbye). Add credits in the Sarvam dashboard before real-call tests.
- Schema or occupations changed → `init_db.py` then `seed_nco.py` (in the worker container).
- Tunnel restarted → `python scripts\set_public_url.py --from-tunnel`, paste the URL in Exotel.
- Console "not built" → `docker compose -f infra/docker-compose.yml up -d --build`.
