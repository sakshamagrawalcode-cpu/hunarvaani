"""Apply every db/*.sql file in order. Safe to run repeatedly.

Run inside the stack:
  docker compose -f infra/docker-compose.yml run --rm worker python scripts/init_db.py
"""

import os
import sys
from pathlib import Path

import psycopg

DB_DIR = Path(__file__).resolve().parent.parent / "database" / "schema"


def main() -> None:
    url = os.environ.get("DATABASE_URL") or "postgresql://hv:hv@db:5432/hv"
    files = sorted(DB_DIR.glob("*.sql"))
    if not files:
        sys.exit(f"no .sql files in {DB_DIR}")
    with psycopg.connect(url) as conn:
        for f in files:
            conn.execute(f.read_text(encoding="utf-8"))
            print(f"applied {f.name}")
        tables = conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        ).fetchall()
    print("tables:", ", ".join(t[0] for t in tables))


if __name__ == "__main__":
    main()
