# HunarMarg: our models, how they work, how we train them, what they cost

The final system runs **its own fine-tuned open models on Indian GPUs**. Sarvam's APIs stay as a
fallback at night and when a GPU fails. The prototype today uses the Sarvam APIs for speech,
voice and the LLM (🟢 = in the prototype, ⚪ = planned). Costs come from `scripts/cost_model.py`,
which lists every input with its source.

## 1. The three open base models (all Indian, all free to use commercially)

| Job | Base model | Why this one | Languages | Licence |
|---|---|---|---|---|
| 🎙️ Speech → text | **IndicConformer-600M-multilingual** (AI4Bharat, IIT Madras) | India's first open ASR for all 22 scheduled languages; trained on IndicVoices (23.7k h, 51k speakers, 400+ districts) | 22 | MIT |
| 🔊 Text → voice | **Indic Parler-TTS Mini** (AI4Bharat + Hugging Face) | Most languages of any open Indic TTS; voice set by a text description (no cloning of real people); trained on 1,806 h | 21 (20 Indic + English) | Apache 2.0 |
| 🧠 Reading the story | **Sarvam-30B** (Sarvam AI) | Mixture of experts: 30B total, only 2.4B active per word, so it is fast; state of the art in 22 Indian languages for its size; int4 fits one 48 GB GPU | 22 | Apache 2.0 |

Also open: multilingual-e5 (search), MuRIL (tagger), LightGBM (ranker), Silero VAD (speech
detection), IndicTrans2 (English summary for officers). Sarvam's own Saaras v3 reports 19.3%
WER on IndicVoices (10 languages); our fine-tuned IndicConformer must match that on phone audio
before it replaces the API for a language.

## 2. Each model: how it works (one line) and how we train it

