"""Speech to text with AI4Bharat IndicConformer-600M, on this laptop. Language is fixed per call.

The model is a set of ONNX files run by ONNX Runtime. By default it runs on the CPU (STT_DEVICE=cpu),
which leaves the whole GPU to the LLM: right for 8 GB cards such as the RTX 5050. With a bigger GPU
and onnxruntime-gpu installed, STT_DEVICE=cuda moves it to the GPU.

IndicConformer covers 22 Indian languages but not English; English answers go to faster-whisper if it
is installed, otherwise to the Hindi model (fine for Hinglish, weak for pure English).
"""

import logging
import os
import threading
import time

import numpy as np

from .config import settings

log = logging.getLogger("hv.stt")


def _pin_onnx_device() -> None:
    """Make every ONNX Runtime session use the device we chose, whatever the model's own code asks for."""
    import onnxruntime as ort

    if getattr(ort.InferenceSession, "_hv_pinned", False):
        return
    original = ort.InferenceSession
    available = ort.get_available_providers()
    if settings.stt_device == "cuda" and "CUDAExecutionProvider" in available:
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    else:
        if settings.stt_device == "cuda":
            log.warning("STT_DEVICE=cuda but onnxruntime has no CUDA here (%s); using the CPU", available)
        providers = ["CPUExecutionProvider"]
    threads = int(os.environ.get("STT_THREADS", "0")) or max(1, (os.cpu_count() or 4) - 1)

    class Pinned(original):  # a subclass, so isinstance checks in the model code still work
        _hv_pinned = True

        def __init__(self, path_or_bytes, sess_options=None, providers_=None, *args, **kwargs):
            kwargs.pop("providers", None)
            kwargs.pop("provider_options", None)
            so = sess_options or ort.SessionOptions()
            so.intra_op_num_threads = threads
            super().__init__(path_or_bytes, sess_options=so, providers=providers)

    ort.InferenceSession = Pinned
    log.info("speech-to-text on %s (%d CPU threads)", providers[0], threads)


class STT:
    def __init__(self, real: bool | None = None):
        self.real = settings.models == "real" if real is None else real
        self._model = None
        self._whisper = None
        self._lock = threading.RLock()
        self._failed: str | None = None

    def _load(self):
        with self._lock:
            if self._model is None:
                if self._failed:
                    raise RuntimeError(f"speech-to-text could not load earlier: {self._failed}")
                import torch  # noqa: F401  (imported here so the fake mode needs no torch)
                from transformers import AutoModel

                _pin_onnx_device()
                log.info("loading %s (first time: downloads about 2.5 GB) ...", settings.stt_model)
                try:
                    self._model = AutoModel.from_pretrained(settings.stt_model, trust_remote_code=True)
                except Exception as exc:
                    self._failed = f"{type(exc).__name__}: {exc}"
                    log.error("speech-to-text failed to load: %s", self._failed)
                    raise
                log.info("speech-to-text ready")
            return self._model

    def _english(self, audio: np.ndarray) -> str | None:
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            return None
        if self._whisper is None:
            self._whisper = WhisperModel("small", device="cpu", compute_type="int8")
        segments, _ = self._whisper.transcribe(audio, language="en")
        return " ".join(s.text.strip() for s in segments)

    def transcribe(self, pcm16k: bytes, lang: str) -> str:
        """16 kHz 16-bit mono PCM -> text. Returns '' in fake mode (the kiosk can type instead)."""
        if not self.real or len(pcm16k) < 3200:
            return ""
        audio = np.frombuffer(pcm16k, dtype=np.int16).astype(np.float32) / 32768.0
        peak = float(np.abs(audio).max()) if audio.size else 0.0
        if peak < 0.01:  # silence: nothing to transcribe (saves seconds of CPU)
            return ""
        if 0.0 < peak < 0.3:  # quiet microphones: bring speech up to a normal level
            audio = audio * (0.3 / peak)
        t0 = time.time()
        with self._lock:  # one transcription at a time
            if lang == "en":
                text = self._english(audio)
                if text is not None:
                    return text.strip()
                lang = "hi"
            import torch

            model = self._load()
            wav = torch.from_numpy(audio).unsqueeze(0)
            text = model(wav, lang, settings.stt_decoding)
        text = (text if isinstance(text, str) else str(text)).strip()
        log.info("STT %s %.1fs audio in %.1fs: %s", lang, len(audio) / 16000, time.time() - t0, text[:120])
        return text

    def warm_up(self) -> bool:
        if not self.real:
            return True
        try:
            self._load()
            self.transcribe((np.random.randn(16000) * 200).astype(np.int16).tobytes(), "hi")
            return True
        except Exception as exc:
            log.error("speech-to-text warm-up failed: %s", exc)
            return False
