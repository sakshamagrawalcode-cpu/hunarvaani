"""scripts/init_db.py applies every db/*.sql file on each run, so they must be safe to repeat."""

import os
from pathlib import Path

import psycopg
import pytest

DB = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DB, reason="TEST_DATABASE_URL unset")

SQL = sorted((Path(__file__).resolve().parent.parent / "db").glob("*.sql"))


def test_schema_files_can_be_applied_again():
    with psycopg.connect(DB, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        for _ in range(3):
            with conn.transaction():
                for f in SQL:
                    conn.execute(f.read_text(encoding="utf-8"))
        columns = {
            r[0]
            for r in conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'call'"
            )
        }
    assert "provider_call_id" in columns and "plivo_request_uuid" not in columns
