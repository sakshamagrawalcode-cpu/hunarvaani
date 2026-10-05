"""Check every local model on this laptop, one by one, with timings.

  python scripts/check_models.py              # GPU, Ollama + LLM, speech-to-text
  python scripts/check_models.py --wav my.wav # also transcribe your own recording (Hindi)

If the voice has been rendered, the speech-to-text check transcribes one of the rendered Hindi
questions (voice model -> speech-to-text round trip), so you see all three models working together.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hv.config import settings  # noqa: E402

OK, BAD = "PASS", "FAIL"


def step(name: str, fn) -> bool:
    t0 = time.time()
    try:
        note = fn()
        print(f"[{OK}] {name} ({time.time() - t0:.1f}s) {note or ''}", flush=True)
        return True
    except Exception as exc:
        print(f"[{BAD}] {name}: {type(exc).__name__}: {exc}", flush=True)
        return False


def gpu() -> str:
    out = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.used,driver_version",
                          "--format=csv,noheader"], capture_output=True, text=True, timeout=20)
    if out.returncode != 0:
        raise RuntimeError("nvidia-smi failed: update the NVIDIA driver")
    return out.stdout.strip()


def ollama() -> str:
    import httpx

    tags = httpx.get(f"{settings.ollama_url}/api/tags", timeout=5).json()
    names = [m["name"] for m in tags.get("models", [])]
    if not any(n == settings.llm_model or n.startswith(settings.llm_model + ":") for n in names):
        raise RuntimeError(f"{settings.llm_model} not pulled. Run: ollama pull {settings.llm_model}  (have: {names})")
    return f"{settings.llm_model} is available"


def llm() -> str:
    from hv.data import get_data
    from hv.llm import LLM

    model = LLM(get_data(), real=True)
    model.raw_labels("मैं सिलाई करती हूँ।", "ask_story")  # loads the model (raises if Ollama is down)
    text = "मैं पाँच साल से घर पर सिलाई करती हूँ। सिलाई ही सीखनी है, पर घर छोड़कर नहीं जा सकती, बच्चे छोटे हैं।"
    t0 = time.time()
    labels = model.label(text, "ask_story")
    took = time.time() - t0
    if not labels.occupation_codes:
        raise RuntimeError(f"the LLM found no occupation in a clear sentence (rejected: {labels.rejected})")
    note = "" if took < 8 else "  SLOW: try LLM_MODEL=gemma4:e2b-it-qat in .env"
    return (f"one answer labelled in {took:.1f}s: codes={labels.occupation_codes} wants={labels.aspiration_codes} "
            f"years={labels.years} emphasis={[(e['factor'], e['strength']) for e in labels.emphasis]} "
            f"mood={labels.mood}{note}")


def stt(wav: str | None) -> str:
    import numpy as np

    from hv.audio import read_wav, resample
    from hv.stt import STT

    s = STT(real=True)
    s._load()
    source = Path(wav) if wav else settings.audio_dir / "hi" / "ask_story.wav"
    if source.exists():
        x, rate = read_wav(source)
        pcm = resample(x, rate, 16000).tobytes()
        what = source.name
    else:
        pcm = (np.random.randn(32000) * 300).astype(np.int16).tobytes()
        what = "2 s of noise (render the voice to test real speech)"
    t0 = time.time()
    text = s.transcribe(pcm, "hi")
    return f"{what} transcribed in {time.time() - t0:.1f}s on {settings.stt_device}: {text!r}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wav", default=None)
    args = ap.parse_args()
    results = [step("GPU", gpu), step("Ollama", ollama), step("LLM labels", llm),
               step("Speech-to-text (IndicConformer)", lambda: stt(args.wav))]
    print("\nAll good." if all(results) else "\nFix the FAIL lines above (README, section 'If something fails').")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
