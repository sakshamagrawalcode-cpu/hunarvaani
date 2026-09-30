"""Cost per person for HunarMarg: Sarvam APIs vs our own fine-tuned open models on Indian GPUs.

Every input is listed below with its source or marked "estimate". Change one and re-run:

    python scripts/cost_model.py

Sources (checked 30 Sep 2026):
  [GIA]   MoSJE PM-AJAY factsheet, 28 Sep 2026: Rs 1,730 crore GIA for 2.5 lakh people since
          FY 2021-22 -> about Rs 69,200 each, about 50,000 people a year
  [V4]    HunarVaani v4 idea file, section 10 (team research): 22.47 phone minutes per person's
          whole journey, Rs 6.58 of Sarvam API use per person, Rs 0.65 of extra checks,
          Rs 48 lakh a year of team + servers, carrier Rs 0.60-1.20 a minute
  [E2E]   E2E Networks price pages: NVIDIA L4 (24 GB) Rs 49/h, L40S (48 GB) Rs 102/h
  [S30B]  Sarvam-30B model card: int4 needs about 20-25 GB, so one L40S (48 GB) holds it with
          room for the KV cache
"""

GIA_PER_PERSON = 69_200  # [GIA]
MINUTES_PER_PERSON = 22.47  # [V4] all calls in one person's journey
CARRIER_LOW, CARRIER_MID, CARRIER_HIGH = 0.60, 0.80, 1.20  # [V4] Rs per minute
API_PER_PERSON = 6.58  # [V4] Sarvam speech-to-text, voice, LLM, messages
EXTRAS_PER_PERSON = 0.65  # [V4] integrity checks and audio fact check (midpoint)
TEAM_AND_SERVERS = 48_00_000  # [V4] Rs a year: 3-person team, CPU servers, content, audit

# Our own models (estimates unless marked)
L4_PER_HOUR, L40S_PER_HOUR = 49, 102  # [E2E]
GPU_HOURS = 12 * 365  # estimate: GPUs on 8 am-8 pm every day; calls outside go to the API
# Calls at once one GPU can serve (estimates, to be measured in the load test):
#   speech-to-text  IndicConformer-600M, batched streaming, caller speaks ~1/3 of the call
#   voice           Indic Parler-TTS Mini, only the changing sentences (fixed prompts pre-rendered)
#   LLM             Sarvam-30B int4 (2.4B active), 1-3 short JSON requests per call
CALLS_PER_GPU = {"stt": ("L4", 100), "tts": ("L4", 25), "llm": ("L40S", 150)}
ML_ENGINEER = 15_00_000  # estimate: one ML engineer a year to run and retrain the models
MESSAGES_PER_PERSON = 1.00  # estimate: SMS and similar that stay paid per use
FALLBACK_SHARE = 0.05  # estimate: 5% of speech still goes to the Sarvam API (night, failover)
PEAK_CALLS_AT_50K = 19  # [V4] 50,000 people x 22.47 min over 300 days x 10 h, 3x peak


def gpu_cost_per_year(people: int) -> float:
    """Enough GPUs of each kind for the peak number of calls at once (at least one each)."""
    peak = PEAK_CALLS_AT_50K * people / 50_000
    price = {"L4": L4_PER_HOUR, "L40S": L40S_PER_HOUR}
    per_hour = sum(
        max(1, -(-peak // capacity)) * price[gpu] for gpu, capacity in CALLS_PER_GPU.values()
    )
    return per_hour * GPU_HOURS


def gpus_needed(people: int) -> dict[str, int]:
    peak = PEAK_CALLS_AT_50K * people / 50_000
    return {job: int(max(1, -(-peak // cap))) for job, (_, cap) in CALLS_PER_GPU.items()}


def api_mode(people: int, carrier: float = CARRIER_MID) -> float:
    return (
        MINUTES_PER_PERSON * carrier
        + API_PER_PERSON
        + EXTRAS_PER_PERSON
        + TEAM_AND_SERVERS / people
    )


def own_models(people: int, carrier: float = CARRIER_MID) -> float:
    variable = (
        MINUTES_PER_PERSON * carrier
        + MESSAGES_PER_PERSON
        + FALLBACK_SHARE * (API_PER_PERSON - MESSAGES_PER_PERSON)
        + EXTRAS_PER_PERSON
    )
    return variable + (TEAM_AND_SERVERS + ML_ENGINEER + gpu_cost_per_year(people)) / people


# One-time cost to add or improve one language (estimates, from [V4] section 10 where marked)
ONE_TIME_PER_LANGUAGE = {
    "100 h of consented phone speech, collected and transcribed twice": 1_60_000,  # [V4] ~1.79 L
    "speech-to-text fine-tune: ~72 GPU-hours on one L40S": 72 * L40S_PER_HOUR,
    "one voice: 12 h studio recording by a local voice artist": 30_000,  # [V4] ~34,400 total
    "voice fine-tune: ~24 GPU-hours on one L40S": 24 * L40S_PER_HOUR,
}
ONE_TIME_SHARED = {
    "LLM LoRA fine-tune: 5,000 story->JSON pairs checked by people": 50_000,
    "LLM LoRA fine-tune: ~16 GPU-hours on one L40S": 16 * L40S_PER_HOUR,
    "occupation matcher + skill tagger: labelling 3,000 sentences": 30_000,
    "matcher + tagger training: ~8 GPU-hours on one L4": 8 * L4_PER_HOUR,
}


def main() -> None:
    print("Cost per person (Rs), carrier Rs 0.80/min")
    print(f"{'people a year':>14} {'Sarvam APIs':>12} {'own models':>11} {'% of GIA (own)':>15}")
    for people in (50_000, 1_00_000, 5_00_000, 10_00_000):
        a, o = api_mode(people), own_models(people)
        print(f"{people:>14,} {a:>12.0f} {o:>11.0f} {100 * o / GIA_PER_PERSON:>14.2f}%")
    lo, hi = own_models(50_000, CARRIER_LOW), own_models(50_000, CARRIER_HIGH)
    alo, ahi = api_mode(50_000, CARRIER_LOW), api_mode(50_000, CARRIER_HIGH)
    print(
        f"\nAt 50,000 a year, carrier Rs 0.60-1.20: own models Rs {lo:.0f}-{hi:.0f}, "
        f"APIs Rs {alo:.0f}-{ahi:.0f}"
    )
    for people in (50_000, 10_00_000):
        print(
            f"GPUs at {people:,} a year: {gpus_needed(people)}, "
            f"Rs {gpu_cost_per_year(people) / 1e5:.2f} lakh"
        )
    per_lang = sum(ONE_TIME_PER_LANGUAGE.values())
    shared = sum(ONE_TIME_SHARED.values())
    print(
        f"\nOne-time: Rs {per_lang / 1e5:.2f} lakh per language + Rs {shared / 1e5:.2f} lakh shared"
    )
    for n in (3, 10, 22):
        print(f"  {n:>2} languages: Rs {(n * per_lang + shared) / 1e5:.1f} lakh")
    b = api_mode(50_000) - own_models(50_000)
    print(f"\nOwn models vs APIs at 50,000: Rs {-b:+.0f} per person")


if __name__ == "__main__":
    main()
