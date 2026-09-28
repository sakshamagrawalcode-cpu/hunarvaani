import psycopg
import redis
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from core.config import load_settings

settings = load_settings()
app = FastAPI(title="HunarVaani voice API")


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/ready")
def ready():
    checks = {}
    try:
        with psycopg.connect(settings.database_url, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
            row = conn.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'").fetchone()
            checks["db"] = True
            checks["pgvector"] = row is not None
    except Exception as exc:
        checks["db"] = False
        checks["db_error"] = type(exc).__name__
    try:
        redis.Redis.from_url(settings.redis_url, socket_connect_timeout=3).ping()
        checks["redis"] = True
    except Exception as exc:
        checks["redis"] = False
        checks["redis_error"] = type(exc).__name__
    ok = checks.get("db") and checks.get("pgvector") and checks.get("redis")
    return JSONResponse({"ok": bool(ok), **checks}, status_code=200 if ok else 503)
