import re
from pathlib import Path

import psycopg
import redis
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from core.config import load_settings

settings = load_settings()
app = FastAPI(title="HunarVaani voice API", docs_url=None, redoc_url=None, openapi_url=None)

AUDIO_DIR = Path(__file__).resolve().parents[2] / "audio"
_LANG = re.compile(r"^[a-z]{2,3}$")
_NAME = re.compile(r"^[A-Za-z0-9_-]{1,80}$")


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
            has_nco = conn.execute("SELECT to_regclass('public.nco')").fetchone()[0]
            checks["nco_rows"] = (
                conn.execute("SELECT count(*) FROM nco").fetchone()[0] if has_nco else None
            )
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


@app.get("/audio/{lang}/{name}.wav")
def audio(lang: str, name: str):
    if not (_LANG.match(lang) and _NAME.match(name)):
        raise HTTPException(404)
    path = AUDIO_DIR / lang / f"{name}.wav"
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path, media_type="audio/wav")
