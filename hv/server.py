"""Web server: kiosk page + WebSocket, Exotel phone WebSocket, officer console + API, prompt audio.

Run:  python -m uvicorn hv.server:app --host 0.0.0.0 --port 8000
"""

import asyncio
import base64
import binascii
import contextlib
import logging
import secrets
import threading

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket

from .audio import PromptBank
from .card import card_svg, load_card, save_card
from .channels.exotel import ExotelChannel
from .channels.kiosk import KioskChannel
from .config import ROOT, settings
from .data import get_data
from .engine import Conversation
from .llm import LLM
from .policy import POLICIES, PolicyError, ahp_weights
from .store import Store
from .stt import STT

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("hv.server")

DATA = get_data()
STORE = Store(settings.db_path)
BANK = PromptBank(settings.audio_dir)
LLM_ = LLM(DATA)
STT_ = STT()
WEB = ROOT / "web"


async def _converse(channel, ws: WebSocket) -> None:
    reader = asyncio.create_task(channel.reader())
    reason = "error"
    try:
        reason = await Conversation(channel, DATA, LLM_, STT_, STORE).run()
    except Exception:
        log.exception("conversation failed")
    finally:
        await channel.end(reason)
        reader.cancel()
        try:
            await ws.close()
        except Exception:
            pass


async def kiosk_ws(ws: WebSocket) -> None:
    await ws.accept()
    await _converse(KioskChannel(ws, BANK), ws)


async def exotel_ws(ws: WebSocket) -> None:
    if not secrets.compare_digest(ws.path_params.get("token", ""), settings.exotel_token):
        log.warning("Exotel connected with a wrong token: check the Voicebot URL")
        await ws.close(code=1008)
        return
    await ws.accept()
    await _converse(ExotelChannel(ws, BANK), ws)


async def audio(request: Request) -> Response:
    lang, key = request.path_params["lang"], request.path_params["key"]
    if lang not in ("hi", "mr", "en") or not key.replace("_", "").replace("-", "").isalnum():
        return Response(status_code=404)
    path = BANK.path(lang, key)
    if not path.exists():
        return Response(status_code=404)
    return FileResponse(path, media_type="audio/wav", headers={"Cache-Control": "max-age=3600"})


