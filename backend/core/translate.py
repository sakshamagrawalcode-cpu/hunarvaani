"""Sarvam translation, used to show the team the caller's words in English.

Only for the console: a failure never affects the call.
"""

import requests

TRANSLATE_URL = "https://api.sarvam.ai/translate"


class TranslateError(RuntimeError):
    pass


def to_english(text: str, language: str, api_key: str, timeout: int = 15) -> str:
    """The English translation of `text` (spoken in `language`, e.g. hi-IN)."""
    if not text or language == "en-IN":
        return text
    if not api_key:
        raise TranslateError("SARVAM_API_KEY is empty")
    try:
        resp = requests.post(
            TRANSLATE_URL,
            headers={"api-subscription-key": api_key, "content-type": "application/json"},
            json={
                "input": text[:1000],
                "source_language_code": language,
                "target_language_code": "en-IN",
                "model": "sarvam-translate:v1",
            },
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise TranslateError(f"could not reach Sarvam: {type(exc).__name__}") from None
    if resp.status_code != 200:
        raise TranslateError(f"Sarvam translate HTTP {resp.status_code}: {resp.text[:200]}")
    return (resp.json().get("translated_text") or "").strip()
