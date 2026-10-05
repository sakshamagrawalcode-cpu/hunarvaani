"""Local LLM through Ollama (default gemma4:e4b-it-qat). One request per spoken answer, JSON only.

Ollama runs on this laptop (http://127.0.0.1:11434); nothing leaves the machine. The JSON schema is
passed as `format`, so the model can only answer in our shape. Thinking mode is switched off: we
want a quick label, not a long reasoning trace.
"""

import json
import logging
import re
import time

import httpx

from .config import settings
from .data import Data
from .labels import Labels, fake_label, schema, system_prompt, validate

log = logging.getLogger("hv.llm")


def parse_json(content: str) -> dict:
    """The model's answer as a dict. Tolerates code fences or text around the JSON object."""
    content = (content or "").strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", content, re.S)
    if fenced:
        content = fenced.group(1)
    try:
        out = json.loads(content)
        return out if isinstance(out, dict) else {}
    except json.JSONDecodeError:
        start, end = content.find("{"), content.rfind("}")
        if 0 <= start < end:
            try:
                out = json.loads(content[start:end + 1])
                return out if isinstance(out, dict) else {}
            except json.JSONDecodeError:
                pass
    log.warning("LLM did not return JSON: %s", content[:200])
    return {}


class LLM:
    def __init__(self, data: Data, real: bool | None = None):
        self.data = data
        self.real = settings.models == "real" if real is None else real
        from .questions import FOLLOW_UPS  # here, to avoid an import loop

        self._schema = schema(data, FOLLOW_UPS)
        self._system = system_prompt(data, FOLLOW_UPS)
        self._think_ok = True  # older Ollama versions reject the "think" field; then we drop it

    def _chat(self, messages: list[dict], fmt: dict | None) -> str:
        body = {"model": settings.llm_model, "stream": False, "messages": messages, "keep_alive": "30m",
                "options": {"temperature": 0, "num_ctx": settings.llm_ctx}}
        if fmt is not None:
            body["format"] = fmt
        if self._think_ok:
            body["think"] = False
        r = httpx.post(f"{settings.ollama_url}/api/chat", json=body, timeout=settings.llm_timeout)
        if r.status_code == 400 and "think" in r.text and self._think_ok:
            self._think_ok = False
            body.pop("think")
            r = httpx.post(f"{settings.ollama_url}/api/chat", json=body, timeout=settings.llm_timeout)
        r.raise_for_status()
        return r.json().get("message", {}).get("content", "")

    def raw_labels(self, transcript: str, question: str = "", context: dict | None = None) -> dict:
        if not self.real:
            return fake_label(transcript, self.data, question)
        ctx = context or {}
        user = (f"Question asked ({question}): {ctx.get('question_text', '')}\n"
                f"Expected answer: {ctx.get('expect', 'anything about their work and life')}\n"
                f"Already known: {ctx.get('known', 'nothing yet')}\n"
                f"Transcript: {transcript}")
        content = self._chat([{"role": "system", "content": self._system}, {"role": "user", "content": user}],
                             self._schema)
        return parse_json(content)

    def label(self, transcript: str, question: str = "", context: dict | None = None) -> Labels:
        """Labels for one answer; on any LLM failure the call goes on with empty labels."""
        if not transcript.strip():
            return Labels()
        t0 = time.time()
        try:
            raw = self.raw_labels(transcript, question, context)
        except Exception as exc:  # the call must never stop because the LLM is down
            log.warning("LLM failed (%s); continuing without labels. Is Ollama running?", exc)
            raw = {}
        labels = validate(raw, transcript, self.data)
        if self.real:
            log.info("LLM labelled in %.1fs: codes=%s wants=%s emphasis=%s mood=%s next=%s rejected=%s",
                     time.time() - t0, labels.occupation_codes, labels.aspiration_codes,
                     [(e["factor"], e["strength"]) for e in labels.emphasis], labels.mood, labels.follow_up,
                     labels.rejected)
        return labels

    def warm_up(self) -> bool:
        """Load the model into GPU memory and cache the long system prompt, so the first caller does
        not wait. Runs in the background when the server starts in real mode."""
        if not self.real:
            return True
        t0 = time.time()
        try:
            self.raw_labels("मैं सिलाई करती हूँ।", "ask_story")
        except Exception as exc:
            log.error("LLM %s is not answering (%s). Is Ollama running and the model pulled?", settings.llm_model, exc)
            return False
        log.info("LLM %s ready (warm-up %.1fs)", settings.llm_model, time.time() - t0)
        return True
