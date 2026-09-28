from datetime import datetime, time, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30), "IST")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ist_day(dt: datetime) -> str:
    return dt.astimezone(IST).date().isoformat()


def parse_quiet_hours(spec: str) -> tuple[time, time] | None:
    """'21:00-09:00' -> (21:00, 09:00). Empty spec means no quiet hours."""
    spec = (spec or "").strip()
    if not spec:
        return None
    start, _, end = spec.partition("-")
    return time.fromisoformat(start.strip()), time.fromisoformat(end.strip())


def in_quiet_hours(dt: datetime, spec: str) -> bool:
    window = parse_quiet_hours(spec)
    if window is None:
        return False
    start, end = window
    t = dt.astimezone(IST).time()
    if start <= end:
        return start <= t < end
    return t >= start or t < end


def next_allowed(dt: datetime, spec: str) -> datetime:
    """dt itself if outside quiet hours, else the moment quiet hours end (IST)."""
    if not in_quiet_hours(dt, spec):
        return dt
    _, end = parse_quiet_hours(spec)
    local = dt.astimezone(IST)
    candidate = local.replace(hour=end.hour, minute=end.minute, second=0, microsecond=0)
    if candidate <= local:
        candidate += timedelta(days=1)
    return candidate.astimezone(timezone.utc)
