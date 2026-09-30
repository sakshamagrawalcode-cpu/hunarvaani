import os
from dataclasses import dataclass


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    return int(raw) if raw else default


def _str(name: str, default: str = "") -> str:
    raw = os.environ.get(name, "").strip()
    return raw if raw else default


def _list(name: str, default: str) -> tuple[str, ...]:
    return tuple(x.strip() for x in _str(name, default).split(",") if x.strip())


@dataclass(frozen=True)
class Settings:
    public_base_url: str
    database_url: str
    redis_url: str
    default_language: str
    languages: tuple[str, ...]
    callback_delay_seconds: int
    max_triggers_per_day: int
    daily_call_budget: int
    quiet_hours: str
    plivo_auth_id: str = ""
    plivo_auth_token: str = ""
    plivo_number: str = ""
    phone_hash_secret: str = ""
    phone_enc_key: str = ""
    telephony_provider: str = "exotel"
    exotel_sid: str = ""
    exotel_api_key: str = ""
    exotel_api_token: str = ""
    exotel_subdomain: str = "api.exotel.com"
    exotel_caller_id: str = ""
    exotel_app_id: str = ""
    exotel_ws_token: str = ""
    ivr_timeout_seconds: int = 8
    recordings_dir: str = "/app/recordings"
    vad_threshold: int = 500
    sarvam_api_key: str = ""
    sarvam_speaker: str = ""
    # the longest the call waits for the worker (speech-to-text, search, voice); the caller
    # hears "please stay on the line" every few seconds meanwhile
    story_wait_seconds: float = 90.0
    calls_page_user: str = "admin"
    calls_page_password: str = ""
    record_silence_seconds: float = 2.5
    record_no_speech_seconds: float = 12.0
    # a key this soon after the previous answer is a repeated press, not the next answer
    min_answer_seconds: float = 0.6
    # read the answers back so the caller can change one; reference number + documents at the end
    review_answers: bool = True
    closing_details: bool = True
    # Sarvam's LLM also reads the work story (India-hosted; never a foreign model)
    llm_enabled: bool = True
    llm_model: str = "sarvam-105b-conversations"
    llm_timeout_seconds: float = 12.0


def load_settings() -> Settings:
    return Settings(
        public_base_url=_str("PUBLIC_BASE_URL").rstrip("/"),
        database_url=_str("DATABASE_URL", "postgresql://hv:hv@db:5432/hv"),
        redis_url=_str("REDIS_URL", "redis://redis:6379/0"),
        default_language=_str("DEFAULT_LANGUAGE", "hi-IN"),
        languages=_list("LANGUAGES", "hi-IN,en-IN,mr-IN"),
        callback_delay_seconds=_int("CALLBACK_DELAY_SECONDS", 5),
        max_triggers_per_day=_int("MAX_TRIGGERS_PER_DAY", 3),
        daily_call_budget=_int("DAILY_CALL_BUDGET", 100),
        quiet_hours=_str("QUIET_HOURS", "21:00-09:00"),
        plivo_auth_id=_str("PLIVO_AUTH_ID"),
        plivo_auth_token=_str("PLIVO_AUTH_TOKEN"),
        plivo_number=_str("PLIVO_NUMBER"),
        phone_hash_secret=_str("PHONE_HASH_SECRET"),
        phone_enc_key=_str("PHONE_ENC_KEY"),
        telephony_provider=_str("TELEPHONY_PROVIDER", "exotel").lower(),
        exotel_sid=_str("EXOTEL_SID"),
        exotel_api_key=_str("EXOTEL_API_KEY"),
        exotel_api_token=_str("EXOTEL_API_TOKEN"),
        exotel_subdomain=_str("EXOTEL_SUBDOMAIN", "api.exotel.com"),
        exotel_caller_id=_str("EXOTEL_CALLER_ID"),
        exotel_app_id=_str("EXOTEL_APP_ID"),
        exotel_ws_token=_str("EXOTEL_WS_TOKEN"),
        ivr_timeout_seconds=_int("IVR_TIMEOUT_SECONDS", 8),
        recordings_dir=_str("RECORDINGS_DIR", "/app/recordings"),
        vad_threshold=_int("VAD_THRESHOLD", 500),
        sarvam_api_key=_str("SARVAM_API_KEY"),
        sarvam_speaker=_str("SARVAM_SPEAKER"),
        story_wait_seconds=float(_str("STORY_MAX_WAIT_SECONDS", "90")),
        calls_page_user=_str("CALLS_PAGE_USER", "admin"),
        calls_page_password=_str("CALLS_PAGE_PASSWORD"),
        record_silence_seconds=float(_str("RECORD_SILENCE_SECONDS", "2.5")),
        record_no_speech_seconds=float(_str("RECORD_NO_SPEECH_SECONDS", "12")),
        min_answer_seconds=float(_str("MIN_ANSWER_SECONDS", "0.6")),
        review_answers=_str("REVIEW_ANSWERS", "true").lower() in ("1", "true", "yes"),
        closing_details=_str("CLOSING_DETAILS", "true").lower() in ("1", "true", "yes"),
        llm_enabled=_str("LLM_ENABLED", "true").lower() in ("1", "true", "yes"),
        llm_model=_str("SARVAM_LLM_MODEL", "sarvam-105b-conversations"),
        llm_timeout_seconds=float(_str("LLM_TIMEOUT_SECONDS", "12")),
    )
