import hmac
import logging
import re
from functools import lru_cache
from pathlib import Path

import psycopg
import redis
from fastapi import FastAPI, HTTPException, Request, WebSocket
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response

from apps.voice import calls
from apps.voice.exotel import ExotelSession, PromptAudio
from core import interview_store, plivo_sig
from core.config import load_settings
from core.plivo_xml import REJECT

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger("voice")


class _HideTokens(logging.Filter):
    """Keep the Exotel URL token out of uvicorn's access and websocket logs."""

    pattern = re.compile(r"(/exotel/(?:ws|status)/)[^\s\"'?]+")

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        hidden = self.pattern.sub(r"\1<token>", message)
        if hidden != message:
            record.msg, record.args = hidden, ()
        return True


for _name in ("uvicorn.access", "uvicorn.error"):
    logging.getLogger(_name).addFilter(_HideTokens())
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


@lru_cache(maxsize=4)
def _redis_for(url: str) -> redis.Redis:
    return redis.Redis.from_url(url, socket_connect_timeout=3, socket_timeout=3)


def _xml(body: str) -> Response:
    return Response(body, media_type="application/xml")


async def _verified_params(request: Request) -> dict:
    form = await request.form()
    params = {k: str(v) for k, v in form.items()}
    query = request.url.query
    path = request.url.path + (f"?{query}" if query else "")
    ok = plivo_sig.is_valid(
        settings.public_base_url,
        path,
        params,
        request.headers.get("x-plivo-signature-v3"),
        request.headers.get("x-plivo-signature-v3-nonce"),
        settings.plivo_auth_token,
    )
    if not ok:
        log.warning("rejected %s: bad or missing Plivo signature", request.url.path)
        raise HTTPException(403)
    return params


@app.post("/pv/answer")
async def pv_answer(request: Request):
    params = await _verified_params(request)
    try:
        body = await run_in_threadpool(
            calls.missed_call, params, settings, _redis_for(settings.redis_url)
        )
    except Exception:
        log.exception("missed call handling failed; rejecting the call anyway")
        body = REJECT
    return _xml(body)


@app.post("/pv/ivr/start")
async def pv_ivr_start(request: Request):
    await _verified_params(request)
    body = await run_in_threadpool(calls.ivr_start, request.query_params.get("call"), settings)
    return _xml(body)


@app.post("/pv/hangup")
async def pv_hangup(request: Request):
    params = await _verified_params(request)
    await run_in_threadpool(calls.hangup, request.query_params.get("call"), params, settings)
    return PlainTextResponse("OK")


def _exotel_token_ok(token: str) -> bool:
    expected = settings.exotel_ws_token
    return bool(expected) and hmac.compare_digest(token.encode(), expected.encode())


@app.websocket("/exotel/ws/{token}")
async def exotel_ws(websocket: WebSocket, token: str):
    if not _exotel_token_ok(token):
        log.warning("rejected Exotel websocket: bad token")
        await websocket.close(code=1008)
        return
    await websocket.accept()
    session = ExotelSession(
        websocket, settings, PromptAudio(AUDIO_DIR), _redis_for(settings.redis_url)
    )
    await session.run()


@app.post("/exotel/status/{token}")
async def exotel_status(token: str, request: Request):
    if not _exotel_token_ok(token):
        raise HTTPException(403)
    form = await request.form()
    sid = str(form.get("CallSid") or "")
    status = str(form.get("Status") or form.get("CallStatus") or "")
    if sid:
        await run_in_threadpool(interview_store.provider_status, settings, sid, status)
    return PlainTextResponse("OK")
