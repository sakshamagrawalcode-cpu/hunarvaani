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
- **Heading style (from the SkillCall deck):** each band opens with a CAPS label in navy, then a
  lighter one-line explanation on the same line, e.g. "THE SOLUTION  one free call, about 10
  minutes, on any keypad phone". Each slide has a one-line question headline under the title
  ("Can it be built and run? Yes: …"). Numbered steps = bold title + grey subline + one sentence.
  Team name top-left, slide number top-right on every slide.

---

## Slide 1: Title
Official template, no design. PS ID SIH26097 · title as on the portal · theme · Software ·
Team ID · Team Name.

---

## Slide 2: Proposed solution
**Title:** HunarMarg: one free phone call from skill to verified livelihood

**Band 1 heading:** THE PROBLEM  a form picks the course, not the person
> 😟 A form picks the course, not the person: SC job seekers land in training that doesn't fit.

| **41%** | **51.6%** | **66.1%** |
|---|---|---|
| of certified trainees got placed [S5] | of rural women have no phone of their own [S2] | SC literacy: forms fail many [S1] |

**Band 2 heading:** THE SOLUTION  one free call on any keypad phone, guided end to end
1. 📞 **Missed call → free callback** from a govt 1600 number*, in his language. No app, no reading.
2. 🔢🗣️ **Keys for facts, voice for skills.** Age, education, distance by keypad; then he describes his work.
3. 🧾 **Complete profile, made by AI.** Skills mapped to NCO codes and NSQF QPs; read back, he presses 1.
4. 🎯 **3 pathways that fit.** Training, RPL certificate, apprenticeship or own work, each with a dated plan and money path (GIA, NSFDC, PM Vishwakarma).
5. 📅 **Stays till he earns.** SMS with case ID + documents; reminders; follow-up calls at 1, 3, 6 months.

**Band 3 heading:** WHY IT WORKS WHERE A FORM FAILS  six things only HunarMarg does (one combined box, 6 tiles)

| | |
|---|---|
| 📞 **Any keypad phone** · missed call, free, own language | 📚 **Never invented** · every fact from govt data; checked before it is spoken |
| 🧾 **Writes the profile itself** · officers only review and approve | 💰 **Money path** · which loan or grant fits, and the monthly EMI |
| 🛡️ **Outcomes that can't be faked** · random-digit liveness, employer check | 🧠 **Learns from verified jobs only** · fake placements can't teach it |

**Footer:** One call → the right skill → a verified livelihood.

---

## Slide 3: Technical approach
**Band 1 heading:** TECH STACK  Indian and open-source, fine-tuned by us

| 📞 Calls & messages | 🧠 AI models (we fine-tune) | ⚙️ Backend & data | 🏛️ Apps & govt links |
|---|---|---|---|
| Exotel · 1600 number* · SMS | IndicConformer-600M (speech → text) · Indic Parler-TTS (voice) · Sarvam-30B (reads the story) · MuRIL (skill tagger) · multilingual-e5 + BM25 (job search) · LightGBM (ranker) · Satyavaani (liveness) | Python · FastAPI · PostgreSQL + pgvector · Redis · Docker · Indian GPU cloud | React console · NCO-2015 · NQR · DigiLocker* · AJAY app* |

**Band 2 heading:** HOW IT WORKS  two lanes: during the call (AI, seconds) and after it (people, days)

① **During the call** (seconds; keypad turns instant)
📱 Phone → 📞 Exotel callback → 🎙️ IndicConformer → 🏷️ MuRIL + 🧠 Sarvam-30B (fills a form, job codes only) → 🔍 e5 job search → ✅ "you said…", caller confirms → ⚖️ LightGBM ranker on 🗂️ govt data (NCO, NQR courses, centres, schemes, demand) → ✔️ fact check → 🔊 Indic Parler-TTS says 3 options.
Dashed: 🔁 GPU down → Sarvam API · 🙋 AI stuck → human counsellor.

② **After the call** (days, people)
🧾 Profile → FastAPI case → 🗄️ PostgreSQL (audit log) → 💬 SMS case ID + documents → 🏛️ officer approves on console / AJAY app* → 📅 follow-ups at 1, 3, 6 months + 🛡️ Satyavaani → ✅ verified outcomes → 🧠 ranker retrained monthly.

One line: **AI understands → data and rules decide → facts checked → humans approve**

**Band 3 heading:** OUR MODELS  what each one does, how we train it, the bar it must pass

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

