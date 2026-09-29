from datetime import datetime, timedelta, timezone

import pytest
from cryptography.fernet import Fernet

from core.phone import decrypt, encrypt, last4, normalize_indian_mobile, phone_hash
from core.timeutil import IST, in_quiet_hours, ist_day, next_allowed


@pytest.mark.parametrize(
    "raw",
    ["919876543210", "+91 98765 43210", "09876543210", "9876543210", "00919876543210"],
)
def test_normalize_accepts_indian_mobiles(raw):
    assert normalize_indian_mobile(raw) == "+919876543210"


@pytest.mark.parametrize(
    "raw",
    ["", None, "14155550123", "915876543210", "98765", "+44 7911 123456", "911234567890"],
)
def test_normalize_rejects_everything_else(raw):
    assert normalize_indian_mobile(raw) is None


def test_hash_is_stable_and_secret_dependent():
    assert phone_hash("+919876543210", "a") == phone_hash("+919876543210", "a")
    assert phone_hash("+919876543210", "a") != phone_hash("+919876543210", "b")
    assert len(phone_hash("+919876543210", "a")) == 64


def test_encrypt_roundtrip_and_no_plaintext():
    key = Fernet.generate_key().decode()
    token = encrypt("+919876543210", key)
    assert b"9876543210" not in token
    assert decrypt(token, key) == "+919876543210"


def test_last4_never_shows_more_than_four_digits():
    assert last4("+919876543210") == "xxxxxx3210"
    assert last4(None) == "unknown"


def ist(h, m=0, day=10):
    return datetime(2026, 10, day, h, m, tzinfo=IST)


@pytest.mark.parametrize(
    "when,quiet",
    [
        (ist(21, 0), True),
        (ist(23, 30), True),
        (ist(3, 0), True),
        (ist(8, 59), True),
        (ist(9, 0), False),
        (ist(14, 0), False),
        (ist(20, 59), False),
    ],
)
def test_quiet_hours_wrap_midnight(when, quiet):
    assert in_quiet_hours(when, "21:00-09:00") is quiet


def test_quiet_hours_empty_spec_is_never_quiet():
    assert in_quiet_hours(ist(23), "") is False


def test_next_allowed_moves_to_nine_am_ist():
    assert next_allowed(ist(22, 15), "21:00-09:00") == ist(9, 0, day=11)
    assert next_allowed(ist(2, 0), "21:00-09:00") == ist(9, 0, day=10)
    assert next_allowed(ist(14, 0), "21:00-09:00") == ist(14, 0)


def test_ist_day_uses_indian_date():
    utc_evening = datetime(2026, 10, 10, 20, 0, tzinfo=timezone.utc)
    assert ist_day(utc_evening) == "2026-10-11"
    assert ist_day(utc_evening - timedelta(hours=2)) == "2026-10-10"
