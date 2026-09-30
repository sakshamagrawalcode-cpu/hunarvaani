# HunarVaani: project handoff (status, plan, how it works)

Last updated: 29 Sep 2026, after the consent review (P06–P08) and the frontend / backend /
database layout. A short start file for a new chat is `CLAUDE.md` in the repo root.
Read this first if you are a new teammate or a new Claude chat picking up the work.
- The SIH problem statement and what we cover of it: `docs/PROBLEM_STATEMENT.md`.
- **The plan, in order, with a timeline: section 6.** Tick items there as they are finished.

**Rules for the work itself:** only one Claude chat changes the code at a time; always
`git pull` first; **update this file (section 5 and section 6) after finishing anything.**

---

## 1. What HunarVaani is, in simple words

A person in a village with a basic keypad phone calls our number. A polite voice greets them and
asks which language they want (**Hindi, English or Marathi**). They answer most questions by
**pressing keys** (consent, age, gender, education, how far they can travel, any physical
difficulty, job or own work), and for "what work do you do?" they **just talk**. The system
**works out their occupation from what they said** (one of 59, e.g. "मैं सिलाई का काम करती हूं" →
Tailor, NCO 7531), says back what it heard and what it understood, and the caller confirms with a
key. If it did not understand, the caller can tell it once more in more detail. The call ends with
a spoken summary and a safety line ("हुनरवाणी कभी पैसे या ओटीपी नहीं माँगता").

The team watches every call on the **team console** (a web app): profile, the caller's words and
recording, what the system understood, consents and a timeline of every step.

**Next (the heart of the problem statement):** use this profile to recommend 2–3 **NSQF training
courses and livelihood options near the caller**, with the skill gap, and say them on the call.

Designed for Smart India Hackathon (problem statement 26097, MoSJE, PM-AJAY) by **Team Cognify**
(IIIT Vadodara). The original design is "HunarVaani — Prototype Build Guide (File 3 of 3)"; this
repo started as its 48-hour slice, adapted to Exotel, and is now being extended as planned in
section 6.

---

## 2. Where everything is

| What | Where |
|---|---|
| Code (this repo) | https://github.com/sakshamagrawalcode-cpu/hunarvaani (private, branch `main`) |
| Code on the laptop | `C:\Projects\hunarvaani` (Windows 11, Docker Desktop, VS Code) |
| Team console | `http://localhost:8000/console/` on the laptop (user `admin`, password = `CALLS_PAGE_PASSWORD`); the older one-table page is `/calls` |
| Design doc (File 3 of 3) | Claude Docs page "HunarVaani — Prototype Build Guide (File 3 of 3)" |
| Problem statement | `docs/PROBLEM_STATEMENT.md` (SIH 26097) |
| SkillCall (teammate idea, earlier prototype) | https://github.com/sakshamagrawalcode-cpu/SIH (React + FastAPI; `backend/app/engine.py` has recommendation / skill-gap logic to port in step A9) |
| Satyavaani (teammate: voice-clone detector) | https://github.com/asmit-1101/satyavaani (FastAPI `/v1/score`; later "liveness" flag, B8) |
| Telephony (in use) | **Exotel trial**: flow **"sih idea"**, App ID **1349182**, shared trial number **09513886363** (callers enter the account PIN first) |
| Telephony limits | Outbound calls (callbacks) need **business KYC** → blocked for us (HTTP 403). Inbound calls work |
| Telephony (backup) | Plivo: signup blocked; Contact-Sales request sent. Plivo code kept (`TELEPHONY_PROVIDER=plivo`) |
| Speech | Sarvam (India): Saaras v3 speech-to-text, Bulbul v3 text-to-speech. Key in `.env` |
| Domain | `hunarvaani.co.in` (DomainIndia, DNS on Cloudflare); email forwarding via Cloudflare |
| Public URL (dev) | Cloudflare quick tunnel, **changes on every restart** |

**Secrets live only in `.env` on the laptop** (never in git, never in chat): `SARVAM_API_KEY`,
`PHONE_HASH_SECRET`, `PHONE_ENC_KEY`, `EXOTEL_WS_TOKEN`, `CALLS_PAGE_PASSWORD`,
`EXOTEL_SID / EXOTEL_API_KEY / EXOTEL_API_TOKEN / EXOTEL_CALLER_ID / EXOTEL_APP_ID`.
`scripts/gen_secrets.py` fills the generated ones. Other settings: `LANGUAGES=hi-IN,en-IN,mr-IN`,
`STORY_MAX_WAIT_SECONDS=90` (longest wait for the worker during a call).

---

## 3. What runs, and how the pieces talk

```mermaid
flowchart LR
    Phone["Keypad phone"] -- "call + PIN" --> Exotel["Exotel<br/>flow: Voicebot → Hangup"]
    Exotel -- "wss:// audio + key presses" --> Tunnel["Cloudflare tunnel"]
    Tunnel --> API["api (FastAPI)<br/>backend/apps/voice"]
    API -- "prompts (8 kHz WAV)" --> Exotel
    API -- "story job (Redis list)" --> Worker["worker<br/>backend/apps/worker"]
    Worker -- "speech-to-text, translate, TTS" --> Sarvam["Sarvam (India)"]
    Worker -- "transcript (+ English), top 3, 'you said' + read-back audio" --> API
    API --> DB[("Postgres + pgvector<br/>calls, answers, consents,<br/>stories, events, 59 occupations")]
    Worker --> DB
    Team["Team browser"] -- "/console (password)" --> API
```

Docker Compose services (`infra/docker-compose.yml`): `api` (also serves the console, built in a
Node stage of the Dockerfile), `worker`, `db` (Postgres 16 + pgvector), `redis`, `tunnel`
(optional profile).

**Folders:** `frontend/` (team console) · `backend/` (voice API, worker, shared logic, tests) ·
`database/` (schema, seed data, sample data) · `scripts/` (tools you run) · `audio/` (rendered
prompts, not in git) · `infra/` (Docker) · `docs/`. Each of `frontend/`, `backend/`, `database/`
has its own README.

