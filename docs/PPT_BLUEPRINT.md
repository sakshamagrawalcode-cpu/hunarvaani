# HunarMarg: final PPT blueprint (SIH 2026, 6 slides)

The deck describes the **final system**, built from scratch. The prototype appears only once, as
proof on slide 4. Models are named by the open model we fine-tune. [Sx] = source tag (slide 6);
* = needs a government MoU.

## Theme (slides 2–6)
- Off-white background · navy headings · **saffron** for big numbers and key words · teal for tech.
- Poppins headings (28–32 pt), Inter text (14–16 pt, never below 12), big numbers 40 pt+.
- Each slide = **3 bands at most**, one idea per box, one emoji per box, no paragraphs.
- Small grey source tag under every number. Rounded boxes, lots of white space.
- Thin dotted "path" line along the bottom of slides 2–6 (Marg = path), one dot lit per slide.
- Speaker notes hold the detail; the slide holds the headline.

---

## Slide 1: Title
Official template, no design. PS ID SIH26097 · title as on the portal · theme · Software ·
Team ID · Team Name.

---

## Slide 2: Proposed solution
**Title:** HunarMarg: one free phone call from skill to verified livelihood

**Band 1: the problem (1 card + 3 numbers)**
> 😟 A form picks the course, not the person: SC job seekers land in training that doesn't fit.

| **41%** | **51.6%** | **66.1%** |
|---|---|---|
| of certified trainees got placed [S5] | of rural women have no phone of their own [S2] | SC literacy: forms fail many [S1] |

**Band 2: how it works, end to end (5 steps with arrows)**
1. 📞 **Missed call → free callback** from a govt 1600 number*, in his language. No app, no reading.
2. 🔢🗣️ **Keys for facts, voice for skills.** Age, education, distance by keypad; then he describes his work.
3. 🧾 **Complete profile, made by AI.** Skills mapped to NCO codes and NSQF QPs; read back, he presses 1.
4. 🎯 **3 pathways that fit.** Training, RPL certificate, apprenticeship or own work, each with a dated plan and money path (GIA, NSFDC, PM Vishwakarma).
5. 📅 **Stays till he earns.** SMS with case ID + documents; reminders; follow-up calls at 1, 3, 6 months.

**Band 3: why it's different (one combined box, 6 tiles, 2 rows × 3)**

| | |
|---|---|
| 📞 **Any keypad phone** · missed call, free, own language | 📚 **Never invented** · every fact from govt data; checked before it is spoken |
| 🧾 **Writes the profile itself** · officers only review and approve | 💰 **Money path** · which loan or grant fits, and the monthly EMI |
| 🛡️ **Outcomes that can't be faked** · random-digit liveness, employer check | 🧠 **Learns from verified jobs only** · fake placements can't teach it |

**Footer:** One call → the right skill → a verified livelihood.

---

## Slide 3: Technical approach
**Band 1: tech stack (4 groups, logos)**

| 📞 Calls & messages | 🧠 AI models (we fine-tune) | ⚙️ Backend & data | 🏛️ Apps & govt links |
|---|---|---|---|
| Exotel · 1600 number* · SMS | IndicConformer-600M (speech → text) · Indic Parler-TTS (voice) · Sarvam-30B (reads the story) · MuRIL (skill tagger) · multilingual-e5 + BM25 (job search) · LightGBM (ranker) · Satyavaani (liveness) | Python · FastAPI · PostgreSQL + pgvector · Redis · Docker · Indian GPU cloud | React console · NCO-2015 · NQR · DigiLocker* · AJAY app* |

**Band 2: how it works, two lanes**

① **During the call** (seconds; keypad turns instant)
📱 Phone → 📞 Exotel callback → 🎙️ IndicConformer → 🏷️ MuRIL + 🧠 Sarvam-30B (fills a form, job codes only) → 🔍 e5 job search → ✅ "you said…", caller confirms → ⚖️ LightGBM ranker on 🗂️ govt data (NCO, NQR courses, centres, schemes, demand) → ✔️ fact check → 🔊 Indic Parler-TTS says 3 options.
Dashed: 🔁 GPU down → Sarvam API · 🙋 AI stuck → human counsellor.

② **After the call** (days, people)
🧾 Profile → FastAPI case → 🗄️ PostgreSQL (audit log) → 💬 SMS case ID + documents → 🏛️ officer approves on console / AJAY app* → 📅 follow-ups at 1, 3, 6 months + 🛡️ Satyavaani → ✅ verified outcomes → 🧠 ranker retrained monthly.

One line: **AI understands → data and rules decide → facts checked → humans approve**

**Band 3: 6 model cards (name = the model we fine-tune)**

