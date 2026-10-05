# HunarVaani prototype

A voice livelihood counsellor for SIH26097 (PM-AJAY GIA). A person talks in Hindi, Marathi or English,
on **any phone** (Exotel call) or at a **helper-run kiosk tablet**. HunarVaani then:

1. asks warm, pre-recorded questions, and the person simply **speaks** every answer (name, age, studies,
   travel, their story); only the PIN is typed, so nobody nearby hears it;
2. turns their speech into text (IndicConformer);
3. uses a **small local LLM** (Gemma 4 E4B through Ollama) to label facts, what they insist on, and their mood;
4. from the very first answer keeps a shortlist, and asks the **follow-up question whose answer could
   change it most** (plus the one the LLM suggests), checking the leading kind of work with the person;
5. shows and reads back **everything it understood**, so any detail can be corrected;
6. ranks NSQF options with the **gated personal ranker**, then speaks or shows the top 3–5, plus
   skills worth learning when a small gap leads to better pay;
7. gives a **HunarVaani ID + a PIN** they set, and saves a printable card with a QR code. District
   officers see the record on a console, by district, name or ID.

The location comes from the device: each kiosk sets its PIN code once, the phone line has its own.

All models run on your laptop. No call audio or text goes to an outside API.

```
 phone (Exotel) ─┐                                   ┌─ spoken top 3–5 (pre-recorded pieces)
                 ├─ engine ─ STT ─ LLM labels ─ ranker ┤
 kiosk (browser) ┘     │                              └─ options + ID card on screen
                       └─ SQLite: people, turns, options, audit ─ officer console
```

---

## 1. Install everything (one time)

You need Windows 10/11, an **NVIDIA GPU** (tested target: RTX 5050, 8 GB), about **25 GB of free
disk**, and internet for the downloads. Put this folder somewhere simple, **not in OneDrive**, for
example `C:\HunarVaani`.

1. Double-click **`INSTALL.bat`**.
2. When the browser opens Hugging Face: log in (or sign up free), click **Agree** on both model
   pages, create a **Read** token, and paste it into the installer window (it stays hidden).
3. Wait. The first run takes about 1–1.5 hours, mostly downloads and rendering the voice. Progress
   and time left are shown. If anything stops, fix the message it prints and double-click
   `INSTALL.bat` again: finished steps are skipped.

What it sets up, all on your laptop:

| Part | Model | Runs on | Size |
|---|---|---|---|
| Speech to text | AI4Bharat IndicConformer 600M (ONNX) | CPU, so the GPU stays free for the LLM | ~2.5 GB |
| Labels, emphasis, mood | Gemma 4 E4B (QAT, 4-bit) in Ollama; `gemma4:e2b-it-qat` on GPUs under 7.5 GB | GPU | ~6 GB |
| Voice | AI4Bharat Indic Parler-TTS, every line rendered once (Hindi Divya, Marathi Sunita, English Mary) | GPU, only while rendering | ~4 GB |

The voice uses PyTorch built for CUDA 12.8, which RTX 50-series cards need.

## 2. Run it

Double-click **`RUN.bat`**. Wait until the window says **models warmed up** (about a minute), then:

- **Kiosk:** open http://localhost:8000/kiosk in Chrome. The first time, set **this kiosk's PIN code**
  on the start screen (once per device; everyone at this kiosk gets that location, nobody is asked).
  Press **Start**. The person just talks: after each question the kiosk listens by itself and stops
  when they pause. Buttons are there too, for quick yes/no or choices. Use a headset.
- **Officer console:** http://localhost:8000/officer. Log in as `officer` with the password from
  `OFFICER_PASSWORD` in the `.env` file (the installer made a random one). It has three tabs:
  - **Live call:** a phone-line demo in the browser. Press the green key to call. Number keys answer
    the menus. Type what the caller says in the box under the phone, or use **Speak** to answer with
    the microphone. The PIN is typed on the keypad. On the right, each step appears as it happens:
    what was heard, what the LLM labelled (and what the checks threw out), why the next question was
    picked, the shortlist so far, and the final ranking (score = gates × fit), plus the work the gates
    left out and why. The **Line PIN code** box sets the line's district, as `PHONE_PINCODE` does.
    Records made here are marked `phone-demo`.
  - **Profiles:** search by district, status, name or ID. A person's page explains the record in
    plain words: why each option, why other work was left out, their weights and their own quotes.
    From there an officer can approve, refer, edit with re-ranking, print the card, or erase. Erase
    asks you to type the ID, and every action goes into the audit log.
  - **Ranking policy:** base weights for all districts or one, the gates, learned proposals and the
    version history.
- If port 8000 is busy, it uses the next free port and prints it.

What happens in one session (everything is spoken except the PIN, which is typed so nobody hears it):

