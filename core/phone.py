import hashlib
import hmac
import re

from cryptography.fernet import Fernet

_NON_DIGIT = re.compile(r"\D")


def normalize_indian_mobile(raw: str | None) -> str | None:
    """Return +91XXXXXXXXXX for an Indian mobile number, else None."""
    digits = _NON_DIGIT.sub("", raw or "")
    if len(digits) == 14 and digits.startswith("0091"):
        digits = digits[4:]
    elif len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10 and digits[0] in "6789":
        return "+91" + digits
    return None


def phone_hash(number: str, secret: str) -> str:
    return hmac.new(secret.encode(), number.encode(), hashlib.sha256).hexdigest()


def encrypt(number: str, key: str) -> bytes:
    return Fernet(key.encode()).encrypt(number.encode())


def decrypt(token: bytes, key: str) -> str:
    return Fernet(key.encode()).decrypt(bytes(token)).decode()


def last4(number: str | None) -> str:
    digits = _NON_DIGIT.sub("", number or "")
    return f"xxxxxx{digits[-4:]}" if len(digits) >= 4 else "unknown"