| Card | Works | Trains | Target |
|---|---|---|---|
| 🎙️ IndicConformer-600M | 22 languages; 8 kHz phone audio → text; job-name list helps | 100 h consented calls per language, transcribed twice + IndicVoices made phone-like; ~72 GPU-h | Hindi error ≤ 20% |
| 🔊 Indic Parler-TTS | 21 languages; text + "calm, slow, clear voice" → speech | 12 h of one local voice artist per language; ~24 GPU-h | Listeners ≥ 4/5 |
| 🧠 Sarvam-30B | Fills a fixed form: job codes from our list, years, skills; never advises | LoRA on 5,000 story → form pairs checked by people; ~16 GPU-h | Right job in top 3 ≥ 90% |
| 🔍 multilingual-e5 + BM25 | Keyword + meaning score → top 20 → reranker → top 3 | Every "1" at read-back = right pair, "none" = wrong pair | Right job in top 5 ≥ 90% |
| ⚖️ LightGBM LambdaRank | Filters, then 6 factors: wish, skills held, demand, reach, completion, income | Starts on officer-set weights (AHP); then learns from verified jobs at 6 months only | Gender gap ≤ 5 pts |
| 🛡️ Satyavaani (team's own) | 4 random digits + fake-voice score; no voiceprint | Retrain on Indian phone speech + 3 cloning tools | Flag, never reject |

Data rules (one grey line): no Aadhaar number stored · caste never asked · consent logged (DPDP
Rules 2025) · raw audio deleted after confirmation · every edit in the audit log · data in India.

---

## Slide 4: Feasibility and viability
**Headline:** Can it be built and run? Yes: every part already runs in India, our prototype
works, and it costs 0.24% of what GIA spends per person.

**Band 1: proof (4 cards + 1 prototype card)**
- 📱 **22 crore** feature-phone users: the channel exists [S10]
- ☎️ **3 crore+** women reached by Kilkari, a govt voice-call line; answer rate 50% → 76% by the 3rd try [S11]
- 🎙️ **22 / 21 languages**: open Indian speech and voice models already exist [S13]
- 🎯 **19.3%** error: best Indian speech AI on IndicVoices; our bar before we switch [S12]
- 🧪 **Our prototype:** real calls in 3 languages · profile + read-back · top 3 options from 115
  courses, 124 centres · team console · measured on **N** real calls [S17]

**Band 2: training and cost (4 final numbers)**

| **₹163** | **0.24%** | **₹8.8 L / yr** | **₹2 L** |
|---|---|---|---|
| per person, all-in, at 50,000 a year | of ₹69,200 GIA support per person | GPUs in India (2× L4 + 1× L40S) | one time per language (100 h data + voice + GPU) |

Small chart: cost per person falls with scale: ₹163 → ₹94 → ₹39 → ₹32 (50k → 1 L → 5 L → 10 L a
year) [S15][S16][S17].
Training timeline strip: 📥 collect 100 h → 🔧 fine-tune (~112 GPU-h) → ✅ beat 19.3% → 🔁 monthly.

**Band 3: what could go wrong → what handles it**
- ✗ Village dialects → ✓ keys for facts, every answer read back, human fallback
- ✗ AI says something wrong → ✓ only facts that match a govt data row are spoken
- ✗ Unknown numbers ignored → ✓ he calls first; callback from an official 1600 number*
- ✗ Our model worse than paid APIs → ✓ switch a language only after it beats 19.3%; API as backup

---

## Slide 5: Impact and benefits
**Headline:** Who gains? SC families, officers, training centres and the Ministry.

**Band 1: 4 numbers**
- 🎯 **41% → 70%** placed: the gap we target (CAG found 41%; 70% is the GIA target) [S5][S4]
- 🤝 **62% → 73%** stay in the job when told real pay and place before joining; HunarMarg tells them on the call [S12a]
- ⏱️ **109 min** officer time saved per person ≈ 52 staff-years a year *(our estimate)*
- 💸 **₹44,136** saved on one woman's ₹80,000 tailoring unit with the right money path *(our calculation)*

Reach line: **~50,000** GIA beneficiaries a year [S3] · starts in **47,243** Adarsh Gram villages [S3].

**Band 2: who gains what (4 cards)**
- 🤝 **Social** (SC families, women, non-readers): right course first time, free, own language; women-only batches; calls until earning
- 💰 **Economic** (Ministry and trainee): 0.24% extra per person so the other 99.76% goes to the right course; the cheapest loan path
- 🏛️ **Governance** (officers, CSCs): ready profiles, one case record from call to job, demand data for the annual plan
- 🌱 **Environment** (every district): no paper forms, fewer trips to offices

**Footer:** Pilot: 6–8 blocks, ~540 people per group, results in 6 months.

---

## Slide 6: Research and references
**Band 1: sources by type (4 columns, short lines + site)**
- 📊 **Government:** S1 Census 2011 (MoSJE Handbook 2021) · S2 NSO Telecom survey 2025 · S3 MoSJE PM-AJAY factsheet, 28 Sep 2026 · S4 PM-AJAY guidelines · S5 CAG Report No. 20 of 2025 · S6 NCO-2015 · S7 NQR · S8 NSFDC · S9 PIB PM Vishwakarma
- 🔬 **Research:** S10 Business Standard 2026 (feature phones) · S11 BMJ Global Health (Kilkari) · S12a Chakravorty et al., J-PAL (job information → retention)
- 💻 **Technology:** S12 Sarvam Saaras v3 benchmark · S13 AI4Bharat IndicConformer, IndicVoices, Indic Parler-TTS · S14 Sarvam-30B open weights · S15 E2E Networks GPU prices · S16 Sarvam pricing, carrier rates
- 📜 **Policy:** DPDP Rules 2025 · TRAI 1600 series · CERT-In directions

**Band 2: "See more" (4 cards with QR codes)**
🐙 GitHub repo (code, `docs/MODELS.md`) · 📞 prototype number / demo · 🎬 demo video (unlisted,
no login) · 🧮 calculations (`scripts/cost_model.py`) [S17]

Credits line: ideas borrowed from SkillCall, VoicePath, Kaushal Saathi, Sahayak, Saksham, MSOL.

---

## Before exporting
- [ ] "N real calls" on slide 4 from `measure.py`, or write "measurement plan"
- [ ] Exotel per-minute rate checked (cost assumes ₹0.60–1.20)
- [ ] Every number has a source tag or "our estimate"
- [ ] * on everything that needs a government MoU (1600 number, DigiLocker, AJAY app)
- [ ] QR codes work without login
- [ ] Name on the call matches the slides (the call still says "HunarVaani")
