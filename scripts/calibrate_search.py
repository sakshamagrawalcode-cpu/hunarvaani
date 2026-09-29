"""Show how the occupation search scores sample sentences, including raw e5 cosines.

Run in the worker container (it has the model):
  docker compose -f infra/docker-compose.yml exec worker python scripts/calibrate_search.py
  docker compose -f infra/docker-compose.yml exec worker python scripts/calibrate_search.py "मैं ..."
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from apps.worker.main import load_encoder  # noqa: E402
from core import store  # noqa: E402
from core.search.nco_search import THRESHOLD, NcoIndex, load_occupations  # noqa: E402

SAMPLES = [
    "मैं सिलाई का काम करती हूं, ब्लाउज़ और सूट सिलती हूं",
    "मैं बिजली का काम करता हूँ, घरों में वायरिंग करता हूं",
    "खेती करता हूं और भैंस का दूध बेचता हूं",
    "मेरी मोबाइल रिपेयर की दुकान है",
    "मैं लकड़ी का फर्नीचर बनाता हूं",
    "मैं कपड़े सीती हूं घर पर",
    "गाड़ियों का इंजन ठीक करता हूं",
    "मैं कुछ नहीं करता, घर पर रहता हूं",
    "आज मौसम बहुत अच्छा है",
]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    url = os.environ.get("DATABASE_URL") or "postgresql://hv:hv@db:5432/hv"
    with store.connect(url) as conn:
        occupations = load_occupations(conn)
    if not occupations:
        sys.exit("nco table is empty; run scripts/seed_nco.py first")
    index, encode = NcoIndex(occupations), load_encoder()
    by_code = {o.code: o for o in occupations}
    for text in sys.argv[1:] or SAMPLES:
        vec = encode(text) if encode else None
        top = index.search(text, vec, top_k=3)
        verdict = "READ BACK" if top and top[0].score >= THRESHOLD else "trade list"
        print(f"\n{text}\n  -> {verdict}")
        for c in top:
            raw = float(np.dot(vec, by_code[c.code].embedding)) if vec is not None else float("nan")
            print(
                f"  {c.code} {c.title_hi:<16} score {c.score:.2f}  alias {c.alias:.0f}  "
                f"bm25 {c.bm25:.2f}  cosine {c.cosine:.2f} (raw {raw:.3f})"
            )


if __name__ == "__main__":
    main()
