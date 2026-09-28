import re
from collections import Counter

from core.search.seed import load_seed, passage_text, vector_literal

DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def test_seed_has_sixteen_unique_occupations():
    rows = load_seed()
    assert len(rows) == 16
    assert len({r.nco_code for r in rows}) == 16


def test_every_row_has_hindi_title_and_aliases():
    for r in load_seed():
        assert DEVANAGARI.search(r.title_hi), r.nco_code
        assert r.title_en and r.aliases, r.nco_code


def test_no_alias_points_at_two_occupations():
    counts = Counter(a.lower() for r in load_seed() for a in r.aliases)
    assert [a for a, n in counts.items() if n > 1] == []


def test_passage_text_uses_e5_prefix_and_includes_aliases():
    row = next(r for r in load_seed() if r.nco_code == "7531")
    text = passage_text(row)
    assert text.startswith("passage: Tailor, dressmaker.")
    assert "silai" in text and "दर्ज़ी" in text


def test_vector_literal_format():
    assert vector_literal([0.5, -1, 0.25]) == "[0.5000000,-1.0000000,0.2500000]"
