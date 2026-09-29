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
    "provider_call_id",
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


STORY_FIELDS = ("transcript", "transcript_en", "top1", "top2", "stt_ms", "search_ms")


def save_story(conn, call_id: str, recording_url: str, **fields: Any) -> None:
    """Insert or fill in the story for one recording.

    The api and the worker both save it, in either order; a value one side already stored is
    kept when the other side has none (e.g. the api stopped waiting before the transcript came).
    """
    values = [fields.get(k) for k in STORY_FIELDS]
    updates = ", ".join(f"{k} = COALESCE(EXCLUDED.{k}, story.{k})" for k in STORY_FIELDS)
    conn.execute(
        f"INSERT INTO story (call_id, recording_url, {', '.join(STORY_FIELDS)}) "
        f"VALUES (%s, %s, {', '.join('%s' for _ in STORY_FIELDS)}) "
        f"ON CONFLICT (recording_url) DO UPDATE SET {updates}",
        (call_id, recording_url, *values),
    )


def add_event(conn, call_id: str, kind: str, payload: dict | None = None) -> None:
    conn.execute(
        "INSERT INTO event (call_id, kind, payload) VALUES (%s, %s, %s)",
        (call_id, kind, Jsonb(payload or {})),
    )
