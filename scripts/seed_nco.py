"""Load data/nco_seed.csv into the nco table with multilingual-e5-base embeddings.

Run inside the stack (the first run downloads the model, about 1 GB):
  docker compose -f infra/docker-compose.yml run --rm worker python scripts/seed_nco.py
"""

import os
import sys
import time

import psycopg

from core.search.seed import load_seed, passage_text, vector_literal

MODEL = "intfloat/multilingual-e5-base"


def main() -> None:
    from sentence_transformers import SentenceTransformer

    rows = load_seed()
    print(f"seed rows: {len(rows)}")
    t0 = time.time()
    model = SentenceTransformer(MODEL)
    print(f"model loaded in {time.time() - t0:.1f}s")
    vectors = model.encode(
        [passage_text(r) for r in rows], normalize_embeddings=True, show_progress_bar=False
    )
    if vectors.shape[1] != 768:
        sys.exit(f"expected 768-dim embeddings, got {vectors.shape[1]}")

    url = os.environ.get("DATABASE_URL") or "postgresql://hv:hv@db:5432/hv"
    with psycopg.connect(url) as conn:
        for r, v in zip(rows, vectors, strict=True):
            conn.execute(
                "INSERT INTO nco (nco_code, title_en, title_hi, title_mr, aliases, embedding) "
                "VALUES (%s, %s, %s, %s, %s, %s::vector) "
                "ON CONFLICT (nco_code) DO UPDATE SET title_en = EXCLUDED.title_en, "
                "title_hi = EXCLUDED.title_hi, title_mr = EXCLUDED.title_mr, "
                "aliases = EXCLUDED.aliases, embedding = EXCLUDED.embedding",
                (
                    r.nco_code,
                    r.title_en,
                    r.title_hi,
                    r.title_mr,
                    " | ".join(r.aliases),
                    vector_literal(v),
                ),
            )
        count = conn.execute("SELECT count(*) FROM nco").fetchone()[0]
    print(f"nco rows in database: {count}")


if __name__ == "__main__":
    main()
