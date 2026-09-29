"""The sample recommendation dataset (database/sample/*.csv), loaded once into plain objects.

Every row is made up for the demonstration and labelled as sample; course ids are ours, not
real NSQF qualification pack codes. Scheme names and benefits describe real schemes in simple
words and must be checked against the official sources before any real use.
"""

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "database" / "sample"

# the interview's education answers, lowest first
EDUCATION_ORDER = ("none", "upto_5th", "upto_8th", "10th", "12th", "iti_or_diploma", "graduate")
# the interview's age answers as (youngest, oldest)
AGE_RANGE = {
    "under_18": (0, 17),
    "18_25": (18, 25),
    "26_35": (26, 35),
    "36_45": (36, 45),
    "46_60": (46, 60),
    "over_60": (61, 120),
}
# how far the caller said they can go each day (P10), in km; "hostel" also allows centres
# with a hostel anywhere in the caller's state
TRAVEL_KM = {"village": 5, "10km": 10, "30km": 30, "district_hq": 60, "hostel": 60}


def _pipe(value: str) -> tuple[str, ...]:
    return tuple(v.strip() for v in value.split("|") if v.strip())


def _yes(value: str) -> bool:
    return value.strip().lower() == "yes"


@dataclass(frozen=True)
class Sector:
    sector: str
    title_en: str
    title_hi: str
    title_mr: str
    wage_min: int
    wage_max: int


@dataclass(frozen=True)
class Scheme:
    scheme: str
    name_en: str
    name_hi: str
    name_mr: str
    kind: str
    benefit_en: str
    eligibility_en: str


@dataclass(frozen=True)
class Occupation:
    nco_code: str
    title_en: str
    sector: str
    typical_skills: tuple[str, ...]
    near: tuple[str, ...]
    loan_scheme: str
    rpl: bool


@dataclass(frozen=True)
class Course:
    course_id: str
    kind: str  # upskill | certificate | startup
    nco_codes: tuple[str, ...]  # ("*",) = any occupation
    sector: str
    title_en: str
    nsqf_level: int
    hours: int
    min_education: str
    min_age: int
    max_age: int
    fee_inr: int
    placement: bool
    heavy_work: bool
    skills: tuple[str, ...]
    scheme: str


@dataclass(frozen=True)
class Centre:
    centre_id: str
    district_code: str
    type: str  # block | pmkk | rseti | iti
    name_en: str
    distance_km: int  # typical distance from villages in the district (sample)
    hostel: bool
    women_batches: bool
    sectors: tuple[str, ...]


@dataclass(frozen=True)
class Dataset:
    sectors: dict[str, Sector]
    schemes: dict[str, Scheme]
    occupations: dict[str, Occupation]
    courses: tuple[Course, ...]
    centres: tuple[Centre, ...]
    demand: dict[tuple[str, str], str]  # (district, sector) -> high | low; else medium
    district_state: dict[str, str]

    def demand_level(self, district: str | None, sector: str) -> str:
        return self.demand.get((district or "", sector), "medium")


def _rows(name: str, folder: Path) -> list[dict[str, str]]:
    with (folder / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=2)
def load(folder: Path = SAMPLE_DIR) -> Dataset:
    sectors = {
        r["sector"]: Sector(
            r["sector"],
            r["title_en"],
            r["title_hi"],
            r["title_mr"],
            int(r["wage_min"]),
            int(r["wage_max"]),
        )
        for r in _rows("sectors.csv", folder)
    }
    schemes = {
        r["scheme"]: Scheme(
            r["scheme"],
            r["name_en"],
            r["name_hi"],
            r["name_mr"],
            r["kind"],
            r["benefit_en"],
            r["eligibility_en"],
        )
        for r in _rows("schemes.csv", folder)
    }
    occupations = {
        r["nco_code"]: Occupation(
            r["nco_code"],
            r["title_en"],
            r["sector"],
            _pipe(r["typical_skills"]),
            _pipe(r["near"]),
            r["loan_scheme"],
            _yes(r["rpl"]),
        )
        for r in _rows("occupations.csv", folder)
    }
    courses = tuple(
        Course(
            r["course_id"],
            r["kind"],
            _pipe(r["nco_codes"]),
            r["sector"],
            r["title_en"],
            int(r["nsqf_level"]),
            int(r["hours"]),
            r["min_education"],
            int(r["min_age"]),
            int(r["max_age"]),
            int(r["fee_inr"]),
            _yes(r["placement"]),
            _yes(r["heavy_work"]),
            _pipe(r["skills"]),
            r["scheme"],
        )
        for r in _rows("courses.csv", folder)
    )
    centres = tuple(
        Centre(
            r["centre_id"],
            r["district_code"],
            r["type"],
            r["name_en"],
            int(r["distance_km"]),
            _yes(r["hostel"]),
            _yes(r["women_batches"]),
            _pipe(r["sectors"]),
        )
        for r in _rows("centres.csv", folder)
    )
    demand = {(r["district_code"], r["sector"]): r["demand"] for r in _rows("demand.csv", folder)}
    district_state = {r["district_code"]: r["state"] for r in _rows("pin_districts.csv", folder)}
    return Dataset(sectors, schemes, occupations, courses, centres, demand, district_state)