| # | Model | How it works | How we train it | Pass mark | Now |
|---|---|---|---|---|---|
| 1 | 🎙️ **HunarMarg STT** | Conformer encoder (convolution + attention) turns 8 kHz audio into letters; a word list of occupation names biases decoding | Fine-tune IndicConformer on IndicVoices downsampled to 8 kHz with phone-codec noise, plus 100 h per language of our own consented calls, transcribed twice; ~72 GPU-hours on one L40S | WER ≤ 20% (Hindi) on our phone test set | ⚪ (Sarvam Saaras 🟢) |
| 2 | 🔊 **HunarMarg Voice** | Text + a description ("a calm female voice, slow, clear") → audio tokens → 8 kHz speech | Fine-tune Parler-TTS Mini on 12 h of one consenting local voice artist per language; ~24 GPU-hours | Local listeners ≥ 4/5; voice → STT round trip WER ≤ 10% | ⚪ (Bulbul 🟢) |
| 3 | 🧠 **Story Reader** (LLM) | Reads the story and fills a fixed JSON form: occupation codes (from our list only), years, skills, job/own work, a short "you said" sentence; never gives advice | LoRA fine-tune of Sarvam-30B on 5,000 story → JSON pairs (our consented calls + synthetic stories per occupation × language, all checked by people); ~16 GPU-hours | 100% valid JSON; right occupation in top 3 ≥ 90% | 🟢 (Sarvam 105B API, same job) |
| 4 | 🔍 **Occupation Matcher** | Score = keyword match (BM25) + meaning match (e5 cosine); top 20 → reranker → top 3 read back | Contrastive fine-tuning on caller phrase ↔ occupation pairs; every caller who presses 1 at the read-back gives a positive pair, "none" gives a hard negative | Right occupation in top 5 ≥ 90% | 🟢 hybrid search; ⚪ fine-tune |
| 5 | 🏷️ **Skill Tagger** | Marks words in the story as EDUCATION / SKILL / YEARS / TRAVEL / WANT (BIO tags); the LLM's answer must point at these words | Fine-tune MuRIL on 3,000 labelled sentences (Hindi, Marathi, English) | Span F1 ≥ 0.85 | ⚪ |
| 6 | ⚖️ **HunarMarg Ranker** | Hard filters (age, travel ×1.5, health, education) → score = 25A + 20S + 20D + 15X + 10C + 10U (wish, skills held, local demand, reach, completion, income gain) | Phase 1: weights agreed with district officers by AHP (pairwise comparison, consistency ratio < 0.1). Phase 2 (after ~5,000 six-month outcomes): LightGBM LambdaRank, labels 0 = offered not picked … 4 = verified working at 6 months, only outcomes that passed the checks; blend α × rules + (1 − α) × learned | Beats Phase 1 on NDCG@3; gender gap in higher-wage offers ≤ 5 points | 🟢 rules (5 factors); ⚪ learned |
| 7 | 🧭 **Lean Model** | Points per answer → softmax (T = 3.5) → job / own work / business shares | Later: logistic regression on what callers actually chose | Read-back accepted ≥ 80% | 🟢 keypad question |
| 8 | ❓ **Smart Skill Check** | Asks the question that most reduces uncertainty about the right course (expected information gain over the course's NOS criteria) | Probabilities from past answers per course | 1–2 fewer questions, same decision | ⚪ |
| 9 | 📉 **Dropout Alert** | Logistic regression on distance, attendance, follow-up answers → risk score | Trained on enrolment → outcome records | Catches ≥ 70% of dropouts | ⚪ |
| 10 | 🛡️ **Satyavaani** (team's own) | Caller repeats 4 random digits + a fake-voice score; flags, never rejects; no voiceprint stored | Retrain on Indian phone speech and ≥ 3 voice-cloning tools | Today 4.6% EER on 6 speakers | ⚪ |

Rule for all of them: **code and rules decide; the LLM only reads.** Every spoken fact comes from
the dataset.

## 3. Cost (from `scripts/cost_model.py`, carrier ₹0.80/min unless noted)

| People a year | Sarvam APIs | Our own models | Own models, % of ₹69,200 GIA |
|---|---|---|---|
| 50,000 (today's GIA volume) | ₹121 | **₹163** | 0.24% |
| 1 lakh | ₹73 | ₹94 | 0.14% |
| 5 lakh | ₹35 | ₹39 | 0.06% |
| 10 lakh | ₹30 | ₹32 | 0.05% |

- At 50,000 a year with carrier ₹0.60–1.20/min: own models **₹159–172**, APIs ₹117–130.
- GPUs at 50,000 a year: 1 L4 (speech-to-text) + 1 L4 (voice) + 1 L40S (LLM), 12 h a day =
  **₹8.76 lakh a year**. At 10 lakh a year: 20 L4 + 3 L40S = ₹56.3 lakh.
- One-time per language: **₹2.0 lakh** (100 h of phone speech, a voice artist, GPU time), plus
  ₹0.82 lakh shared (LLM, matcher, tagger). 3 languages ₹6.8 lakh · 10 languages ₹20.8 lakh ·
  all 22 ₹44.8 lakh.

**Honest reading:** our own models cost ₹42 more per person in the pilot and about the same at
state scale. They are not chosen to save money; they are chosen for 22 languages (Sarvam's voice
covers fewer), tuning to phone audio and dialects, callers' voices never leaving our servers,
and no dependence on one vendor's prices.

## Sources

- IndicConformer: huggingface.co/ai4bharat/indic-conformer-600m-multilingual (22 languages, MIT)
- IndicVoices: arxiv.org/abs/2403.01926; huggingface.co/datasets/ai4bharat/IndicVoices
- Indic Parler-TTS: huggingface.co/ai4bharat/indic-parler-tts (21 languages, 1,806 h)
- Sarvam-30B / 105B open weights: sarvam.ai/blogs/sarvam-30b-105b; huggingface.co/sarvamai/sarvam-30b
- Saaras v3 benchmark (19.31% WER, IndicVoices, 10 languages): sarvam.ai/blogs/asr
- GPU prices: e2enetworks.com (L4 ₹49/h, L40S ₹102/h)
- Journey minutes, API cost, team budget, carrier range: HunarVaani v4 idea file, section 10
- GIA per person: MoSJE PM-AJAY factsheet, 28 Sep 2026
