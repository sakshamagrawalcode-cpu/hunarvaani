# HunarVaani: what we submit (idea PDF, video, finale)

This file updates the three planning files (v4 idea, PPT plan, build guide) with what is
**actually built**. Use it for the six slides and the demo video. Rule for every slide and every
spoken line: claim only what the prototype does; mark sample data as sample; mark plans as plans.

Numbers marked **[measure]** come from `scripts/measure.py` run on our own saved calls (section 6).
Write the real call count next to them ("measured on N real calls"). Never write "30 calls"
unless 30 calls were made.

---

## 1. The idea in one paragraph

HunarVaani is a free, voice-first livelihood counsellor for SC beneficiaries under the GIA
component of PM-AJAY. A person calls from any keypad phone and talks in Hindi, English or
Marathi. They answer a few short keypad questions, then describe their work in their own words.
HunarVaani understands that description, maps it to NCO occupations and NSQF-aligned courses,
and offers three realistic options on the same call: training, a certificate for skills they
already have, or help to start their own work with the right scheme or loan. The caller hears
each option in detail and picks one. They get a reference number and a list of documents to
bring. District teams see every call, the caller's own words and the options on one console.

**Tagline:** "One call. Your own words. The right skill."

## 2. The three differentiators (same words on slides 2, 3 and 5)

| # | Differentiator | Status to show |
|---|---|---|
| 1 | **Works from any keypad phone, in the caller's own words.** No app, no form, no reading needed | **Built**: a real phone call; voice + keypad; 3 languages. Pilot: a free missed call → callback |
| 2 | **Advice from rules and government data, never invented.** | **Built**: code picks the options from the dataset; only dataset facts are spoken; the LLM only reads the story and must answer with codes from our list of 59 |
| 3 | **Outcomes that are checked, not just claimed.** | **Design** (not built): follow-up calls, random-digit check, employer confirmation |

## 3. What changed since the v4 idea file

| v4 said | Now |
|---|---|
| Plivo number, missed call → callback | Exotel number; the caller dials in and enters a PIN. Missed call → callback is blocked by Exotel's business KYC, so it stays the pilot plan |
| SMS with the top 3 | A spoken **reference number** (said twice) + the **documents list** (Aadhaar, bank passbook, education certificate, 2 photos, caste/income certificate if they have one) + "never pay anyone" |
| Pipecat voice server | Our own FastAPI websocket server for Exotel Voicebot |
| Tagger + LLM | Word search (BM25 + multilingual e5) + **Sarvam LLM (India-hosted)** that reads the story: occupations, years of experience, skills, a clean "you said…" sentence |
| Top 2 read back | **3 occupations** read back; the caller confirms or tells it again (up to 3 tries) |
| Top 3 with dated plan + money path | **Top 3 options** with reasons + skill gap (console); the scheme / loan route is named; press the option's number to **hear details**; **no dates or EMI yet** |
| Skill check | Not built; years of experience and skills come from the story |
| — | **Review step**: the caller hears their answers and can change any one |
| — | **District from PIN code**; never skips a question and never hangs up on silence ("stay on the line" while it works) |
| Officer dashboard, 6 roles | **Team console** (one password): live call view, options, CSV export, district filter, sample data page, voice prompts page |
| Real NQR QP data | **Sample dataset**: 59 occupations, 115 courses, 124 centres in 31 districts, demand, 9 real schemes |

## 4. Honesty table (slide 6)

| Real and working | Sample data (marked on screen) | Not built yet / needs a department |
|---|---|---|
| Real calls on an Indian number (Exotel) | Courses, centres, demand in 31 districts | Missed call → free callback (needs KYC or a 1600 number) |
| Hindi, English, Marathi: speech-to-text, translation, speech (Sarvam, India) | Occupation ↔ course mapping | SMS |
| Consents in simple words (recording, sharing, AI training) | PIN → district table (demo region) | Follow-up calls + outcome checks |
| Keypad profile: age, gender, education, travel, difficulty, PIN, job or own work | | Dated plan, EMI / money-path maths |
| Review + change any answer | | Skill-check questions |
| Work story → occupation (word search + India-hosted LLM) → read-back of 3 | | Officer approve / modify actions, role logins |
| Recommender: top 3 with reasons and skill gap; option details; choice saved | | Satyavaani liveness check |
| Reference number, documents, closing | | Real QP / seat data, DigiLocker |
| Team console, CSV export | | Word error rate on labelled calls |

## 5. Demo video (about 3 minutes)

Setup: the phone on speaker beside the laptop showing `/console/` → the call page. Real audio
only, English subtitles, no music over speech. Put "SAMPLE DATA" as a caption whenever the
options card is on screen. Record 3–4 takes and keep the cleanest one.

| Time | On screen | Heard / subtitle |
|---|---|---|
| 0:00–0:15 | A keypad phone in a hand; one problem number with its source | "Many SC job seekers cannot use apps or forms. So we built HunarVaani." |
| 0:15–0:35 | Dialling + PIN; the console's live log starts | Language menu → greeting → consent |
| 0:35–1:00 | Keypad answers; the PIN appears as a district on the console | Age, gender, education, travel, difficulty, PIN, job or own work |
| 1:00–1:15 | Review panel on the console | Review; change one answer |
| 1:15–1:50 | Processing panel: transcript → English → "AI understood" (occupation, years, skills) | The caller tells their work; "stay on the line"; "you said…" + 3 occupations; press 1 |
| 1:50–2:25 | Options card with reasons + skill gap (**SAMPLE DATA**) | 3 options (time, fee, distance); press a number to hear details; choose one |
| 2:25–2:40 | Ref badge on the call page | Reference number twice, documents, "never pay anyone" |
| 2:40–2:55 | Calls list, district filter, CSV | "Code decides, from real schemes and data. The AI only listens." |
| 2:55–3:10 | Honesty table + next steps | "Next: missed-call callback, follow-ups that check outcomes, a one-district pilot." |

