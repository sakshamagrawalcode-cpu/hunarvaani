# HunarMarg: final PPT blueprint (SIH 2026, 6 slides)

🟢 = working in the prototype · ⚪ = planned · [Sx] = source tag (slide 6)

## Theme (slides 2–6)
- Background off-white; headings navy; **saffron** only for big numbers and key words; teal for
  tech; green 🟢 built; grey ⚪ planned.
- Fonts: Poppins (headings 28–32 pt), Inter (text 14–16 pt, never below 12). Big numbers 40 pt+.
- One emoji or icon per box, one idea per box, no paragraphs, ≤ 40 words of body text per slide.
- Source tags small and grey under each number. Rounded boxes, soft shadow, lots of white space.
- A thin dotted "path" line along the bottom of slides 2–6, one dot lit per slide.

---

## Slide 1: Title
Official template, no design changes. Fill: PS ID **SIH26097** · title exactly as on the portal ·
Theme · Software · Team ID · Team Name (as registered). Idea name if a field exists:
**HunarMarg (हुनरमार्ग)**.

---

## Slide 2: Proposed solution
**Title:** HunarMarg: a free voice counsellor for SC livelihoods under PM-AJAY

**Problem strip (grey, 1 line):**
😟 Many SC job seekers have only a keypad phone and little reading: apps and forms don't reach
them, so skilling support rarely matches the work they already know.
Small tags under it: **51.6%** rural women have no phone of their own [S2] · **66.1%** SC literacy [S1]

**Our idea (4 points):**
- 📞 Call from any keypad phone: no app, no reading
- 🗣️ Tell your work in your own words: Hindi, Marathi, English
- 🧠 AI understands your work and matches it to NCO occupations and NSQF courses
- 🎯 Hear 3 training or work options on the same call, pick one, get a reference number

**Three boxes:**

| ⭐ What makes us different | 🧩 Features | ✅ Working today |
|---|---|---|
| Any keypad phone, your own words | Hear any option in detail | Real phone calls (Exotel) |
| Advice from rules + govt data, never invented | Check and change your answers | 3 languages, voice + keys |
| Outcomes checked, not just claimed ⚪ | District from PIN code | AI reads the story, says it back |
| | Documents list + "never pay anyone" | Top 3 options + live team console |

**Footer:** One call → the right skill → a checked livelihood.

---

## Slide 3: Technical approach
**Top (60%): flow chart, 4 coloured zones, left → right** (small note top-right:
"Prototype runs on Sarvam APIs today; ⚪ = final-design models")

| 🎧 Listen (blue) | 🧠 Understand (purple) | ⚖️ Decide (teal) | 🔊 Speak & follow up (orange) |
|---|---|---|---|
| 📱 Keypad phone → 📞 Exotel (Indian number) 🟢 · missed call ⚪ | 🏷️ Skill Tagger ⚪ | 🗂️ Data: NCO, NSQF courses, centres, schemes, demand 🟢 | 🔈 HunarMarg Voice ⚪ (Bulbul 🟢) |
| 🔢 Keys + 🎙️ voice 🟢 | 🧠 Story Reader: codes only 🟢 | 🚦 Hard filters: age, travel, health, education 🟢 | 📋 3 options + details 🟢 |
| 🎙️ HunarMarg STT ⚪ (Saaras 🟢) | 🔍 Occupation Matcher 🟢 | 🏆 HunarMarg Ranker → top 3 + skill gap 🟢 | 🔖 Ref. number + documents 🟢 |
| 🌐 Translate 🟢 | ✅ Caller confirms "you said…" 🟢 | | 💬 SMS ⚪ · 📅 follow-ups ⚪ · 🛡️ liveness ⚪ |

Side chips: 🖥️ Team console 🟢 · 🔒 Data stays in India · 🔑 **Rules decide, AI only reads**

**Bottom (40%): 6 model cards, 2 rows × 3.** Each card: name · works · trains · target · dot.