```
name (spoken) -> "tell us about yourself" (the first real answer)
   -> IndicConformer (text) -> Gemma labels: work, wishes, limits, what they insist on, mood, and any
      detail they mention (age, studies, travel), so it is not asked again
   -> a shortlist is ranked straight away, and every next question is chosen because its answer could
      change that shortlist (simulated with the ranker), plus the question the LLM suggests;
      follow-ups alternate with the required details (age, gender, studies, travel), so the call
      builds on what they said: "you do tailoring: grow in it, or learn something new?",
      "from what you told us, this work could suit you: does that sound right?"
   -> wording follows the mood (softer if worried or upset, fewer questions when upset)
   -> review: everything understood is shown and read back; "no" -> which one -> say it again
   -> gated ranking -> top 3-5 options, spoken and on screen -> skills worth learning
   -> HunarVaani ID read out, PIN set twice (typed), card file with QR saved (cards\<id>.svg / .html)
```

Short answers ("पैंतीस साल", "दसवीं पास", "दस किलोमीटर", "हाँ") are read by simple rules in a
millisecond; longer answers go to the LLM. If an answer is not understood twice, that one question
falls back to buttons / the keypad.

**After updating to a new version:** record the new voice lines (only new or changed ones are made):
`.\install.ps1 -OnlyVoices -Langs hi` (about 5-10 minutes; close games first).

`.\run.ps1 -Fake` starts without any models, to test screens only. The terminal version is
`.venv\Scripts\python.exe scripts\chat.py`.

**Check the models any time:** `.venv\Scripts\python.exe scripts\check_models.py`. It shows how long
the LLM and speech-to-text take; the speech check transcribes one of the rendered Hindi questions,
so it tests the voice and speech-to-text together.

**Change a spoken line:** edit its text in `hv\prompts.py`, then run `.\install.ps1 -OnlyVoices`. Only
changed lines are rendered again.

## 3. Kiosk on a tablet

A browser lets a page use the microphone only over **https** (or on `localhost`). Start a free
tunnel on the laptop and open the https address on the tablet:

```powershell
winget install --id Cloudflare.cloudflared
cloudflared tunnel --url http://localhost:8000
```

Open `https://<the-address-it-prints>/kiosk` on the tablet (Chrome) and allow the microphone. Use a
headset. The helper types the name; the person sets the PIN on the screen keypad themselves.

## 4. Phone line (Exotel)

With the tunnel from step 3 running, set this as the **Voicebot** applet's URL in your Exotel flow:
```
wss://<the-address-it-prints>/exotel/ws/<EXOTEL_WS_TOKEN from .env>
```
Call your ExoPhone. Callers answer with the keypad or speak after the beep. Key **0** asks for an
officer; **9** twice deletes the caller's data. The missed-call callback still needs Exotel KYC or a
government 1600 number. Until then, callers dial in.

The tunnel address changes each time cloudflared restarts, so update the Exotel URL each time. For a
demo, a server in India is better than a laptop and tunnel.

## 5. How it works (where to look)

