import os
from dataclasses import dataclass


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    return int(raw) if raw else default


def _str(name: str, default: str = "") -> str:
    raw = os.environ.get(name, "").strip()
    return raw if raw else default


@dataclass(frozen=True)
class Settings:
    public_base_url: str
    database_url: str
    redis_url: str
    default_language: str
    second_language: str
    callback_delay_seconds: int
    max_triggers_per_day: int
    daily_call_budget: int
    quiet_hours: str
    plivo_auth_id: str = ""
    plivo_auth_token: str = ""
    plivo_number: str = ""
    phone_hash_secret: str = ""
    phone_enc_key: str = ""


def load_settings() -> Settings:
    return Settings(
        public_base_url=_str("PUBLIC_BASE_URL").rstrip("/"),
        database_url=_str("DATABASE_URL", "postgresql://hv:hv@db:5432/hv"),
        redis_url=_str("REDIS_URL", "redis://redis:6379/0"),
        default_language=_str("DEFAULT_LANGUAGE", "hi-IN"),
        second_language=_str("SECOND_LANGUAGE"),
        callback_delay_seconds=_int("CALLBACK_DELAY_SECONDS", 5),
        max_triggers_per_day=_int("MAX_TRIGGERS_PER_DAY", 3),
        daily_call_budget=_int("DAILY_CALL_BUDGET", 100),
        quiet_hours=_str("QUIET_HOURS", "21:00-09:00"),
        plivo_auth_id=_str("PLIVO_AUTH_ID"),
        plivo_auth_token=_str("PLIVO_AUTH_TOKEN"),
        plivo_number=_str("PLIVO_NUMBER"),
        phone_hash_secret=_str("PHONE_HASH_SECRET"),
        phone_enc_key=_str("PHONE_ENC_KEY"),
    )
