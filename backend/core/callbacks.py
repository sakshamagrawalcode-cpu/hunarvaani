"""Redis structures for callbacks: a due-time queue, dedupe keys and daily counters."""

from datetime import datetime

QUEUE = "hv:callbacks"
TWO_DAYS = 2 * 24 * 3600


def schedule(r, call_id: str, due: datetime) -> None:
    r.zadd(QUEUE, {call_id: due.timestamp()})


def pop_due(r, now: datetime) -> str | None:
    """Claim the earliest callback that is due. Safe with several workers."""
    items = r.zrangebyscore(QUEUE, "-inf", now.timestamp(), start=0, num=1)
    if not items:
        return None
    call_id = items[0]
    if r.zrem(QUEUE, call_id) != 1:
        return None
    return call_id.decode() if isinstance(call_id, bytes) else call_id


def first_seen(r, inbound_call_uuid: str) -> bool:
    return bool(r.set(f"hv:seen:{inbound_call_uuid}", 1, nx=True, ex=TWO_DAYS))


def count_trigger(r, phone_hash: str, day: str) -> int:
    key = f"hv:triggers:{day}:{phone_hash}"
    n = r.incr(key)
    r.expire(key, TWO_DAYS)
    return int(n)


def take_budget(r, day: str, limit: int) -> bool:
    key = f"hv:budget:{day}"
    n = r.incr(key)
    r.expire(key, TWO_DAYS)
    return int(n) <= limit