| File | What it does |
|---|---|
| `hv/engine.py` | The conversation, written once for every channel: code picks the next question from what is missing |
| `hv/labels.py` | What the LLM must return (JSON schema), and the checks: job codes must be in our list; an emphasis label is kept only if its quote is really in the transcript |
| `hv/policy.py`, `hv/emphasis.py`, `hv/learn.py` | The policy file, evidence → multiplier, and learning from choices and outcomes (section 5b) |
| `hv/ranker.py` | **Score = G × Σ w·m·f.** Gates: work capacity (age + health vs the job's physical load), distance (radius from what they insist on; no hostel if they cannot leave home), eligibility (age, education, RPL only for skills already held). w = officer weights, m = emphasis multiplier from evidence (0.5–3), f = fit on six factors |
| `hv/questions.py` | The question bank and the choice of the next question: value = how much the answer could change the top 3 (simulated), plus the LLM's suggestion; required details alternate with follow-ups |
| `hv/understand.py` | Rules that read short spoken answers (numbers in Hindi/Marathi/English, age, studies, travel in km or minutes, yes/no, choices, names) |
| `hv/engine.py` → `guided()`, `review()`, `variant()` | The guided talk, the review/correction step, and wording for the mood |
| `hv/skills.py` | Skills worth learning: courses the person can take whose gap is small (same trade) or moderate (a neighbouring trade), at most 12 weeks, that pay more or reach a higher NSQF level |
| `hv/card.py` | The card file (`cards\<id>.svg` and a print page). The QR holds only `HUNARVAANI:<id>` |
| `hv/prompts.py` | Every spoken line in 3 languages, as pieces; numbers, job titles and districts are pieces too |
| `hv/channels/exotel.py` | Phone: 8 kHz audio, keypad, a key cuts a prompt short, simple voice-activity detection |
| `hv/channels/kiosk.py`, `web/kiosk.html` | Tablet: buttons, keypad, mic (16 kHz), typing, options and ID card with QR, print |
| `hv/store.py`, `web/officer.html`, `web/console.js` | SQLite records and the officer console (login, live call, profiles, policy); officers search by district, name or ID, see the quotes behind every label, approve, refer, edit or erase; every action is in the audit log |
| `hv/explain.py`, `hv/channels/console.py` | Plain-language explanations of every decision (labels, next question, ranking, gates) and the console's live phone-demo call that streams them step by step |
| `data/*.csv` | **Sample** data (59 jobs, 115 courses, 124 centres, 31 districts). Replace with NQR, NCO, SIDH and NCS exports |

## 5b. Dynamic ranking: nothing important is hard-coded

Every number the ranker uses lives in one **policy file** (`config/policy.json`). The defaults and
their meaning are in `config/policy.example.json`. The policy changes in three ways, at three speeds:

| Level | What changes | How |
|---|---|---|
| **The person, during the call** | How much each factor counts for *this* person | Emphasis is a running score built from evidence, not one fixed label. Each piece adds to it: the LLM's label (insists / prefers / neutral / doesnt_care), times how forcefully it was said (`intensity` 0–1), plus a bonus for words like "only", "never", "सिर्फ", "फक्त", plus every repeat mention. The score becomes a smooth multiplier between `min` and `max` (neutral = 1). The daily travel radius shrinks smoothly as the access score grows. If the top two options pull in opposite directions (one closer, one better paid), the call **asks a trade-off question**, and the answer is strong evidence |
| **The district, by officers** | Base weights, gate strength, age bands, radius rule, trade-off settings, how many follow-up questions and how much an answer must matter to be asked (`questions`) | Officer console → *Ranking policy*, for all districts or one. Or `POST /api/policy/ahp` with a pairwise survey: it returns weights and a consistency ratio, and refuses to save if the ratio is above 0.1. Every save is a new version in `config/history/` plus an audit line |
| **Real use, over time** | Base weights and gate strength | `python scripts\learn.py` fits weights to the options people actually chose (conditional logit, pulled towards the current weights, limited to ±10 points a round). It fits gate strength to verified outcomes that officers record with `POST /api/person/<id>/outcome`. A proposal is blocked if it widens the gender gap in better-paid options. It goes live only when an officer activates it |

Every value is checked against safe bounds before use (for example, work gate 0.01–0.95, multiplier
0.2–5). The LLM's labels only ever move a person's multipliers within those bounds. Caste-linked work
(sanitation, tanning, cobbling) is never suggested unless the person brings it up themselves
(`consent_only_codes`).

## 6. Privacy rules built in

- Caste is never asked. No Aadhaar number is stored. The PIN is kept only as a salted hash and locks
  after 3 wrong tries.
- Consent comes first: record and share, plus a separate yes or no for AI training.
- **9 twice** erases the person's profile, answers, options and card file. One audit line remains,
  saying it was erased.
- The card shows name, ID, district, the chosen option and skills to learn. Its QR holds only the ID.
  The PIN is never printed or stored in plain text.
- The kiosk clears the screen 60 seconds after a session ends.

## 7. If something fails

| Problem | Fix |
|---|---|
| `.\install.ps1` "is not recognized" | You are in the wrong folder. Double-click `INSTALL.bat` inside the folder instead |
| Hugging Face `401` / `GatedRepoError` | Log in on huggingface.co, click **Agree** on both model pages, run `INSTALL.bat` again and paste a **Read** token |
| `PyTorch cannot use the GPU` while installing the voice | Update the NVIDIA driver (nvidia.com/drivers), then `.\install.ps1 -OnlyVoices` |
| `pull failed` for the LLM | Update Ollama (the installer tries this), or pick a smaller model: `.\install.ps1 -Model gemma4:e2b-it-qat` |
| LLM check says SLOW (over 8 s) | Set `LLM_MODEL=gemma4:e2b-it-qat` in `.env`, run `ollama pull gemma4:e2b-it-qat`, restart. Close games or apps that use the GPU |
| The kiosk says the same thing back / does not understand speech | Check the RUN window: each answer logs `STT ... : <text>` and `LLM labelled ...`. If the text is empty, speak closer to the mic or raise the volume |
| Kiosk only speaks numbers, or speaks with the browser voice | The voice is not rendered: `.\install.ps1 -OnlyVoices` |
| Kiosk mic does not work | Open the kiosk on `localhost` or over the https tunnel, not `http://192.168...`, and allow the microphone |
| `[Errno 10048]` / port in use | `RUN.bat` picks the next free port and prints it; or `.\run.ps1 -Port 8010` |
| Phone call silent | Render the voice; check that `audio\hi\greet.wav` exists |
| Background noise cut in as speech (phone) | Raise `VAD_THRESHOLD` in `.env` (for example to 800) |

## 8. Not built yet

WhatsApp voice notes · missed-call callback · follow-up calls at 1, 3 and 6 months with outcome checks ·
live TTS for free text (FastPitch) ·
a richer learned ranker (LightGBM, neural network) once thousands of outcomes exist · real government data.