## 6. Numbers for slide 3 (from our own calls)

On the laptop, after the rehearsal calls:

```powershell
git pull
docker compose -f infra/docker-compose.yml up -d --build
docker compose -f infra/docker-compose.yml logs api > api.log
Get-Content api.log | docker compose -f infra/docker-compose.yml exec -T api python scripts/measure.py --log -
```

Add `--since 2026-09-30` to leave out old test calls, or `--min-seconds 30` to leave out calls
that were only connection tests. The script prints, each with its own count:

- how far calls got (answered → consents → questions → story → read-back → options → chosen → goodbye);
- calls that ended early and why;
- speech-to-text and search time; **how long the caller waited after the story**;
- **how often the caller confirmed one of the 3 occupations** (and how often it was the first);
- options offered, details heard, option chosen, kinds of options;
- how late Exotel played prompts (from the log).

Slide 3 box "Measured by us" (fill from the output):

> "Measured on **N** real calls: **X of Y** callers confirmed their occupation in the read-back;
> the caller waited a median of **W s** after telling their story; prompts played **L s** after
> sending (median). Word error rate on labelled calls: measurement plan."

Known already, from the 30 Sep call: one full 230-second call (every step, end to end);
prompts played about 1.1 s after sending (1.0 s of that is our own send-ahead).

We have **no word error rate**: that needs each call's words typed out by hand and compared.
Write "measurement plan" for it; do not estimate it.

## 7. Six slides (pitch name: **HunarMarg**)

Rules: light, not crowded, no paragraphs. One emoji or icon per box, one idea per box, at most
about 40 words of body text per slide. Numbers are big; the source is a small grey tag under
each one. Green dot = in the prototype, grey dot = planned.

**Theme (all slides):** off-white background; navy headings; **saffron/orange** for key numbers;
teal for tech; green = built, grey = planned. Headings in Poppins, body text in Inter. A thin
dotted "path" line (Marg = path) runs along the bottom of slides 2–6, with a dot for each slide.

| Slide | What it holds | Look |
|---|---|---|
| 1 Title | Official template only: PS ID SIH26097, title as on the portal, theme, Software, Team ID, Team Name | Unchanged; no design |
| 2 Idea | Problem in 1–2 lines · the idea as 4 points with emojis · 3 boxes: ⭐ what makes us different, 🧩 features, ✅ already working | Problem strip on top, 4 idea points, 3 equal boxes |
| 3 Tech | Flow chart in 4 coloured zones (Listen → Understand → Decide → Speak and follow up), plus a row of logos for every technology the final system uses (green/grey dots) | Flow chart fills 70% of the slide; logos underneath |
| 4 Proof and feasibility | 2×2 grid: 🌐 proven online · 🧪 our prototype · 💰 cost and scale · ⚠️ risks → fixes | 3 items per box at most; one small bar picture (₹69,200 vs ₹134) |
| 5 Impact | 4 big numbers · "who benefits" cards (caller, women, officers, centres, banks, ministry) · social / economic / environment line | Numbers on top, cards in the middle |
| 6 Sources | Sources grouped with icons (govt data, studies, tech, our own work) · a small honesty strip · QR codes for GitHub and the video | Two columns, QR codes at the bottom |

New online sources added to the v4 list: 22 crore feature-phone users (Business Standard,
Apr 2026) · Kilkari, MoHFW's voice-call programme: over 3 crore women reached, answer rate 50%
at the first try and 76% by the third (BMJ Global Health) · Sarvam Saaras v3, the model we use:
19.3% word error rate on IndicVoices across 10 languages (Sarvam's own benchmark).

## 8. Final build plan to propose

| When | What |
|---|---|
| Done (prototype) | Everything in the first column of section 4 |
| Next 2 weeks | Server in India (Azure Central India, `docs/DEPLOY.md`); more rehearsal calls in all 3 languages; typed-out transcripts of 20 calls for a word error rate |
| Weeks 3–8 (before the finale) | Missed call → callback (KYC or a partner number); SMS summary; a dated plan + money path (loan amount, EMI) for each option; officer actions (approve / ask for info / refer) on the console; one follow-up call with the random-digit check |
| Pilot (with the department) | 6–8 blocks, about 540 people per group, results at 6 months; real course, seat and employer data per district; a 1600 number; DigiLocker; recommender weights agreed with district officers; Satyavaani retrained on Indian phone speech before any use |
| After about 5,000 checked outcomes | Learned ranker trained only on outcomes that passed the checks |

What we need from the ministry: a 1600 number, district course / seat data, DigiLocker access,
and one district for the pilot.

## 9. Before recording

1. New keys for everything pasted in chat earlier (Sarvam, Exotel, console password).
2. `git pull`, then `docker compose -f infra/docker-compose.yml up -d --build`.
3. `init_db.py` in the worker container (schema 09).
4. Sarvam credits, then `python scripts\render_prompts.py`.
5. One rehearsal call per language; check `/console/`.
6. Run `measure.py` (section 6) and fill slide 3.
