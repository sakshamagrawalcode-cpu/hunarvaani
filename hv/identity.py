"""HunarVaani ID (9 digits, last one a check digit, easy to type on a keypad) and the PIN the
person sets. The PIN is stored only as a salted PBKDF2 hash. No Aadhaar number is ever stored."""

import hashlib
import hmac
import secrets

PIN_LEN = 4
MAX_PIN_TRIES = 3


def _luhn_digit(digits: str) -> str:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return str((10 - total % 10) % 10)


def new_id() -> str:
    body = str(secrets.randbelow(9 * 10**7) + 10**7)  # 8 digits, no leading zero
    return body + _luhn_digit(body)


def valid_id(hv_id: str) -> bool:
    return len(hv_id) == 9 and hv_id.isdigit() and _luhn_digit(hv_id[:8]) == hv_id[8]


def pretty(hv_id: str) -> str:
    return f"{hv_id[:4]}-{hv_id[4:8]}-{hv_id[8:]}" if len(hv_id) == 9 else hv_id


def hash_pin(pin: str, salt: bytes | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, 200_000)
    return salt.hex(), digest.hex()


def check_pin(pin: str, salt_hex: str, hash_hex: str) -> bool:
    _, digest = hash_pin(pin, bytes.fromhex(salt_hex))
    return hmac.compare_digest(digest, hash_hex)


def valid_pin(pin: str | None) -> bool:
    return bool(pin) and len(pin) == PIN_LEN and pin.isdigit()
