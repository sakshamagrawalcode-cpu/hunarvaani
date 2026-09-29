"""Caller's district from the 6-digit PIN code.

The demo table (`database/sample/pin_districts.csv`) maps the first three PIN digits to the main
district of that postal area. It is approximate sample data: a real build would use the full
India Post PIN directory.
"""

import csv
from functools import lru_cache
from pathlib import Path

TABLE_PATH = Path(__file__).resolve().parents[2] / "database" / "sample" / "pin_districts.csv"
UNKNOWN = "unknown"


def valid_pin(pin: str) -> bool:
    return len(pin) == 6 and pin.isascii() and pin.isdigit() and pin[0] != "0"


@lru_cache(maxsize=1)
def table(path: Path = TABLE_PATH) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return {r["pin_prefix"]: r for r in csv.DictReader(f)}


def district_for_pin(pin: str) -> dict[str, str] | None:
    """The table row (state, district_code, district_en/hi/mr) for a valid PIN, else None."""
    return table().get(pin[:3]) if valid_pin(pin) else None


def district_name(row: dict[str, str], language: str) -> str:
    key = {"en-IN": "district_en", "mr-IN": "district_mr"}.get(language, "district_hi")
    return row[key]
