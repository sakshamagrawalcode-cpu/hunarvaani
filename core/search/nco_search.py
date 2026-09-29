"""Occupation search: alias match + BM25 + multilingual-e5 cosine, as in the build spec.

combined = 0.4 * alias + 0.3 * normalised BM25 + 0.3 * cosine; below 0.35 means "not sure".
"""

from dataclasses import dataclass

import numpy as np
from rank_bm25 import BM25Okapi
from rapidfuzz import fuzz

from core.search.text import content_tokens, is_devanagari, normalise, to_latin

THRESHOLD = 0.35
ALIAS_MIN_RATIO = 85
W_ALIAS, W_BM25, W_COSINE = 0.4, 0.3, 0.3
BM25_FULL = 10.0
# multilingual-e5 cosines bunch up between ~0.7 and ~0.95, so stretch that band to 0..1.
# Tune with scripts/calibrate_search.py on real transcripts.
COSINE_LOW, COSINE_HIGH = 0.78, 0.90


@dataclass(frozen=True)
class Occupation:
    code: str
    title_en: str
    title_hi: str
    aliases: tuple[str, ...]
    embedding: np.ndarray | None = None
    title_mr: str = ""


@dataclass(frozen=True)
class Candidate:
    code: str
    title_en: str
    title_hi: str
    score: float
    alias: float
    bm25: float
    cosine: float
    title_mr: str = ""


def _alias_hit(alias: str, text: str, tokens: set[str]) -> bool:
    a = normalise(alias)
    if not a:
        return False
    if len(a) <= 4 and " " not in a:
        return a in tokens
    return fuzz.partial_ratio(a, text) >= ALIAS_MIN_RATIO


class NcoIndex:
    def __init__(self, occupations: list[Occupation]):
        self.occupations = occupations
        docs = []
        for o in occupations:
            names = o.aliases + (o.title_hi, o.title_mr)
            words = normalise(f"{o.title_en} {' '.join(names)}")
            latin = to_latin(" ".join(a for a in names if is_devanagari(a)))
            docs.append(content_tokens(words) + content_tokens(latin))
        self.bm25 = BM25Okapi(docs)

    def search(self, transcript: str, query_vec=None, top_k: int = 2) -> list[Candidate]:
        dev = normalise(transcript)
        lat = to_latin(transcript) if is_devanagari(transcript) else dev
        dev_tokens, lat_tokens = set(dev.split()), set(lat.split())
        if not (dev or lat):
            return []

        query = sorted(set(content_tokens(dev)) | set(content_tokens(lat)))
        bm25 = (
            np.array(self.bm25.get_scores(query), dtype=float)
            if query
            else np.zeros(len(self.occupations))
        )
        bm25n = np.clip(bm25 / BM25_FULL, 0, 1)

        results = []
        for i, o in enumerate(self.occupations):
            alias = 0.0
            for a in o.aliases + (o.title_hi, o.title_mr):
                text, tokens = (dev, dev_tokens) if is_devanagari(a) else (lat, lat_tokens)
                if _alias_hit(a, text, tokens):
                    alias = 1.0
                    break
            cosine = 0.0
            if query_vec is not None and o.embedding is not None:
                raw = float(np.dot(query_vec, o.embedding))
                cosine = float(np.clip((raw - COSINE_LOW) / (COSINE_HIGH - COSINE_LOW), 0, 1))
            score = W_ALIAS * alias + W_BM25 * float(bm25n[i]) + W_COSINE * cosine
            results.append(
                Candidate(
                    o.code,
                    o.title_en,
                    o.title_hi,
                    round(score, 4),
                    alias,
                    round(float(bm25n[i]), 4),
                    round(cosine, 4),
                    o.title_mr,
                )
            )
        results.sort(key=lambda c: c.score, reverse=True)
        return results[:top_k]


def load_occupations(conn) -> list[Occupation]:
    rows = conn.execute(
        "SELECT nco_code, title_en, title_hi, title_mr, aliases, embedding::text AS emb FROM nco "
        "ORDER BY nco_code"
    ).fetchall()
    out = []
    for r in rows:
        emb = None
        if r["emb"]:
            emb = np.array([float(x) for x in r["emb"].strip("[]").split(",")], dtype=np.float32)
        aliases = tuple(a.strip() for a in (r["aliases"] or "").split("|") if a.strip())
        out.append(
            Occupation(r["nco_code"], r["title_en"], r["title_hi"], aliases, emb, r["title_mr"])
        )
    return out