| Card | How it works | How we train it | Target |
|---|---|---|---|
| 🎙️ HunarMarg STT ⚪ | IndicConformer-600M (22 languages) turns 8 kHz phone audio into text; job-name list helps | 100 h consented calls per language, transcribed twice + IndicVoices made phone-like; ~72 GPU-h | Hindi error ≤ 20% |
| 🔊 HunarMarg Voice ⚪ | Indic Parler-TTS (21 languages): text + "calm, slow, clear voice" → speech | 12 h of one local voice artist per language; ~24 GPU-h | Listeners ≥ 4/5 |
| 🧠 Story Reader 🟢 | Fills a fixed form: job codes from our list only, years, skills; never advises | Final: Sarvam-30B (open) + LoRA on 5,000 checked story→form pairs; ~16 GPU-h | Right job in top 3 ≥ 90% |
| 🔍 Occupation Matcher 🟢 | Keyword (BM25) + meaning (e5) score → top 20 → reranker → top 3 | Learns from calls: "1" = right pair, "none" = wrong pair | Right job in top 5 ≥ 90% |
| ⚖️ HunarMarg Ranker 🟢 | Filters → score of 6 factors: wish, skills held, demand, reach, completion, income gain | Phase 1 weights set with officers (AHP) · Phase 2 LightGBM on verified jobs at 6 months only | Beats Phase 1; gender gap ≤ 5 pts |
| 🛡️ Satyavaani ⚪ (team's own) | 4 random digits + fake-voice score; no voiceprint stored | Retrain on Indian phone speech + 3 cloning tools | Today 4.6% error (6 speakers) |

Line under cards: ➕ also ours: 🧭 Lean model 🟢 · ❓ Smart skill check ⚪ · 📉 Dropout alert ⚪

**Logo row:** Python · FastAPI · Exotel · Sarvam · AI4Bharat · Hugging Face · PyTorch · LightGBM ·
PostgreSQL + pgvector · Redis · React · Docker · E2E Networks / Azure India

---

## Slide 4: Feasibility and viability
**Layout:** 3 columns + risks strip.

**🌐 It can work (proof)**
- 📱 **22 crore** feature-phone users in India [S10]
- ☎️ **3 crore+** women reached by Kilkari, a govt voice-call service [S11]
- 🔁 Kilkari answer rate **50% → 76%** by the 3rd try: retries matter [S11]
- 🎙️ Open Indian models exist: speech **22** languages, voice **21** [S13]
- 🧪 Our prototype: full real call end to end · "measured on **N** real calls" [S17]

**🏋️ Training plan (4-step timeline)**
1. 📥 Collect 100 h consented phone speech per language
2. 🔧 Fine-tune: STT ~72 GPU-h · voice ~24 GPU-h · Story Reader ~16 GPU-h
3. ✅ Switch a language only after beating **19.3%** error (the paid service's benchmark [S12])
4. 🔁 Improve monthly from confirmed calls

Chip: **₹2 lakh per language, one time** · 3 languages ₹6.8 L · all 22 ₹44.8 L [S17]

**💰 Cost per person (bar chart)**

| People a year | Cost per person | % of ₹69,200 GIA |
|---|---|---|
| 50,000 (today) | **₹163** | **0.24%** |
| 1 lakh | ₹94 | 0.14% |
| 5 lakh | ₹39 | 0.06% |
| 10 lakh | ₹32 | 0.05% |

Thin grey line on the chart: paid-API option (₹121 → ₹30).
Under it: "GPUs ₹8.76 L/yr (2× L4 + 1× L40S, India) · carrier ₹0.60–1.20/min → ₹159–172" [S15][S16]

**⚠️ Risks → fixes (strip)**
🗣️ Speech errors → keys for facts + "you said…" check · 📶 Call drops → server in India ·
🖥️ GPU fails → Sarvam API takes over · 📉 Thin local data → honest "need more info"

---

## Slide 5: Impact and benefits
**Top row, 4 big numbers:**
- 👥 **~50,000** GIA beneficiaries a year [S3]
- ⏱️ **109 min** staff time saved per person ≈ 52 staff-years a year *(our estimate)*
- 💸 **₹44,136** saved on one woman's ₹80,000 tailoring unit with the right loan path *(our calculation)*
- 🎯 **70%** placement target, with outcomes checked [S4]

**Middle, "who benefits" cards:**
- 👨‍🌾 **SC job seeker:** free, own language, right course first time, no middleman
- 👩 **Women:** keypad-only option, "safe to talk?", women-only batches
- 🏛️ **District officers:** ready profiles, less paperwork, one dashboard
- 🏫 **Training centres:** the right trainees, fewer dropouts
- 🏦 **Banks / NSFDC:** better-matched loan applicants ⚪
- 🇮🇳 **Ministry:** real demand data for plans, outcomes it can trust

**Bottom strip:** 🤝 Social: fair, right-first-time advice · 💰 Economic: **0.24%** of the GIA
spend per person · 🌱 Environment: fewer office trips, no paper forms

**Footer:** Pilot: 6–8 blocks, ~540 people per group, results in 6 months.

---

## Slide 6: Research and references
**Left (55%), sources grouped:**

📊 Government data
- S1 Census 2011 via MoSJE Handbook on Social Welfare Statistics 2021
- S2 NSO Comprehensive Modular Survey: Telecom 2025
- S3 MoSJE PM-AJAY factsheet, 28 Sep 2026 (₹1,730 cr, 2.5 lakh beneficiaries)
- S4 PM-AJAY guidelines (70% placement, 30% women)
- S5 CAG Report No. 20 of 2025 (PMKVY audit)
- S6 NCO-2015 · S7 National Qualifications Register · S8 NSFDC schemes · S9 PIB: PM Vishwakarma

🔬 Studies and reports
- S10 Business Standard, Apr 2026: 220 million feature-phone users
- S11 BMJ Global Health: Kilkari reach and answer rates

💻 Technology
- S12 Sarvam: Saaras v3 benchmark (19.31% WER, IndicVoices)
- S13 AI4Bharat: IndicConformer, IndicVoices, Indic Parler-TTS
- S14 Sarvam-30B open weights (Apache 2.0)
- S15 E2E Networks GPU prices (L4 ₹49/h, L40S ₹102/h)
- S16 Sarvam API pricing; carrier rates (team research)

🧮 Our work
- S17 GitHub: prototype code, `docs/MODELS.md`, `scripts/cost_model.py`, `scripts/measure.py`

**Right (45%), honesty strip:**
- 🟢 **Working:** real calls, 3 languages, AI reads the story, top 3 options + details, reference number, team console
- 🟠 **Sample data:** courses, centres, demand (31 districts)
- ⚪ **Planned:** missed-call callback, SMS, own STT/voice/LLM, follow-ups + liveness, learned ranker

**Bottom:** QR GitHub · QR demo video (unlisted, no login) · one line crediting borrowed ideas
(SkillCall, VoicePath, Kaushal Saathi, Sahayak, Saksham, MSOL).

---

## Before exporting
- [ ] N real calls filled on slide 4 (`measure.py`), or write "measurement plan"
- [ ] Exotel per-minute rate checked (cost range assumes ₹0.60–1.20)
- [ ] Every number has a tag or "our estimate"
- [ ] ⚪ on everything not in the prototype
- [ ] Video QR works without login
- [ ] Name on the call matches the slides (the call still says "HunarVaani")
