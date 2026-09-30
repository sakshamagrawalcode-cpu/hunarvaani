"""Understanding the caller's own words with an India-hosted LLM (Sarvam chat completions).

Given the work story (the transcript and its English translation) and our 59 occupations, the
model returns: the occupations the caller most likely does (codes from our list only, best
first), years of experience, skills they mentioned, whether they want a job or their own work,
and one clean sentence in the caller's language saying back what they told us.

It only adds to the word search, never replaces it: if the model is slow, fails, or answers
with anything outside the list, the call goes on exactly as before. Real callers' words go
only to Sarvam (India), as the project rules require; no foreign LLM sees them.
"""

import json
import re

import requests

CHAT_URL = "https://api.sarvam.ai/v1/chat/completions"
LANGUAGE_NAMES = {"hi-IN": "Hindi", "en-IN": "English", "mr-IN": "Marathi"}
MAX_SAID_WORDS = 25


class LlmError(RuntimeError):
    pass


def build_messages(
    transcript: str, transcript_en: str | None, language: str, occupations: list[tuple[str, str]]
) -> list[dict]:
    catalogue = "\n".join(f"{code}: {title}" for code, title in occupations)
    lang = LANGUAGE_NAMES.get(language, "Hindi")
    system = (
        "You help a government phone helpline in India that finds skill training for workers. "
        "Read what the caller said about their work and answer with ONLY one JSON object, no "
        "other text:\n"
        '{"occupations": [up to 3 codes from the list, best first; [] if they did not talk '
        'about work], "years": number of years in this work or null, "skills": [up to 5 short '
        'English phrases for things they said they can do], "wants": "job" or "own_work" or '
        f'null, "said": "one short sentence in {lang}, in the first person, repeating only '
        f'what the caller said about their work, at most {MAX_SAID_WORDS} words"}}\n'
        "Use only codes from this list:\n" + catalogue
    )
    user = f"Caller ({lang}): {transcript}"
    if transcript_en and transcript_en != transcript:
        user += f"\nEnglish translation: {transcript_en}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def parse(content: str, codes: set[str]) -> dict:
    """The model's JSON, checked: unknown codes, odd years and long sentences are dropped."""
    content = re.sub(r"<think>.*?</think>", "", content or "", flags=re.S)
    match = re.search(r"\{.*\}", content, re.S)
    if not match:
        raise LlmError("no JSON in the answer")
    try:
        raw = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise LlmError(f"bad JSON ({exc.msg})") from None
    if not isinstance(raw, dict):
        raise LlmError("the answer is not a JSON object")
    found = [str(c) for c in raw.get("occupations") or [] if str(c) in codes]
    years = raw.get("years")
    years = int(years) if isinstance(years, (int, float)) and 0 < years <= 60 else None
    skills = [str(s)[:60] for s in raw.get("skills") or [] if str(s).strip()][:5]
    wants = raw.get("wants") if raw.get("wants") in ("job", "own_work") else None
    said = str(raw.get("said") or "").strip()
    if len(said.split()) > MAX_SAID_WORDS + 5:
        said = ""
    return {
        "occupations": list(dict.fromkeys(found))[:3],
        "years": years,
        "skills": skills,
        "wants": wants,
        "said": said,
    }


def understand(
    transcript: str,
    transcript_en: str | None,
    language: str,
    occupations: list[tuple[str, str]],
    api_key: str,
    model: str,
    timeout: float = 12,
) -> dict:
    """Ask the model; raises LlmError on any problem (the caller of this ignores it)."""
    if not api_key:
        raise LlmError("SARVAM_API_KEY is empty")
    try:
        resp = requests.post(
            CHAT_URL,
            headers={"api-subscription-key": api_key, "content-type": "application/json"},
            json={
                "model": model,
                "messages": build_messages(transcript, transcript_en, language, occupations),
                "temperature": 0.1,
                "max_tokens": 400,
            },
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise LlmError(f"could not reach Sarvam: {type(exc).__name__}") from None
    if resp.status_code != 200:
        raise LlmError(f"Sarvam chat HTTP {resp.status_code}: {resp.text[:200]}")
    try:
        content = resp.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise LlmError("unexpected answer shape") from None
    return parse(content, {code for code, _ in occupations})
