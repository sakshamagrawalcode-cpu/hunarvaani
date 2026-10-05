"""Settings, read once from environment variables (or a .env file next to the project)."""

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for raw in env.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


def _flag(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Settings:
    # "real" = local GPU models; "fake" = rule-based stand-ins (no GPU, for tests and UI work)
    models: str = field(default_factory=lambda: os.environ.get("HV_MODELS", "fake"))
    ollama_url: str = field(default_factory=lambda: os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"))
    llm_model: str = field(default_factory=lambda: os.environ.get("LLM_MODEL", "gemma4:e4b-it-qat"))
    llm_timeout: float = field(default_factory=lambda: float(os.environ.get("LLM_TIMEOUT", "60")))
    stt_model: str = field(
        default_factory=lambda: os.environ.get("STT_MODEL", "ai4bharat/indic-conformer-600m-multilingual"))
    stt_decoding: str = field(default_factory=lambda: os.environ.get("STT_DECODING", "ctc"))
    tts_model: str = field(default_factory=lambda: os.environ.get("TTS_MODEL", "ai4bharat/indic-parler-tts"))
    db_path: Path = field(default_factory=lambda: Path(os.environ.get("HV_DB", str(ROOT / "hunarvaani.db"))))
    audio_dir: Path = field(default_factory=lambda: Path(os.environ.get("HV_AUDIO", str(ROOT / "audio"))))
    data_dir: Path = field(default_factory=lambda: ROOT / "data")
    cards_dir: Path = field(default_factory=lambda: Path(os.environ.get("HV_CARDS", str(ROOT / "cards"))))
    # speech-to-text runs on "cpu" (leaves the GPU to the LLM; right for 8 GB cards) or "cuda"
    stt_device: str = field(default_factory=lambda: os.environ.get("STT_DEVICE", "cpu"))
    llm_ctx: int = field(default_factory=lambda: int(os.environ.get("LLM_CTX", "8192")))
    exotel_token: str = field(default_factory=lambda: os.environ.get("EXOTEL_WS_TOKEN", "change-me"))
    officer_user: str = field(default_factory=lambda: os.environ.get("OFFICER_USER", "officer"))
    officer_password: str = field(default_factory=lambda: os.environ.get("OFFICER_PASSWORD", "change-me"))
    # phone speech capture: RMS above this counts as voice; stop after this much silence
    vad_threshold: int = field(default_factory=lambda: int(os.environ.get("VAD_THRESHOLD", "500")))
    silence_seconds: float = field(default_factory=lambda: float(os.environ.get("SILENCE_SECONDS", "1.6")))
    max_speech_seconds: float = field(default_factory=lambda: float(os.environ.get("MAX_SPEECH_SECONDS", "25")))
    key_timeout: float = field(default_factory=lambda: float(os.environ.get("KEY_TIMEOUT", "10")))
    max_options: int = field(default_factory=lambda: int(os.environ.get("MAX_OPTIONS", "5")))
    # location "per device": a kiosk sets its PIN code once on the device (kiosk page settings);
    # DEVICE_PINCODE is the default for kiosks that have not; PHONE_PINCODE is the phone line's area
    device_pincode: str = field(default_factory=lambda: os.environ.get("DEVICE_PINCODE", ""))
    phone_pincode: str = field(default_factory=lambda: os.environ.get("PHONE_PINCODE", ""))
    log_turns: bool = field(default_factory=lambda: _flag("LOG_TURNS", True))


settings = Settings()
