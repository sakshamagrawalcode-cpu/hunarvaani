"""Render every spoken piece to audio/<lang>/<key>.wav with Indic Parler-TTS (once, on the GPU).

  python scripts/render_audio.py                 # all languages, only new or changed pieces
  python scripts/render_audio.py --langs hi       # Hindi only
  python scripts/render_audio.py --only greet     # one piece (all languages)
  python scripts/render_audio.py --force          # re-render everything
  python scripts/render_audio.py --fake           # quick placeholder tones, no GPU (for testing the phone line)

Listen to the results; if a piece sounds wrong, change its text in hv/prompts.py and run again
(only changed pieces are rendered). For a different voice, edit VOICES below.
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hv.audio import to_int16, write_wav  # noqa: E402
from hv.config import settings  # noqa: E402
from hv.data import get_data  # noqa: E402
from hv.prompts import all_pieces, speakable  # noqa: E402

VOICES = {
    "hi": "Divya speaks in a warm, friendly and slightly expressive tone at a slightly slow pace with a moderate "
          "pitch. The recording is very clear and close-sounding, with no background noise.",
    "mr": "Sunita speaks in a warm, friendly and slightly expressive tone at a slightly slow pace with a moderate "
          "pitch. The recording is very clear and close-sounding, with no background noise.",
    "en": "Mary speaks in a warm, friendly and slightly expressive tone at a slightly slow pace with a moderate "
          "pitch and an Indian accent. The recording is very clear and close-sounding, with no background noise.",
}


def digest(text: str, lang: str) -> str:
    return hashlib.sha1(f"{VOICES[lang]}|{speakable(text, lang)}".encode()).hexdigest()[:12]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", default="hi,mr,en")
    ap.add_argument("--only", default="")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--fake", action="store_true", help="placeholder tones instead of speech (no GPU)")
    args = ap.parse_args()

    pieces = all_pieces(get_data())
    model = tok = desc_tok = device = None
    if not args.fake:
        import torch
        from parler_tts import ParlerTTSForConditionalGeneration
        from transformers import AutoTokenizer

        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        if device == "cpu":
            print("WARNING: no CUDA GPU visible to PyTorch; rendering on the CPU is very slow.")
        else:
            print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"loading {settings.tts_model} on {device} (first time: downloads about 4 GB) ...")
        model = ParlerTTSForConditionalGeneration.from_pretrained(settings.tts_model).to(device)
        tok = AutoTokenizer.from_pretrained(settings.tts_model)
        desc_tok = AutoTokenizer.from_pretrained(model.config.text_encoder._name_or_path)

    for lang in [x.strip() for x in args.langs.replace(" ", ",").split(",") if x.strip()]:
        folder = settings.audio_dir / lang
        folder.mkdir(parents=True, exist_ok=True)
        manifest_path = folder / "_manifest.json"
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        todo = {k: t for k, t in pieces[lang].items() if (not args.only or k == args.only)}
        done = 0
        need = [k for k, t in todo.items() if args.force or not (folder / f"{k}.wav").exists()
                or manifest.get(k) != digest(t, lang) + ("-fake" if args.fake else "")]
        print(f"{lang}: {len(need)} of {len(todo)} pieces to render")
        started = time.time()
        for key, text in todo.items():
            path = folder / f"{key}.wav"
            h = digest(text, lang) + ("-fake" if args.fake else "")
            if key not in need:
                continue
            t0 = time.time()
            if args.fake:
                rate = 16000
                n = int(rate * min(4.0, 0.25 + 0.06 * len(text)))
                t = np.arange(n) / rate
                audio = (np.sin(2 * np.pi * 440 * t) * 600).astype(np.int16)
            else:
                import torch

                d = desc_tok(VOICES[lang], return_tensors="pt").to(device)
                pr = tok(speakable(text, lang), return_tensors="pt").to(device)
                with torch.inference_mode():
                    gen = model.generate(input_ids=d.input_ids, attention_mask=d.attention_mask,
                                         prompt_input_ids=pr.input_ids, prompt_attention_mask=pr.attention_mask)
                audio = to_int16(gen.cpu().numpy().squeeze())
                rate = model.config.sampling_rate
            write_wav(path, audio, rate)
            manifest[key] = h
            done += 1
            left = (time.time() - started) / done * (len(need) - done)
            print(f"[{done}/{len(need)}, ~{left / 60:.0f} min left] {lang}/{key}.wav {time.time() - t0:.1f}s  {text[:50]}")
            manifest_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
        manifest_path.write_text(json.dumps(manifest, indent=1, ensure_ascii=False))
        print(f"{lang}: {done} rendered, {len(todo) - done} already up to date")


if __name__ == "__main__":
    main()