| Folder / file | Job |
|---|---|
| `backend/core/dialogue/flow.py` | **The interview** as a pure state machine (no I/O). Provider-neutral |
| `backend/core/dialogue/prompts.py` | 30 prompts × 3 languages (P13, P15, P21 are filled in during the call) |
| `backend/core/dialogue/summary.py`, `options.py` | The closing summary; the options sentence (P34) in each language |
| `backend/apps/voice/exotel.py` | Exotel Voicebot WebSocket: plays prompts, reads keys, records the story |
| `backend/apps/voice/main.py` | Routes: `/health`, `/ready`, `/audio/..`, `/exotel/ws/<token>`, `/exotel/status/<token>`, `/pv/*` (Plivo), `/calls`, `/console/…` |
| `backend/apps/voice/console_api.py` | Read-only JSON for the console (`/console/api/summary`, `/calls`, `/calls/<id>`, `/calls/<id>/audio/<n>`, `/people`, `/occupations`, `/prompts`) |
| `backend/apps/voice/calls_page.py` | The older one-table calls page |
| `backend/apps/worker/main.py` | Background worker: story understanding + callbacks |
| `backend/core/stt.py`, `tts.py`, `dynprompt.py` | Sarvam speech-to-text / text-to-speech, cached generated prompts |
| `backend/core/story_job.py` | Worker job: transcribe → English (Sarvam translate) → search both wordings → render "you said" + read-back of the top 3 (in parallel) |
| `backend/core/prompt_check.py` | Checks every rendered prompt file (length, loudness, silence, text changed) for the console's Voice prompts page |
| `backend/core/search/*` | Occupation search: aliases + BM25 + multilingual-e5 meaning match |
| `backend/core/geo.py` | PIN code → district (first 3 digits, sample table) |
| `backend/core/llm.py` | Sarvam LLM reads the work story (occupations, years, skills, clean sentence) |
| `backend/core/sample_data.py`, `recommend.py` | Loads the sample dataset; picks the top 3 training / livelihood options with reasons and skill gap (A9) |
| `backend/core/interview_store.py`, `store.py` | Database writes (incl. 9 = delete everything, recordings too) |
| `backend/core/callbacks.py`, `dialers.py` | Missed-call → callback queue, Exotel / Plivo dialers |
| `backend/tests/` | 349 tests (unit + real-Postgres/Redis integration) |
| `frontend/` | **Team console**: Vite + React + TypeScript + Tailwind; pages in `src/pages/` |
| `database/schema/*.sql` | Tables (applied by `scripts/init_db.py`) |
| `database/seed/nco_seed.csv` | **59 occupations** with English, Hindi, Marathi names and words callers use |
| `database/sample/` | Sample data (A7, A8): PIN → district, occupations, courses, centres, demand, sectors, schemes |
| `scripts/` | `recommend` (options for a profile), `gen_secrets`, `render_prompts`, `seed_nco`, `set_public_url`, `simulate_call`, `show_call`, `calibrate_search`, `exotel_call_me`, `init_db` |

---

## 4. How a call goes (the conversation flow)

```mermaid
flowchart TD
    A([Caller dials 09513886363 + PIN]) --> P05["P05 language first: 1 हिंदी / 2 English / 3 मराठी<br/>(no choice: the menu plays again)"]
    P05 --> P01["P01 greeting in the chosen language … आगे बढ़ने के लिए 1"]
    P01 -- "silence 8 s" --> P02["P02 क्या आप सुन पा रहे हैं? 1 / कॉल नहीं किया तो 9"]
    P02 -- 1 --> P03
    P02 -- "silence" --> P02
    P01 -- 1 --> P03["P03 बात करने का समय है? (~4 min) 1 हाँ / 2 बाद में"]
    P03 -- 2 --> P04["P04 कल फिर कॉल करेंगे"] --> CB([callback queued for tomorrow])
    P03 -- 1 --> P06["P06 consent: recording (says what for)"] --> P07["P07 consent: share with centre/bank"] --> P08["P08 consent: use without name/number to train our AI"]
    P08 --> P28["P28 why we ask (once): age, education, travel → right training, work, schemes; some schemes only for women"] --> P25["P25 age band 1–6"] --> P26["P26 gender 1–4"]
    P26 --> P09["P09 education 1–7"] --> P10["P10 travel 1–5"] --> P27["P27 physical difficulty 1/2"] --> P31["P31 PIN code: 6 digits (# to end, * to skip)"] --> P11["P11 job / own work / unsure"]
    P11 --> REV["P35 आपने बताया: उम्र…, पढ़ाई…, पिन कोड 4 1 1 0 0 1…<br/>P36 सब सही 1 / कुछ बदलना 2"]
    REV -- 2 --> CH["P37 क्या बदलना है? उम्र 1 … नौकरी या अपना काम 7"] -- "that question again" --> REV
    REV -- "1, recording = yes" --> P12["P12 अपने काम के बारे में बताइए<br/>(stops on silence, # or 60 s)"]
    REV -- "1, recording = no" --> P14
    P12 --> P17["P17 धन्यवाद, एक पल रुकिए…<br/>worker: Sarvam STT → English → search → TTS<br/>every 8 s: P30 कृपया लाइन पर बने रहिए (up to 90 s)"]
    P17 -- "understood" --> P13["P21 आपने बताया: (caller's words) +<br/>P13 आपका काम इनमें से एक है: X के लिए 1, Y के लिए 2, Z के लिए 3; कोई नहीं = 4"]
    P17 -- "unclear / too short" --> RETRY["P21 आपने बताया: … + P24 समझ नहीं पाए<br/>(no speech: P22 आवाज़ साफ़ नहीं)"]
    RETRY -- "tries 1–2" --> P23["P23 बीप के बाद थोड़ा और विस्तार से बताइए"] --> P17
    RETRY -- "3rd try" --> P14
    P17 -- "worker error / no answer in 90 s" --> P14["P14 keypad trade list 1–5"]
    P13 -- "1, 2 or 3" --> REC
    P13 -- "none (tries 1–2)" --> P23
    P13 -- "none (3rd try)" --> P14
    P14 --> REC["recommender (sample data): top 3 options<br/>P17 एक पल रुकिए while P34 is made"]
    REC -- "options + voice ok" --> P34["P34 हमने लिख ली है: education, काम…<br/>रास्ता 1: … 2: … 3: … पसंद का नंबर दबाइए; कोई नहीं = 4"]
    P34 -- "1–3 or none" --> P33["P33 धन्यवाद, आपकी पसंद सेव हो गई"] --> CLOSE["P38 रेफ़रेंस नंबर 4 8 2 1 5 7, P40 फिर से …<br/>P39 सेंटर / सीएससी पर बताइए; आधार, पासबुक, सर्टिफ़िकेट, फ़ोटो; कभी पैसे या ओटीपी नहीं"] --> END([hang up])
    REC -- "no option / no voice" --> P15["P15 summary: हमने लिख लिया है: education, और काम: occupation (P20 if TTS fails)"]
    P15 --> CLOSE
```

