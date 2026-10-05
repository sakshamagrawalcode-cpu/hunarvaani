"""Sample data (made up for the demo, labelled "sample" everywhere): occupations, courses, centres,
district demand, sectors and schemes. Real use replaces these CSVs with NQR / NCO / SIDH / NCS exports."""

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .config import settings

# Physical load of the work in each sector, 1 (seated) .. 5 (heavy manual). Our starting values,
# to be checked with trainers. A course marked heavy_work=yes is at least 4.
SECTOR_LOAD = {
    "construction": 5, "agriculture": 4, "metal": 4, "logistics": 4, "livestock": 3, "automotive": 3,
    "electrical": 3, "food": 3, "care": 3, "facility": 3, "apparel": 2, "handicraft": 2, "beauty": 2,
    "retail": 2, "electronics": 2, "vishwakarma": 2, "rpl": 2, "entrepreneurship": 1, "it_ites": 1,
}

EDUCATION_ORDER = ["none", "upto_5th", "upto_8th", "10th", "12th", "graduate"]


@dataclass(frozen=True)
class Occupation:
    code: int
    title_en: str
    title_hi: str
    title_mr: str
    sector: str
    skills: tuple[str, ...]
    near: tuple[int, ...]
    loan_scheme: str
    rpl: bool

    def title(self, lang: str) -> str:
        return {"hi": self.title_hi, "mr": self.title_mr}.get(lang, self.title_en)


@dataclass(frozen=True)
class Course:
    course_id: str
    kind: str  # upskill | certificate (RPL) | startup
    nco_codes: tuple[int, ...]  # empty = any trade
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
    district: str
    type: str  # block | pmkk | rseti | iti
    name_en: str
    distance_km: int
    hostel: bool
    women_batches: bool
    sectors: tuple[str, ...]


@dataclass(frozen=True)
class District:
    code: str
    state: str
    name_en: str
    name_hi: str
    name_mr: str

    def name(self, lang: str) -> str:
        return {"hi": self.name_hi, "mr": self.name_mr}.get(lang, self.name_en)


@dataclass(frozen=True)
class Sector:
    code: str
    title_en: str
    title_hi: str
    title_mr: str
    wage_min: int
    wage_max: int

    def title(self, lang: str) -> str:
        return {"hi": self.title_hi, "mr": self.title_mr}.get(lang, self.title_en)


def _rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _codes(text: str) -> tuple[int, ...]:
    return tuple(int(c) for c in text.split("|") if c.strip().isdigit())


def _list(text: str) -> tuple[str, ...]:
    return tuple(t.strip() for t in text.split("|") if t.strip())


class Data:
    def __init__(self, folder: Path):
        names = {int(r["nco_code"]): r for r in _rows(folder / "occupation_names.csv")}
        self.aliases = {int(r["nco_code"]): _list(r["aliases"]) for r in names.values()}
        self.occupations: dict[int, Occupation] = {}
        for r in _rows(folder / "occupations.csv"):
            code = int(r["nco_code"])
            n = names.get(code, {})
            self.occupations[code] = Occupation(
                code, r["title_en"], n.get("title_hi", r["title_en"]), n.get("title_mr", r["title_en"]),
                r["sector"], _list(r["typical_skills"]), _codes(r["near"]), r["loan_scheme"], r["rpl"] == "yes")
        self.courses = [
            Course(r["course_id"], r["kind"], _codes(r["nco_codes"]), r["sector"], r["title_en"],
                   int(r["nsqf_level"]), int(r["hours"]), r["min_education"], int(r["min_age"]), int(r["max_age"]),
                   int(r["fee_inr"]), r["placement"] == "yes", r["heavy_work"] == "yes", _list(r["skills"]),
                   r["scheme"])
            for r in _rows(folder / "courses.csv")]
        self.centres = [
            Centre(r["centre_id"], r["district_code"], r["type"], r["name_en"], int(r["distance_km"]),
                   r["hostel"] == "yes", r["women_batches"] == "yes", _list(r["sectors"]))
            for r in _rows(folder / "centres.csv")]
        self.demand = {(r["district_code"], r["sector"]): r["demand"] for r in _rows(folder / "demand.csv")}
        self.pins: dict[str, District] = {}
        self.districts: dict[str, District] = {}
        for r in _rows(folder / "pin_districts.csv"):
            d = District(r["district_code"], r["state"], r["district_en"], r["district_hi"], r["district_mr"])
            self.pins[r["pin_prefix"]] = d
            self.districts[d.code] = d
        self.sectors = {r["sector"]: Sector(r["sector"], r["title_en"], r["title_hi"], r["title_mr"],
                                            int(r["wage_min"]), int(r["wage_max"]))
                        for r in _rows(folder / "sectors.csv")}
        self.schemes = {r["scheme"]: r for r in _rows(folder / "schemes.csv")}

    def district_for_pin(self, pin: str) -> District | None:
        return self.pins.get((pin or "")[:3])

    def course_sector(self, course: Course) -> str:
        """RPL and toolkit courses are filed under 'rpl'/'vishwakarma'; use the trade's own sector."""
        if course.sector in ("rpl", "vishwakarma") and course.nco_codes:
            occ = self.occupations.get(course.nco_codes[0])
            if occ:
                return occ.sector
        return course.sector

    def load(self, course: Course) -> int:
        load = SECTOR_LOAD.get(self.course_sector(course), 3)
        return max(load, 4) if course.heavy_work else load

    def wage_max(self, sector: str) -> int:
        s = self.sectors.get(sector)
        return s.wage_max if s else 10000

    def centres_for(self, course: Course, district: str) -> list[Centre]:
        return [c for c in self.centres if c.district == district and course.sector in c.sectors]


@lru_cache(maxsize=1)
def get_data() -> Data:
    return Data(settings.data_dir)
