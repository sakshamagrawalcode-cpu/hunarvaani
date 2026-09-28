import csv
from dataclasses import dataclass
from pathlib import Path

SEED_PATH = Path(__file__).resolve().parents[2] / "data" / "nco_seed.csv"


@dataclass(frozen=True)
class NcoRow:
    nco_code: str
    title_en: str
    title_hi: str
    aliases: tuple[str, ...]


def load_seed(path: Path = SEED_PATH) -> list[NcoRow]:
    with open(path, encoding="utf-8", newline="") as f:
        return [
            NcoRow(
                nco_code=r["nco_code"].strip(),
                title_en=r["title_en"].strip(),
                title_hi=r["title_hi"].strip(),
                aliases=tuple(a.strip() for a in r["aliases"].split("|") if a.strip()),
            )
            for r in csv.DictReader(f)
        ]


def passage_text(row: NcoRow) -> str:
    return f"passage: {row.title_en}. {row.title_hi}. {', '.join(row.aliases)}"


def vector_literal(vec) -> str:
    return "[" + ",".join(f"{float(x):.7f}" for x in vec) + "]"