**PIN code (P31):** the caller types the 6 digits (they end by themselves; `#` ends early). Too short or wrong → P32 and the question again, as for every question; only `*` (said in P31) skips it. The first 3 digits give the district from `database/sample/pin_districts.csv` (approximate sample table); saved as answers `q_pin` and `q_district`. While typing the PIN, 9 and 0 are ordinary digits (they do not delete or flag).

**Anywhere in a menu (except while typing the PIN):** `9` = delete all my data (calls, answers, recordings) + block my number
(P18, hang up); `0` = flag the call for a human officer (P19) and repeat the question.
**No key:** P16 "माफ़ कीजिए, हमें आपका जवाब नहीं मिला…"; **wrong key:** P29 "माफ़ कीजिए, यह बटन इस सवाल
के लिए नहीं है…"; then the **same question again, as often as needed**. Nothing is skipped and the
call never hangs up for silence; it ends only when the caller hangs up, presses 9, or finishes.
(At the language menu the menu itself replays; at the greeting P02 "can you hear us?" repeats.)

**Options (A10):** once the occupation is known, the recommender picks up to 3 options from the
sample dataset; P34 says what we noted and each option (what it is, how long, free, how far), the
caller presses its number (or the next key for none), P33 says goodbye. The options, and which one
the caller chose, are saved (`recommendation` table) and shown on the call page. If nothing fits,
or the voice cannot be made (no Sarvam credits), the call ends with the summary (P15 / P20).

### Example 1: Sunita, tailor, Hindi (full happy path)

| # | Phone says | Sunita does | System does |
|---|---|---|---|
| 1 | P05 language menu | 1 (Hindi) | `call.language = hi-IN` |
| 2 | P01 नमस्ते जी! … (in Hindi) | presses 1 | logs key |
| 3 | P03 बात करने का समय है? | 1 | |
| 4 | P06, P07, P08 consents | 1, 1, 2 | recording yes, share yes, research no |
| 5 | P28 (why we ask, once) + P25 age, P26 gender | 3, 1 | `26_35`, `female` |
| 6 | P09, P10, P27, P11 | 3, 2, 1, 2 | up to 8th, 10 km, no difficulty, own work |
| 7 | P12 + beep | "मैं घर पर ब्लाउज़ और सूट सिलती हूं, दस साल से" | recording stops 2.5 s after she goes quiet |
| 8 | P17 धन्यवाद, एक पल रुकिए… (P30 every 8 s if Sarvam is slow) | waits ~2–5 s | worker: transcript → English "I stitch blouses and suits at home…" → search both → 7531 दर्ज़ी (0.8) / 7533 कढ़ाई / 7318 बुनकर → renders two audio pieces at once |
| 9 | "आपने बताया: मैं घर पर ब्लाउज़ और सूट सिलती हूं, दस साल से। हमारी समझ से, आपका काम इनमें से एक है। दर्ज़ी के लिए 1 दबाइए। कढ़ाई … 2 … अगर इनमें से कोई नहीं, तो 4 दबाइए।" | presses 1 | `occupation = 7531`, story confirmed |
| 10 | P15 summary … | | call `completed`; the "you said" audio is deleted |

On the console: her row on Overview and Calls; the call page shows her profile, her words with the
recording, "Understood: Tailor (दर्ज़ी) / Embroidery worker", "Caller confirmed: yes", consents and
the full timeline.

### Example 2: Ramesh, careful caller (timeouts, human flag, no recording)

1. P01: he waits 8 s → P02 → presses 1. P05: 1 (Hindi). P03: 1.
2. P06 (recording): **2 = no** → keypad-only mode, no story will be recorded. P07: 2, P08: 2.
3. P25: he presses **0** → P19 "हमारे एक अधिकारी जल्दी ही आपसे बात करेंगे…" + P25 again; call
   flagged `wants a human`. He presses 4 (36–45). P26: 2.
4. P09: 6 (ITI). P10: silence → P16 + P10 again → silence → P16 + P10 again → he presses 2. P27: 2, P11: 1.
5. Recording was refused → P14 trade list → 3 (electrical work, 7411) → P15.
   On the console: badges **wants a human**, **keypad only**; two "No answer" warnings at travel.

### Example 3: Meena, Marathi, not understood the first time

P05: 3 (Marathi) → all questions in Marathi → story: "आज हवामान चांगलं आहे" (small talk) →
"तुम्ही सांगितलं: आज हवामान चांगलं आहे. माफ करा, आम्हाला तुमचं काम नीट समजलं नाही." + P23 →
she tells again: "मी शेतात मजुरी करते" → "…शेतमजूर साठी 1 दाबा…" → 1 → summary in Marathi.
The console shows both tries.

