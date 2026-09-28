from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

CALL_COLUMNS = {
    "phone_enc",
    "callback_at",
    "answered_at",
    "ended_at",
    "duration_seconds",
    "language",
    "keypad_only",
    "human_flag",
    "status",
    "plivo_request_uuid",
}


def connect(url: str) -> psycopg.Connection:
    return psycopg.connect(url, autocommit=True, row_factory=dict_row, connect_timeout=5)


def is_blocked(conn, phone_hash: str) -> bool:
    row = conn.execute("SELECT 1 FROM blocked_number WHERE phone_hash = %s", (phone_hash,))
    return row.fetchone() is not None


def create_call(
    conn,
    *,
    phone_hash: str,
    phone_enc: bytes | None,
    inbound_uuid: str | None,
    status: str,
    missed_at,
) -> str | None:
    """Insert a call. Returns None if this inbound call UUID was already stored."""
    row = conn.execute(
        "INSERT INTO call (phone_hash, phone_enc, plivo_call_uuid, missed_at, status) "
        "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (plivo_call_uuid) DO NOTHING RETURNING id",
        (phone_hash, phone_enc, inbound_uuid or None, missed_at, status),
    ).fetchone()
    return str(row["id"]) if row else None


def get_call(conn, call_id: str) -> dict[str, Any] | None:
    try:
        return conn.execute("SELECT * FROM call WHERE id = %s", (call_id,)).fetchone()
    except psycopg.errors.InvalidTextRepresentation:
        return None


def update_call(conn, call_id: str, **fields: Any) -> None:
    unknown = set(fields) - CALL_COLUMNS
    if unknown:
        raise ValueError(f"not updatable: {sorted(unknown)}")
    assignments = ", ".join(f"{k} = %s" for k in fields)
    conn.execute(f"UPDATE call SET {assignments} WHERE id = %s", (*fields.values(), call_id))


def add_event(conn, call_id: str, kind: str, payload: dict | None = None) -> None:
    conn.execute(
        "INSERT INTO event (call_id, kind, payload) VALUES (%s, %s, %s)",
        (call_id, kind, Jsonb(payload or {})),
    )