# officer console --------------------------------------------------------------------------------
def _officer(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("basic "):
        try:
            user, _, pw = base64.b64decode(header[6:]).decode().partition(":")
        except (binascii.Error, UnicodeDecodeError):
            return None
        if secrets.compare_digest(user, settings.officer_user) and secrets.compare_digest(pw, settings.officer_password):
            return user
    return None


def _need_login() -> Response:
    return Response("Login needed", status_code=401, headers={"WWW-Authenticate": 'Basic realm="HunarVaani officers"'})


async def officer_page(request: Request) -> Response:
    if not _officer(request):
        return _need_login()
    return FileResponse(WEB / "officer.html")


async def api_districts(request: Request) -> Response:
    if not _officer(request):
        return _need_login()
    return JSONResponse([{"code": d.code, "name": d.name_en, "state": d.state} for d in DATA.districts.values()])


async def api_people(request: Request) -> Response:
    if not _officer(request):
        return _need_login()
    q = request.query_params
    rows = STORE.find(district=q.get("district", ""), name=q.get("name", ""), hv_id=q.get("id", ""))
    for r in rows:
        d = DATA.districts.get(r["district"] or "")
        r["district_name"] = d.name_en if d else ""
    return JSONResponse(rows)


async def api_person(request: Request) -> Response:
    officer = _officer(request)
    if not officer:
        return _need_login()
    hv_id = request.path_params["hv_id"].replace("-", "")
    person = STORE.person(hv_id)
    if not person:
        return JSONResponse({"error": "not found"}, status_code=404)
    STORE.audit(officer, "viewed", hv_id)
    d = DATA.districts.get(person["district"] or "")
    person["district_name"] = d.name_en if d else ""
    prof = person["profile"]
    person["work"] = [DATA.occupations[c].title_en for c in prof.get("occupation_codes", []) if c in DATA.occupations]
    person["wants"] = [DATA.occupations[c].title_en for c in prof.get("aspiration_codes", []) if c in DATA.occupations]
    person["options"] = STORE.options(hv_id)
    person["turns"] = STORE.turns(hv_id)
    person["audit"] = STORE.audit_log(hv_id)
    return JSONResponse(person)


async def api_card(request: Request) -> Response:
    """The person's printable card (made at the end of their session; rebuilt if the file is missing)."""
    officer = _officer(request)
    if not officer:
        return _need_login()
    hv_id = request.path_params["hv_id"].replace("-", "")
    person = STORE.person(hv_id)
    if not person:
        return JSONResponse({"error": "not found"}, status_code=404)
    svg = load_card(hv_id)
    if svg is None:
        d = DATA.districts.get(person["district"] or "")
        chosen = next((o["course"] for o in STORE.options(hv_id) if o.get("chosen")), "")
        advice = person["profile"].get("skill_advice") or []
        svg = card_svg(hv_id, person["name"], d.name_en if d else "", chosen,
                       advice[0]["skills"][:3] if advice else [], person["created"][:10])
        save_card(hv_id, svg)
    STORE.audit(officer, "card_viewed", hv_id)
    page = ('<!doctype html><html><head><meta charset="utf-8"><title>HunarVaani card</title></head>'
            f'<body style="margin:24px">{svg}<p><button onclick="print()">Print</button></p></body></html>')
    return HTMLResponse(page)


async def api_status(request: Request) -> Response:
    officer = _officer(request)
    if not officer:
        return _need_login()
    body = await request.json()
    status = body.get("status")
    if status not in ("approved", "referred", "needs_info", "new"):
        return JSONResponse({"error": "bad status"}, status_code=400)
    STORE.set_status(request.path_params["hv_id"].replace("-", ""), status, officer, str(body.get("note", ""))[:500])
    return JSONResponse({"ok": True})


# ranking policy: officers read, edit (per district), set weights by AHP, activate learned proposals ---
async def api_policy(request: Request) -> Response:
    officer = _officer(request)
    if not officer:
        return _need_login()
    if request.method == "GET":
        return JSONResponse({"active": POLICIES.active().to_dict(), "history": POLICIES.history()[-20:],
                             "proposals": [{"file": p["file"], "report": p.get("report")} for p in POLICIES.proposals()]})
    body = await request.json()
    raw = POLICIES.active().to_dict()
    changes = {k: body[k] for k in ("base_weights", "emphasis", "gates", "tradeoff", "questions") if k in body}
    district = body.get("district")
    try:
        if district:
            if district not in DATA.districts:
                return JSONResponse({"error": "unknown district"}, status_code=400)
            ov = raw.setdefault("district_overrides", {}).setdefault(district, {})
            for k, v in changes.items():
                ov[k] = {**ov.get(k, {}), **v}
        else:
            for k, v in changes.items():
                raw[k] = {**raw[k], **v}
        pol = POLICIES.save(raw, officer, str(body.get("note", ""))[:300])
    except (PolicyError, KeyError, TypeError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    STORE.audit(officer, "policy_saved", "", f"{pol.version} {district or 'all districts'}")
    return JSONResponse({"ok": True, "version": pol.version})


async def api_ahp(request: Request) -> Response:
    officer = _officer(request)
    if not officer:
        return _need_login()
    body = await request.json()
    try:
        weights, cr = ahp_weights(body["matrix"])
    except (PolicyError, KeyError, ValueError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    result = {"weights": weights, "consistency_ratio": cr, "consistent": cr <= 0.1, "saved": False}
    if body.get("save") and cr <= 0.1:
        raw = POLICIES.active().to_dict()
        if body.get("district"):
            raw.setdefault("district_overrides", {}).setdefault(body["district"], {})["base_weights"] = weights
        else:
            raw["base_weights"] = weights
        result["version"] = POLICIES.save(raw, officer, "AHP survey").version
        result["saved"] = True
        STORE.audit(officer, "policy_ahp", "", f"CR {cr}")
    return JSONResponse(result)


async def api_activate(request: Request) -> Response:
    officer = _officer(request)
    if not officer:
        return _need_login()
    body = await request.json()
    try:
        pol = POLICIES.activate(str(body.get("file", "")), officer)
    except (FileNotFoundError, PolicyError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    STORE.audit(officer, "policy_activated", "", pol.version)
    return JSONResponse({"ok": True, "version": pol.version})


async def api_outcome(request: Request) -> Response:
    officer = _officer(request)
    if not officer:
        return _need_login()
    body = await request.json()
    hv_id = request.path_params["hv_id"].replace("-", "")
    if not STORE.person(hv_id) or not body.get("course_id"):
        return JSONResponse({"error": "unknown person or course"}, status_code=400)
    w = body.get("working_6m")
    STORE.add_outcome(hv_id, str(body["course_id"]), bool(body.get("completed")), None if w is None else bool(w), officer)
    return JSONResponse({"ok": True})


async def api_pincode(request: Request) -> Response:
    """Kiosk setup: which district a PIN code belongs to (no personal data; used once per kiosk)."""
    pin = request.path_params["pin"]
    d = DATA.district_for_pin(pin) if pin.isdigit() and len(pin) == 6 else None
    if not d:
        return JSONResponse({"error": "unknown PIN code"}, status_code=404)
    return JSONResponse({"pin": pin, "district": d.name_en, "district_code": d.code, "state": d.state})


async def health(request: Request) -> Response:
    return JSONResponse({"ok": True, "models": settings.models, "llm": settings.llm_model})


def _warm_up() -> None:
    """Real mode: load the LLM and speech-to-text in the background, so the first person does not wait."""
    import httpx

    try:
        httpx.get(f"{settings.ollama_url}/api/tags", timeout=5).raise_for_status()
    except Exception:
        log.error("Ollama is not reachable at %s. Start the Ollama app (or run: ollama serve).", settings.ollama_url)
    llm_ok = LLM_.warm_up()
    stt_ok = STT_.warm_up()
    if llm_ok and stt_ok:
        log.info("models warmed up: ready for calls")
    else:
        log.error("models NOT ready (see the errors above): calls will fall back to keypad answers")


@contextlib.asynccontextmanager
async def lifespan(app):
    hi = len(list((settings.audio_dir / "hi").glob("*.wav"))) if (settings.audio_dir / "hi").exists() else 0
    log.info("HunarVaani starting: models=%s, LLM=%s, speech-to-text on %s, %d Hindi voice pieces",
             settings.models, settings.llm_model, settings.stt_device, hi)
    if hi == 0:
        log.warning("No rendered voice in %s: the kiosk uses the browser voice and phone calls are silent. "
                    "Render it: .\\install.ps1 -OnlyVoices", settings.audio_dir)
    if settings.models == "real":
        threading.Thread(target=_warm_up, daemon=True).start()
    else:
        log.info("fake mode: no LLM or speech recognition (type answers on the kiosk). Use .\\run.ps1 -Real")
    yield


app = Starlette(lifespan=lifespan, routes=[
    Route("/", lambda r: RedirectResponse("/kiosk")),
    Route("/kiosk", lambda r: FileResponse(WEB / "kiosk.html")),
    Route("/health", health),
    Route("/api/pincode/{pin}", api_pincode),
    Route("/audio/{lang}/{key}.wav", audio),
    Route("/officer", officer_page),
    Route("/api/districts", api_districts),
    Route("/api/people", api_people),
    Route("/api/person/{hv_id}", api_person),
    Route("/api/person/{hv_id}/card", api_card),
    Route("/api/person/{hv_id}/status", api_status, methods=["POST"]),
    Route("/api/person/{hv_id}/outcome", api_outcome, methods=["POST"]),
    Route("/api/policy", api_policy, methods=["GET", "POST"]),
    Route("/api/policy/ahp", api_ahp, methods=["POST"]),
    Route("/api/policy/activate", api_activate, methods=["POST"]),
    WebSocketRoute("/ws/kiosk", kiosk_ws),
    WebSocketRoute("/exotel/ws/{token}", exotel_ws),
    Mount("/web", StaticFiles(directory=str(WEB)), name="web"),
])