### Example 4: short endings

- **Not now:** P03 → 2 → P04. A callback is queued for tomorrow (needs KYC to actually dial).
- **Delete me:** any menu → 9 → P18. Every call row for that number, its recordings and cached
  results are deleted; the number's hash is blocked.

---

## 5. What is built, and measured

| Step | Built | Commit |
|---|---|---|
| 1 | Laptop setup (Docker, WSL 2, Python 3.11, ffmpeg), repo | `30c02e3` |
| 2 | Sarvam key; domain + email; Plivo blocked → Exotel chosen | — |
| 3 | Docker stack: api, worker, Postgres/pgvector, Redis; `/health`, `/ready` | `e77ad02` |
| 4 | DB schema; NCO occupations with e5 embeddings | `5089582` |
| 5 | Hindi prompts rendered with Bulbul (8 kHz); `/audio` route | `b44dd68` |
| 6 | Cloudflare tunnel + `set_public_url.py` | `cb25ae5` |
| 7 | Missed call → free callback (rules: Indian mobiles, 3/day, budget, quiet hours, block list, dedupe, hashed + encrypted numbers). **Blocked by Exotel KYC** | `45fb299` |
| 8 | Keypad interview engine + Exotel Voicebot adapter + simulator | `4cfd752` |
| 8b | Recording stops on silence; per-call logs; `show_call.py` | `49d145a`, `c9f3af8` |
| 9 | Story → Sarvam STT → occupation search → spoken read-back | `ff5e1d6`, `279c8d2` |
| 10 | Spoken summary; `/calls` page | `1c092b7` |
| Review | 9 deletes recordings too; late transcripts kept; callback matched by number; `init_db.py` re-runnable; simulator fixed | `a22910d`–`cb3b546` |
| Fix | Calls no longer drop after the story when the worker needs over 3 s | `3652ddf` |
| A1 | **Three languages** (Hindi, English, Marathi), menu right after the greeting | `32890f5` |
| A2 | **Read-back says what we heard**; unclear or "neither" → tell it again in more detail; all prompts polite and clear; "you said" audio deleted after the call | `4e15b34` |
| A3 | **Age, gender, physical difficulty** questions; each question says **why** we ask | `c588c06` |
| A4 | **59 occupations** (was 16) incl. traditional crafts and rural work, words in 3 languages | `710657e` |
| A5 | **Team console** (React): overview, calls, call detail with recording + timeline, people, occupations | `44dd869` |
| A3b | "Why we ask" said **once** (P28) before the personal questions; the questions are short again | `bd15a36` |
| Layout | Code split into `frontend/`, `backend/`, `database/` (+ `scripts/`, `audio/`, `infra/`, `docs/`), a README in each | `4517c32` |
| B2 | **Live call view** (done early; redesigned: sidebar layout, three panels Conversation / Processing / Errors & warnings, no English shown in the console); language menu now comes **before** the greeting; wrong key gets its own apology (P29): every step saved as an event (what the system said with English, keys, answers, the caller's words + English translation via Sarvam translate, occupation scores, worker timings, problems); the call page shows a categorised live log (filters, search, follow live), LIVE badges and a "call happening now" banner | see git log |
| A7 | **District from the PIN code**: P31/P32 in 3 languages, digit-collecting `Ask.digits` + `Interview.on_digits`, `core/geo.py` + `database/sample/pin_districts.csv` (Maharashtra + Hindi-belt, 3-digit prefixes), console shows District | see git log |
| Calls | **Never skip, never hang up for silence** (P16/P29 + the question again, as often as needed); smoother audio (2 s send-ahead, database writes off the audio path, every prompt at the same loudness); laptop port back to 8000; **Voice prompts** console page (listen to every file, length, loudness, silence, problems) | `cc209e7` |
| Story | **Waits for Sarvam** (P17, then P30 "please stay on the line" every 8 s, up to 90 s); the caller's words are **translated to English** and the search uses both; read-back offers the **3 closest occupations** (1–3, next key = none); unclear or too short → tell it again, up to 3 tries, then the trade list; `story.top3` (schema 07); new prompt P30 | see git log |
| Exotel | **Talks to Exotel like the team's SIH bridge** (which works on every call): audio 1 s ahead (was 2 s), `clear` before every prompt and on every key press, log lines for `connected` / `start` / accepted socket; an Exotel URL on SIH's `…/exotel` or with a wrong token is refused with a log line saying how to fix it; smoke test with a real uvicorn server + fake Exotel client passed (menu → PIN → trade list → goodbye) | see git log |
| Reliability | After a real call **cut off during P10** with no `stop` message from Exotel (so the connection itself closed) and some keys lost: the tunnel now uses **HTTP/2 instead of QUIC** (Cloudflare's advice for long websockets); uvicorn waits **60 s** for a keepalive reply (was 20 s); the log and the console's Errors panel say **why a call ended** (caller hung up / Exotel stopped / connection closed with code N / sending failed) and warn if Exotel goes quiet for 15 s; each prompt logs **how long Exotel took to play it** (`exotel played P01 (+0.9 s)`: the real delay); a **second press of the same key within 0.6 s** is ignored instead of answering the next question; binary frames no longer end a call | see git log |
| A8 | **Sample dataset** (`database/sample/`, all labelled sample): 59 occupation profiles (sector, usual skills, near trades, loan route, RPL yes/no), 115 courses (59 upskill + 54 RPL certificates + PM Vishwakarma training/toolkit + "Start your own work" at RSETI), 124 centres (4 types in each of the 31 PIN-table districts, distance, hostel, women-only batches), demand per district, 16 sectors with wages, 9 real schemes described simply (verify before real use); loader `core/sample_data.py`. Course ids are ours, not real QP codes | see git log |
| A9 | **Recommendation engine** `core/recommend.py`: filters (age, education, heavy work if physical difficulty, no business course for job seekers, centre within the daily travel or a hostel in the state) → score 0.35 fit + 0.20 demand + 0.20 reach + 0.15 wish + 0.10 step-up (+0.03 women-only batch) → top 3 with reasons and skill gap; farther centres only fill in, marked "farther"; every occupation × district × travel × wish gets ≥ 1 option (tested); `scripts/recommend.py` shows options for any profile; ideas from SkillCall `engine.py` | see git log |
| A10 | **Options said on the call** (3 languages): after the occupation, `Offer` → recommender → P34 "रास्ता 1: … 3 महीने, मुफ़्त, 8 किलोमीटर दूर …" → key 1–3 or none → P33 goodbye; saved in `recommendation` (schema 08: rank, course, centre, score, reasons, skill gap, spoken, chosen) and as answer `interest`; P17 plays while P34 is made; no option / no voice → summary as before; `core/dialogue/options.py` speaks only dataset facts | see git log |
| A11 (part) | Call page: **"Training and livelihood options"** card (what, NSQF level, hours, fee, placement, centre + km, farther badge, scheme, loan, reasons, skill gap, "caller chose"), labelled sample; live log shows "3 options found" and "caller chose option N" | see git log |
| A11 | **Console v2 done**: **Sample data** page (courses / centres / schemes, search, district filter, "sample" banner); **Download CSV** of all calls (answers, district, occupation, options offered, option chosen; last 4 digits only; opens in Excel with Hindi/Marathi); **district filter** on Calls and People; **Option / Chosen option** column on Calls and People | see git log |
| Fix | One-language setup: the call's language was never saved (no menu → no "language" answer); now saved at the start | see git log |
| Real call ✅ | **First full real call** (30 Sep, 230 s): language → consents → questions → PIN → spoken story (6.5 s) → read-back confirmed motor vehicle mechanic → 3 options said → option 2 chosen → goodbye. Exotel played every prompt ~1.1 s after our last audio (1.0 s is our own send-ahead, so the network adds only ~0.1–0.3 s). Fix from it: the `#` callers press after a full PIN (as P31 tells them) reached P11 as a wrong key; now ignored for 4 s after a PIN | see git log |
| Script v2 | **All prompts rewritten short and clear** (Hindi ~27% fewer characters with 6 new prompts; every question states its keys at once) in 3 languages; voice **pace 0.9** (a little slower); **answer review** after the keypad questions: P35 + one prerendered piece per saved answer (age, gender, education, travel, difficulty, PIN digit by digit, job/own work) + P36 "all correct 1 / change 2" → P37 change menu (1–7) → that question again → review again; **closing**: reference number (6 digits from the call id, said twice, digit by digit), where to go (training centre / CSC), documents to take (Aadhaar, bank passbook, education certificate, 2 photos; caste or income certificate if they have one), never pay; console shows "Ref 482157" and finds calls by it. 39 fragments per language (`FRAGMENTS`), rendered by `render_prompts.py`. Settings `REVIEW_ANSWERS`, `CLOSING_DETAILS` (default on) | see git log |
| Options v2 | **Hear an option in detail**: P34 now says "press its number for all about it"; the number plays that option's details (what they learn, how long, free or fee, which centre and how far, hostel, job help after, what the scheme gives, loan help for own work), built in English only from the dataset, translated by Sarvam into the caller's language (short local fallback if translation fails), then P41 "choose 1 / hear the options again 2". All option sentences are made at the same time. **Recommender**: years of experience from the story (Hindi, Marathi, English number words; English translation first): under 2 years no RPL certificate, 2+ years the certificate ranks higher, 3+ years helps business training for "not sure" callers; **variety**: a second option of the same kind counts 0.05 less; new reason "N years of experience"; while the option sentences are made the caller hears P30 "stay on the line" every 8 s (never silence), and a Sarvam HTTP 429 is retried once | see git log |
| LLM | **Sarvam LLM reads the work story** (India-hosted, `sarvam-105b-conversations`; never a foreign model): gets the transcript + English + our 59 occupations and returns occupations (codes from our list only), years, skills, job/own work and one clean first-person sentence in the caller's language; its occupations lead the read-back (and rescue stories the word search was unsure about), its sentence replaces the raw transcript in "आपने बताया: …", its years go to the recommender; every field is checked; any failure (slow, no credits, bad JSON) changes nothing; saved in `story.llm` (schema 09) and shown on the call page ("AI understood"); `LLM_ENABLED`, `SARVAM_LLM_MODEL`, `LLM_TIMEOUT_SECONDS` | see git log |
| A13 kit | **Deploy kit**: `infra/docker-compose.prod.yml` (restart policies + Caddy HTTPS on `DOMAIN`), `infra/Caddyfile`, **`docs/DEPLOY.md`** step by step (Azure for Students recommended: USD 100, no card, Central India; Oracle Always Free as the free backup; DigitalOcean student credit ended 1 Aug 2026), DNS on Cloudflare, Exotel URL that never changes | see git log |
| Review | Consents in simple words: P06 only about recording (and "no" still works with keys), P07 says why we share, P08 = "use without name and number to train our AI and recommendation models"; console shows readable consent names; `CLAUDE.md` start file | see git log |

**Measured so far:**
- Real Exotel calls: prompts play, keys work, story recorded, read-back and summary heard.
- Real call understanding: STT 540–700 ms, search 60–340 ms; with the read-back audio 1–4 s.
- Search: 58 test sentences across the 59 occupations in 3 languages map correctly (plus the
  earlier 19 Hindi, 12 English/Marathi); names, small talk and "I am studying" are refused.
- Real e5 cosines (16-occupation set): correct ≈ 0.82–0.84, others ≈ 0.78–0.80, junk ≈ 0.74–0.78.
- 349 automated tests pass (1 skipped where ffmpeg is missing).

---

## 6. The plan (step by step, with a timeline)

**Principle:** first finish a complete, working prototype with the important, doable parts; the
big features come after, in priority order, only if time remains.

**What the finished prototype does (Phase A):** a caller rings, picks a language, answers the
questions by key and voice, the system understands their work, **finds the 2–3 best training /
livelihood options for them from our (sample) dataset of occupations, NSQF courses, centres and
schemes, explains the skill gap, and says the options on the call**; the team sees everything,
live, on the console.

### Phase A: finish the prototype (must have), about 8–9 working days

Days are working days of build + your test calls; a Claude session builds each step in a few
hours, the rest is testing on real calls.

| # | Step | What exactly | Who | Time | Status |
|---|---|---|---|---|---|
| A1 | Three languages | Hindi, English, Marathi | Claude | — | ✅ `32890f5` |
| A2 | Better read-back, polite prompts | "you said…", retell once, polite wording | Claude | — | ✅ `4e15b34` |
| A3 | Age, gender, physical difficulty; "why we ask" once (P28) | keypad questions P25–P27 | Claude | — | ✅ `c588c06`, `bd15a36` |
| A4 | 59 occupations | better matching of what callers say | Claude | — | ✅ `710657e` |
| A5 | Team console v1 | calls, call detail, people, occupations | Claude | — | ✅ `44dd869` |
| A6 | **Test A1–A5 on real calls** | prompts already rendered (needs Sarvam credits for calls), rebuild, 3 calls (one per language), check the console | You | 0.5 day | ⏳ next |
| A7 | **Where the caller lives** | keypad PIN code (6 digits + #) → district, from a PIN-prefix table for the demo state (Maharashtra) + a few Hindi-belt districts; spoken fallback "say your district" later | Claude | 0.5 day | ✅ (needs `render_prompts.py` for P31, P32) |
| A8 | **Sample dataset** (clearly labelled "sample, for demonstration") | `database/sample/`: for each of the 59 occupations: NSQF courses (QP code, name, NSQF level, hours, min education, age range, free/fee, scheme: PMKVY / DDU-GKY / PM-AJAY GIA), skills each course teaches (for the skill gap), heavy-work flag; training centres per district (distance, hostel yes/no, women-only batches); local demand per district (openings, typical wage); self-employment routes (tool kit, loan: PMEGP / Mudra / PM-AJAY GIA income generation) | Claude | 1 day | ✅ see §5 |
| A9 | **Recommendation engine** | score = occupation fit (same trade upskill or a near trade) + eligibility (age, education) + reach (centre within travel limit, or hostel) + wish (job → placement-linked; own work → entrepreneurship + loan) + physical (no heavy work if difficulty) + local demand; returns top 3 with plain-language reasons and the skill gap; port ideas from SkillCall `engine.py`; many tests | Claude | 1 day | ✅ see §5 |
| A10 | **Say the options on the call** | after P15: "आपके लिए दो अच्छे रास्ते हैं: 1) … 2) …; जानकारी चाहिए तो उसका नंबर दबाइए" → choice saved as "interested"; in all 3 languages | Claude | 0.5–1 day | ✅ see §5 |
| A11 | **Console v2** | recommendations + reasons + skill gap on the call and people pages; dataset pages (courses, centres, schemes); **English translation in brackets** of Hindi/Marathi words (Sarvam Translate); CSV export; district filter | Claude | 1 day | ✅ see §5 (English translation in brackets left out: the console shows no translation, by decision) |
| A12 | Step 11 checklist on real calls | every row of the checklist below, fix what breaks | You + Claude | 0.5 day | ☐ |
| A13 | Deploy to India (Step 12) — kit ready: `docs/DEPLOY.md` | 4 vCPU / 8 GB VM in Mumbai/Hyderabad, Docker Compose, Caddy HTTPS, `api.hunarvaani.co.in`; ends the changing tunnel URL | You + Claude | 0.5–1 day | ☐ |
| A14 | Measure 30 calls (Step 13) | 10 Hindi + 10 Marathi + 10 English with consenting people; `scripts/measure.py`: word error rate, wait time p50/p90, completion rate, correct occupation rate → `docs/measurements.md` | You + Claude | 1 day | ☐ |
| A15 | Video, README, slides (Step 14) | 2-minute recording of a call beside the console; honesty table (real vs sample data); slides | You + Claude | 1 day | ☐ |

**Suggested timeline:** Day 1: A6 + A7. Day 2: A8. Day 3: A9. Day 4: A10 + tests on calls.
Day 5: A11. Day 6: A12 + A13. Day 7: A14. Day 8: A15. Day 9: buffer.

### Phase B: add if time remains (in this order)

Ordered by value to the judges ÷ effort. Each is independent, so we can stop anywhere.

| # | Feature | Why it matters | Effort | Risk / blocker |
|---|---|---|---|---|
| B1 | **Traditional family occupation + "what would you like to learn?"** (two short spoken questions, same understanding pipeline) | the problem statement asks for both | 1 day | low |
| B2 | ✅ **Live call view** (done early, polling every 1.5 s): each prompt, key, words, understanding and timing, with English | — | — | done |
| B3 | **Speak or press for every answer** ("पच्चीस साल" → age band) | more natural for callers | 1.5 days | medium (speech errors) |
| B4 | More languages (e.g. Bengali, Tamil, Telugu, Gujarati) | reach | 0.5 day each | needs a native speaker check |
| B5 | Officer tools: mark follow-up done, notes, filters by district/occupation | the GIA "coordination" issue | 1 day | low |
| B6 | **"Talk like a person"**: India-hosted LLM (Sarvam) writes each next line from earlier answers and understands free answers; consent lines stay fixed | empathy, conversation | 2–3 days | high latency (3–5 s a turn), unpredictable wording |
| B7 | Follow-up call with the plan, and missed-call → free callback | the original design | 0.5 day | **blocked: Exotel business KYC** |
| B8 | Satyavaani liveness flag; fraud checks | integrity | 1 day | medium |
| B9 | WhatsApp voice-note channel (same pipeline) | problem statement mentions it | 2 days | WhatsApp Business API approval |
| B10 | Learned ranking (LightGBM) from outcomes | better recommendations | later | needs real outcome data |

### Not possible in this prototype
- Missed-call callbacks and follow-up calls: Exotel needs business KYC documents (we have none).
- Dialects Sarvam does not support (Bhojpuri, Marwari, …).
- Real PM-AJAY beneficiary / centre data: not public → sample data, clearly labelled.
- Asking caste for eligibility: our rule; eligibility is confirmed by an official afterwards.
- Actually enrolling people in a course.

### Step 11 checklist (from the guide; used in A12)

| Check | Status |
|---|---|
| Missed call → callback within 30 s, caller not charged | ⛔ blocked by Exotel KYC (HTTP 403 on the callback API); code + tests done |
| Silence at opening → P02; 9 blocks; blocked number gets no callback | ✅ code + tests; ⏳ confirm on a real call |
| Language, consents, answers saved with keys and timestamps | ✅ real calls; visible on the console |
| No to recording → keypad trade list | ✅ tests; ⏳ real call |
| 45 s story → transcribed and read back within ~6 s | ✅ 1–4 s on short stories; ⏳ try a 45 s one |
| "none" at read-back → tell again (up to 3 tries), then trade list | ✅ tests; ⏳ real call |
| Spoken summary; console shows answers, words, occupation, timings | ✅ built; ⏳ confirm on a real call |
| 4th missed call in a day → no callback; no callbacks in quiet hours | ✅ tests (needs callbacks live) |
| Wrong token → refused | ✅ Exotel secret URL token (SIH-style `…/exotel` refused too, with a hint in the log); Plivo signatures |
| `scripts/measure.py` → WER, latency for 30 calls | ☐ A14 |

### English translation: part of understanding the story
Every Hindi or Marathi story is translated to English (Sarvam translate) **before** the search, and
the search runs on both the caller's words and the English, keeping each occupation's best score.
This helps when the caller's words are not in our word lists, and the English copy is saved in
`story.transcript_en` for English-only models later (B10, training). It adds about 0.5–1 s; if it
fails, the search uses the caller's words only and the console shows a warning. Training data
may only use callers who said yes to P08 (train our AI). The console never shows the English
words themselves (only the timing).

### Review of what the call asks (29 Sep)
- **Questions are enough, not too many** (about 3–4 minutes): language, OK to talk, 3 consents,
  age, gender, education, travel, physical difficulty, job or own work, the work story. Still
  missing for good recommendations: **where the caller lives** (A7) and, from the problem
  statement, **family occupation and what they want to learn** (B1). No caste, no Aadhaar.
- **All 3 consents stay**: each purpose needs its own permission under India's data protection
  law (DPDP Act 2023), and each is short. Recording (P06) is needed for the spoken story; saying
  no still gets the keypad interview. Sharing (P07) is needed before a centre or bank may contact
  them. Training our AI (P08) is optional and does not change the help they get.
- "Why we ask" is said once (P28) before the personal questions; the questions are short.
- To check on real calls: that the Marathi and English sound natural (native speaker), and that
  the whole call stays under ~4 minutes.

### Telephony: why calls were slow or cut, and what fixes it (29 Sep review)
- **How our calls work:** every prompt and every key travels phone → Exotel → internet → Cloudflare
  quick tunnel → Docker on the laptop (home Wi-Fi) → back. Our own code answers a key in about 1 ms
  (see the log timestamps); the delay and the drops come from that long path.
- **How most IVRs work** (and SIH teams such as Pashu-Shield, which moved from Twilio to Exotel's
  native IVR): the provider's own servers play the prompts and read the keys (Exotel "Gather",
  Twilio `<Gather>`), and only a web request goes to the app. We need a live audio stream only for
  the spoken work story, but we stream the whole call.
- **Biggest fix: A13, run the server on a VM in India** (Mumbai / Hyderabad / Bangalore): no
  laptop, no Wi-Fi, no quick tunnel, a fixed URL. Steps and the account to make: `docs/DEPLOY.md`
  (Azure for Students, Central India; the DigitalOcean student credit ended on 1 Aug 2026).
- **Other providers** all need KYC for Indian numbers (DoT rules): Plivo (business email), Twilio
  (business documents for Indian numbers), Ozonetel / Knowlarity / MyOperator (business KYC).
  Exotel's trial is the only no-KYC path we have, so we keep it.
- **Backup for the demo:** a browser "phone" page that speaks the same websocket messages as Exotel
  (mic + keypad) would show the whole flow with no telephony at all (Phase B idea).
- **After each test call, read** `exotel played … (+N s)` (delay the caller hears) and
  `ended early: …` (who ended it) in the api log, and the call's row in Exotel's Call Logs
  (status, duration, who hung up).

### Open decisions and loose ends
- **Sarvam credits ran out** (HTTP 402 on 29 Sep). All 75 prompt files were rendered before that. Live calls need credits for speech-to-text and the read-back / summary voice: add credits in the Sarvam dashboard.
- **Demo region (A7/A8)**: used Maharashtra (18 districts) + 13 Hindi-belt / other cities, the
  districts of `pin_districts.csv`; change it by editing the CSVs in `database/sample/`.
- **Sample data check**: courses, centres, demand and wages are invented; scheme descriptions are
  simplified from memory of the official schemes. A teammate should check `schemes.csv` against
  the official websites before the demo.
- **Native-speaker check** of the Hindi, Marathi and English prompts; voice is Sarvam's default
  (set `SARVAM_SPEAKER`, then `render_prompts.py --force`).
- **NCO codes**: the 59 use NCO-2015 / ISCO-08 4-digit unit groups; check each against NCO-2015
  Vol II before the demo.
- **Plivo**: waiting on Contact-Sales reply (backup only). Plivo `/pv/ivr/start` plays only P01.

---

## 7. Recommendations: design for steps A7–A10 (A7–A9 built as described; A10 next)

1. **Profile** from the call: language, age band, gender, education, travel limit, physical
   difficulty, job vs own work, confirmed occupation (NCO), district (A7), consents.
2. **Candidate options** for the occupation: (a) upskilling courses in the same trade (NSQF level
   above what they likely have), (b) courses in near trades (same sector), (c) for "own work":
   entrepreneurship course + tool kit + loan route.
3. **Filters**: age inside the course's range; education ≥ the course minimum; a centre within the
   travel limit (or hostel if they said hostel); heavy-work courses dropped if physical difficulty;
   women-only batches offered first to women who ask.
4. **Score** (rules first, weights in one place): occupation fit 0.35, local demand 0.20, reach
   0.20, wish (job/own work) 0.15, NSQF step-up 0.10. Ties → shorter, free courses first.
5. **Skill gap**: skills the course teaches minus what their occupation and story already show
   (e.g. tailor → "pattern cutting, machine embroidery, pricing").
6. **Say it**: top 2 on the call in the caller's language, with duration, distance, cost ("free")
   and one reason each; press 1/2 → "interested" saved. Top 3 with reasons on the console.
7. **Honesty**: every sample row carries `sample=true`; the console and slides say so.
8. **As built (A9)**: candidates are same-trade upskill, same-trade RPL certificate, near-trade
   upskill, and for own work / unsure: PM Vishwakarma (its trades) or "Start your own work" plus the
   trade's loan scheme (PM Vishwakarma, PMEGP, Mudra, PM SVANidhi). Reach = 1 − 0.5 × distance ÷
   limit (village 5 km, 10, 30, district HQ 60 km; hostel = 60 km or a hostel centre elsewhere in
   the state). Wish: job → placement-linked 1.0; own work → business training 1.0. No PIN code →
   options without a centre ("centre to be confirmed"). No occupation → no options.

Reuse: SkillCall's `backend/app/engine.py` (occupation matching, skill gap, recommendations,
career path). No foreign LLM may see real callers' data.

---

## 8. Everyday commands (Windows PowerShell, in `C:\Projects\hunarvaani`)

```powershell
# start (Docker Desktop must say "Engine running")
git pull
docker compose -f infra/docker-compose.yml --profile tunnel up -d --build
python scripts\set_public_url.py --from-tunnel      # then paste the wss:// URL into Exotel's Voicebot and Save
docker compose -f infra/docker-compose.yml up -d api worker

# after pulling new prompts or occupations
python scripts\render_prompts.py            # renders missing or changed prompts, every language
python scripts\render_prompts.py --force    # re-renders ALL (only if the voice changed; costs credits)
docker compose -f infra/docker-compose.yml run --rm worker python scripts/init_db.py
docker compose -f infra/docker-compose.yml run --rm worker python scripts/seed_nco.py

# watch and inspect
# team console: http://localhost:8000/console/  (user admin, password = CALLS_PAGE_PASSWORD)
docker compose -f infra/docker-compose.yml logs -f api worker
docker compose -f infra/docker-compose.yml exec api python scripts/show_call.py -n 3
docker compose -f infra/docker-compose.yml exec api python scripts/simulate_call.py   # no phone needed
# listen to every rendered prompt: console → Voice prompts
docker compose -f infra/docker-compose.yml exec worker python scripts/calibrate_search.py
```

Troubleshooting: call cut in the middle → the api log line `ended early: …` says why (caller hung
up / Exotel stopped the stream / connection closed without a stop, code N); check Exotel's Call
Logs too. Keys feel slow → look at `exotel played … (+N s)`; over ~2 s is the network path.
"failed to connect to the docker API" → start Docker Desktop. No logs during a
call → tunnel URL changed; re-run `set_public_url.py` and update Exotel. Log says **"rejected an
Exotel call on wss://.../exotel, the SIH bridge's address"** → the flow "sih idea" is shared with the
SIH bridge and still points at SIH's address; paste the `…/exotel/ws/<token>` URL that
`set_public_url.py` prints. Log says **"wrong token"** → same fix. Log shows `exotel: start` but the
call is silent → prompts not rendered (`render_prompts.py`). Console says "not built"
→ `up -d --build`. Console keeps asking for a password → check `CALLS_PAGE_PASSWORD` in `.env` and
restart the api. Simulator: answer within 8 s; at P12 give seconds to "speak" (a tone, so the story
has no words and the retell / trade list follows).

Console development (optional, needs Node 22): `cd frontend`, `npm install`, `npm run dev`,
open `http://localhost:5173/console/` while the api runs (laptop port 8000).

---

## 9. Rules for anyone (human or Claude) changing this code

- Real callers' audio and text go only to Sarvam (India) and our own server. **No foreign LLM or
  speech API on real data.**
- No caste question, no Aadhaar. Consent before any question; 9 deletes the caller's data.
- Secrets only in `.env`; never print, log or commit them. Logs and the console show only the
  last four digits.
- Callbacks only to Indian mobiles, ≤ 3 triggers per number per day, never 21:00–09:00 IST.
- The interview logic stays in `backend/core/dialogue/flow.py` (pure, provider-neutral); providers are
  adapters.
- Sample data is always labelled as sample.
- Workflow: one Claude chat at a time; `git pull` first; edit, run lint + all tests, commit to
  `main`, push; **update this file**. The laptop runs `git pull` + `docker compose … up -d --build`.
  Tests: `pip install -r backend/requirements-dev.txt`, then `pytest` (set `TEST_DATABASE_URL` and
  `TEST_REDIS_URL` to a throwaway Postgres with pgvector and Redis to run the integration tests;
  they wipe that database). Console: `npm run build` in `frontend/` must pass (strict TypeScript).
- Suggested models: Sonnet (medium) for setup and guidance; Opus (high) for call-flow, search,
  recommendation and deployment code.