**Band 1 heading:** ALREADY WORKING IN INDIA  nothing here is untested
- 📱 **22 crore** feature-phone users: the channel exists [S10]
- ☎️ **3 crore+** women reached by Kilkari, a govt voice-call line; answer rate 50% → 76% by the 3rd try [S11]
- 🎙️ **22 / 21 languages**: open Indian speech and voice models already exist [S13]
- 🎯 **19.3%** error: best Indian speech AI on IndicVoices; our bar before we switch [S12]
- 🧪 **Our prototype:** real calls in 3 languages · profile + read-back · top 3 options from 115
  courses, 124 centres · team console · measured on **N** real calls [S17]

**Band 2 heading:** WHAT IT COSTS  four final numbers; every rate is in the calculations

| **₹163** | **0.24%** | **₹8.8 L / yr** | **₹2 L** |
|---|---|---|---|
| per person, all-in, at 50,000 a year | of ₹69,200 GIA support per person | GPUs in India (2× L4 + 1× L40S) | one time per language (100 h data + voice + GPU) |

Small chart: cost per person falls with scale: ₹163 → ₹94 → ₹39 → ₹32 (50k → 1 L → 5 L → 10 L a
year) [S15][S16][S17].
Training timeline strip: 📥 collect 100 h → 🔧 fine-tune (~112 GPU-h) → ✅ beat 19.3% → 🔁 monthly.

**Band 3 heading:** WHAT COULD GO WRONG, AND WHAT ALREADY HANDLES IT
- ✗ Village dialects → ✓ keys for facts, every answer read back, human fallback
- ✗ AI says something wrong → ✓ only facts that match a govt data row are spoken
- ✗ Unknown numbers ignored → ✓ he calls first; callback from an official 1600 number*
- ✗ Our model worse than paid APIs → ✓ switch a language only after it beats 19.3%; API as backup

---

## Slide 5: Impact and benefits
**Headline:** Who gains? SC families, officers, training centres and the Ministry.

**Band 1 heading:** WHAT CHANGES  four numbers, each with its source
- 🎯 **41% → 70%** placed: the gap we target (CAG found 41%; 70% is the GIA target) [S5][S4]
- 🤝 **62% → 73%** stay in the job when told real pay and place before joining; HunarMarg tells them on the call [S12a]
- ⏱️ **109 min** officer time saved per person ≈ 52 staff-years a year *(our estimate)*
- 💸 **₹44,136** saved on one woman's ₹80,000 tailoring unit with the right money path *(our calculation)*

Reach line: **~50,000** GIA beneficiaries a year [S3] · **47,000+** SC-majority villages already on the PM-AJAY dashboard [S9a].

**Band 2 heading:** WHO GAINS WHAT  social · economic · governance · environment
- 🤝 **Social** (SC families, women, non-readers): right course first time, free, own language; women-only batches; calls until earning
- 💰 **Economic** (Ministry and trainee): 0.24% extra per person so the other 99.76% goes to the right course; the cheapest loan path
- 🏛️ **Governance** (officers, CSCs): ready profiles, one case record from call to job, demand data for the annual plan
- 🌱 **Environment** (every district): no paper forms, fewer trips to offices

**Footer:** Pilot: 6–8 blocks, ~540 people per group, results in 6 months.

---

## Slide 6: Research and references
**Band 1 heading:** SOURCES  by type, each with its website
- 📊 **Government:** S1 Census 2011 (MoSJE Handbook 2021) · S2 NSO Telecom survey 2025 · S3 MoSJE PM-AJAY factsheet, 28 Sep 2026 · S4 PM-AJAY guidelines · S5 CAG Report No. 20 of 2025 (56 lakh certified, 41% placed) · S6 NCO-2015 · S7 NQR · S8 NSFDC · S9 PIB PM Vishwakarma · S9a PIB: PM-AJAY portal and AJAY app launch, 26 May 2026
- 🔬 **Research:** S10 Business Standard 2026 (feature phones) · S11 BMJ Global Health (Kilkari) · S12a Chakravorty et al., J-PAL (DDU-GKY, Bihar and Jharkhand: job information → retention 62% → 73%)
- 💻 **Technology:** S12 Sarvam Saaras v3 benchmark · S13 AI4Bharat IndicConformer, IndicVoices, Indic Parler-TTS · S14 Sarvam-30B open weights · S15 E2E Networks GPU prices · S16 Sarvam pricing, carrier rates
- 📜 **Policy:** DPDP Rules 2025 (notified 14 Nov 2025) · TRAI 1600 series for government-to-citizen calls · CERT-In directions

**Band 2 heading:** SEE MORE  code, prototype, video and every calculation, one scan each
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
