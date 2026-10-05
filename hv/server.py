"""Web server: kiosk page + WebSocket, Exotel phone WebSocket, officer console + API, prompt audio.

The officer console (/officer) has its own login (a session cookie); the API also accepts HTTP Basic
with the same user and password, for scripts. Its live call (/ws/console) plays a phone call in the
officer's browser and shows every decision step by step.

Run:  python -m uvicorn hv.server:app --host 0.0.0.0 --port 8000
"""

import asyncio
import base64
import binascii
import contextlib
import logging
import secrets
import threading
import time
from urllib.parse import urlsplit

from starlette.applications import Starlette
from starlette.requests import HTTPConnection, Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket

from .audio import PromptBank
from . import explain
from .card import card_svg, delete_card, load_card, save_card
from .channels.console import ConsoleChannel
from .channels.exotel import ExotelChannel
from .channels.kiosk import KioskChannel
from .config import ROOT, settings
from .data import EDUCATION_ORDER, get_data
from .engine import Conversation
from .llm import LLM
from .policy import FACTORS, POLICIES, PolicyError, ahp_weights
from .profile import Profile
from .ranker import rank
from .skills import skill_advice
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


async def console_ws(ws: WebSocket) -> None:
    """The console's live call: a logged-in officer plays the caller; every decision is traced."""
    officer = _officer(ws)
    if not officer:
        await ws.close(code=1008)
        return
    await ws.accept()
    STORE.audit(officer, "live_call", "", "phone demo from the console")
    await _converse(ConsoleChannel(ws, BANK), ws)


async def audio(request: Request) -> Response:
    lang, key = request.path_params["lang"], request.path_params["key"]
    if lang not in ("hi", "mr", "en") or not key.replace("_", "").replace("-", "").isalnum():
        return Response(status_code=404)
    path = BANK.path(lang, key)
    if not path.exists():
        return Response(status_code=404)
    return FileResponse(path, media_type="audio/wav", headers={"Cache-Control": "max-age=3600"})


# officer console --------------------------------------------------------------------------------
COOKIE = "hv_officer"
SESSION_SECONDS = 12 * 3600
SESSIONS: dict[str, tuple[str, float]] = {}  # token -> (officer, expires); a restart logs everyone out
FAILED: dict[str, list[float]] = {}  # address -> times of wrong logins (5 in 5 minutes: wait)


def _same(a: str, b: str) -> bool:
    return secrets.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def _right_login(user: str, pw: str) -> bool:
    return _same(user, settings.officer_user) & _same(pw, settings.officer_password)


def _same_origin(conn: HTTPConnection) -> bool:
    """A cookie login is only honoured from this site's own pages (no cross-site requests)."""
    origin = conn.headers.get("origin")
    return not origin or urlsplit(origin).netloc == conn.headers.get("host", "")


def _officer(conn: HTTPConnection) -> str | None:
    header = conn.headers.get("authorization", "")
    if header.lower().startswith("basic "):
        try:
            user, _, pw = base64.b64decode(header[6:]).decode().partition(":")
        except (binascii.Error, UnicodeDecodeError):
            return None
        return user if _right_login(user, pw) else None
    token = conn.cookies.get(COOKIE, "")
    found = SESSIONS.get(token) if token else None
    if found and found[1] > time.time() and _same_origin(conn):
        return found[0]
    if found and found[1] <= time.time():
        SESSIONS.pop(token, None)
    return None


def _need_login() -> Response:
    # no WWW-Authenticate header: the console shows its own login instead of the browser's pop-up
    return JSONResponse({"error": "login needed"}, status_code=401)


async def _body(request: Request) -> dict:
    try:
        body = await request.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}


async def officer_page(request: Request) -> Response:
    return FileResponse(WEB / "officer.html")


async def api_login(request: Request) -> Response:
    body = await _body(request)
    where = request.client.host if request.client else ""
    recent = [t for t in FAILED.get(where, []) if t > time.time() - 300]
    if len(recent) >= 5:
        return JSONResponse({"error": "Too many wrong tries. Wait five minutes."}, status_code=429)
    user, pw = str(body.get("user", "")), str(body.get("password", ""))
    if not _right_login(user, pw):
        FAILED[where] = recent + [time.time()]
        STORE.audit(user[:40] or "?", "login_failed", "", where)
        await asyncio.sleep(0.4)
        return JSONResponse({"error": "Wrong user or password."}, status_code=401)
    FAILED.pop(where, None)
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = (user, time.time() + SESSION_SECONDS)
    STORE.audit(user, "login", "", where)
    response = JSONResponse({"ok": True, "user": user})
    response.set_cookie(COOKIE, token, max_age=SESSION_SECONDS, httponly=True, samesite="strict",
                        secure=request.url.scheme == "https")
    return response


async def api_logout(request: Request) -> Response:
    SESSIONS.pop(request.cookies.get(COOKIE, ""), None)
    response = JSONResponse({"ok": True})
    response.delete_cookie(COOKIE)
    return response


async def api_me(request: Request) -> Response:
    officer = _officer(request)
    if not officer:
        return _need_login()
    return JSONResponse({"user": officer, "default_password": settings.officer_password == "change-me",
                         "models": settings.models, "llm": settings.llm_model})


async def api_catalog(request: Request) -> Response:
    """Everything the console's menus need: districts, occupations, sectors, education levels."""
    if not _officer(request):
        return _need_login()
    line = settings.phone_pincode or settings.device_pincode
    return JSONResponse({
        "districts": [{"code": d.code, "name": d.name_en, "state": d.state} for d in DATA.districts.values()],
        "occupations": sorted(({"code": o.code, "title": o.title_en, "sector": o.sector}
                               for o in DATA.occupations.values()), key=lambda o: o["title"]),
        "sectors": sorted(({"code": x.code, "title": x.title_en} for x in DATA.sectors.values()),
                          key=lambda x: x["title"]),
        "education": [{"code": e, "title": explain.EDU_TEXT[e]} for e in EDUCATION_ORDER],
        "factors": [{"code": f, "label": explain.FACTOR_LABEL[f], "text": explain.FACTOR_TEXT[f]} for f in FACTORS],
        "line_pin": line if DATA.district_for_pin(line) else "",
        "models": settings.models})


async def api_stats(request: Request) -> Response:
    if not _officer(request):
        return _need_login()
    return JSONResponse(STORE.counts())


async def api_districts(request: Request) -> Response:
    if not _officer(request):
        return _need_login()
    return JSONResponse([{"code": d.code, "name": d.name_en, "state": d.state} for d in DATA.districts.values()])


async def api_people(request: Request) -> Response:
    if not _officer(request):
        return _need_login()
    q = request.query_params
    rows = STORE.find(district=q.get("district", ""), name=q.get("name", ""), hv_id=q.get("id", ""),
                      status=q.get("status", ""))
    for r in rows:
        d = DATA.districts.get(r["district"] or "")
        r["district_name"] = d.name_en if d else ""
    return JSONResponse(rows)


def _person_view(hv_id: str) -> dict | None:
    person = STORE.person(hv_id)
    if not person:
        return None
    d = DATA.districts.get(person["district"] or "")
    person["district_name"] = d.name_en if d else ""
    prof = person["profile"]
    person["work"] = [DATA.occupations[c].title_en for c in prof.get("occupation_codes", []) if c in DATA.occupations]
    person["wants"] = [DATA.occupations[c].title_en for c in prof.get("aspiration_codes", []) if c in DATA.occupations]
    person["options"] = STORE.options(hv_id)
    person["turns"] = STORE.turns(hv_id)
    person["audit"] = STORE.audit_log(hv_id)
    try:
        pol = POLICIES.active().for_district(person["district"])
        person["explain"] = explain.person(DATA, Profile.from_dict(prof), person["options"], pol)
        person["explain"]["options"] = [explain.option(o) for o in person["options"]]
    except Exception:  # an explanation must never hide the record itself
        log.exception("could not explain %s", hv_id)
        person["explain"] = {"lines": [], "left_out": [], "weights": [], "options": []}
    return person


async def api_person(request: Request) -> Response:
    officer = _officer(request)
    if not officer:
        return _need_login()
    hv_id = request.path_params["hv_id"].replace("-", "")
    if request.method == "PATCH":
        return await _edit_person(request, officer, hv_id)
    if request.method == "DELETE":
        return await _erase_person(request, officer, hv_id)
    person = _person_view(hv_id)
    if not person:
        return JSONResponse({"error": "not found"}, status_code=404)
    STORE.audit(officer, "viewed", hv_id)
    return JSONResponse(person)


def _edited(body: dict, prof: dict) -> dict:
    """The officer's changes, checked like the conversation checks answers. Raises ValueError."""
    def number(key, lo, hi):
        v = body[key]
        if v is None or v == "":
            return None
        if isinstance(v, bool) or not isinstance(v, (int, float, str)) or not str(v).strip().lstrip("-").isdigit():
            raise ValueError(f"{key}: a whole number")
        v = int(v)
        if not lo <= v <= hi:
            raise ValueError(f"{key}: between {lo} and {hi}")
        return v

    def choice(key, allowed, empty=None):
        v = body[key]
        if v in (None, ""):
            return empty
        if v not in allowed:
            raise ValueError(f"{key}: one of {', '.join(map(str, allowed))}")
        return v

    def codes(key):
        v = body[key] or []
        if not isinstance(v, list) or any(not isinstance(c, int) or c not in DATA.occupations for c in v):
            raise ValueError(f"{key}: occupation codes from our list")
        return list(dict.fromkeys(v))[:3]

    def flag(key):
        if not isinstance(body[key], bool) and body[key] is not None:
            raise ValueError(f"{key}: true or false")
        return body[key]

    rules = {
        "name": lambda: str(body["name"] or "").strip()[:40],
        "age": lambda: number("age", 14, 80), "years": lambda: number("years", 0, 60),
        "radius_km": lambda: number("radius_km", 1, 200), "max_weeks": lambda: number("max_weeks", 1, 104),
        "gender": lambda: choice("gender", ("female", "male", "other")),
        "education": lambda: choice("education", EDUCATION_ORDER),
        "health": lambda: choice("health", ("none", "some", "severe"), "none"),
        "lean": lambda: choice("lean", ("job", "own_work", "either")),
        "aspiration_sector": lambda: choice("aspiration_sector", tuple(DATA.sectors)),
        "district": lambda: choice("district", tuple(DATA.districts)),
        "occupation_codes": lambda: codes("occupation_codes"),
        "aspiration_codes": lambda: codes("aspiration_codes"),
        "hostel_ok": lambda: flag("hostel_ok"), "cannot_leave_home": lambda: bool(flag("cannot_leave_home")),
    }
    out = {}
    for key, read in rules.items():
        if key in body:
            v, was = read(), prof.get(key)
            if key.endswith("_codes") and set(v) == set(was or []):
                continue  # the same work in another order is no change
            if v != was:
                out[key] = v
    if "name" in out and not out["name"]:
        raise ValueError("name: cannot be empty")
    return out


async def _edit_person(request: Request, officer: str, hv_id: str) -> Response:
    person = STORE.person(hv_id)
    if not person:
        return JSONResponse({"error": "not found"}, status_code=404)
    body = await _body(request)
    prof = person["profile"]
    try:
        changes = _edited(body, prof)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    note = "; ".join(f"{k}: {prof.get(k)!r} → {v!r}" for k, v in changes.items())
    prof.update(changes)
    if "district" in changes:
        prof["pin"], prof["location_from"] = "", "officer"
    if changes.get("cannot_leave_home"):
        prof["hostel_ok"] = False
    reranked = False
    if body.get("rerank") and prof.get("district"):
        p = Profile.from_dict(prof)
        pol = POLICIES.active().for_district(p.district)
        before = next((o["course_id"] for o in STORE.options(hv_id) if o.get("chosen")), None)
        options = rank(DATA, p, settings.max_options, policy=pol)
        STORE.save_options("officer-edit", hv_id, [o.summary() for o in options])
        for i, o in enumerate(options, 1):
            if o.course.course_id == before:
                STORE.choose(hv_id, i)
        prof["skill_advice"] = skill_advice(DATA, p, pol)
        reranked = True
        note = (note + "; " if note else "") + "ranked again"
    if not changes and not reranked:
        return JSONResponse({"ok": True, "changed": [], "person": _person_view(hv_id)})
    STORE.edit_person(hv_id, prof.get("name") or person["name"], prof.get("district"), prof, officer,
                      (str(body.get("note", ""))[:200] + " | " if body.get("note") else "") + note)
    return JSONResponse({"ok": True, "changed": sorted(changes), "reranked": reranked, "person": _person_view(hv_id)})


async def _erase_person(request: Request, officer: str, hv_id: str) -> Response:
    if not STORE.person(hv_id):
        return JSONResponse({"error": "not found"}, status_code=404)
    body = await _body(request)
    if str(body.get("confirm", "")).replace("-", "") != hv_id:
        return JSONResponse({"error": "type the HunarVaani ID to confirm"}, status_code=400)
    STORE.delete_person(hv_id, officer, "erased by an officer" + (f": {str(body['note'])[:200]}" if body.get("note") else ""))
    delete_card(hv_id)
    return JSONResponse({"ok": True})


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
    body = await _body(request)
    status = body.get("status")
    if status not in ("approved", "referred", "needs_info", "new"):
        return JSONResponse({"error": "bad status"}, status_code=400)
    hv_id = request.path_params["hv_id"].replace("-", "")
    if not STORE.person(hv_id):
        return JSONResponse({"error": "not found"}, status_code=404)
    STORE.set_status(hv_id, status, officer, str(body.get("note", ""))[:500])
    return JSONResponse({"ok": True})


# ranking policy: officers read, edit (per district), set weights by AHP, activate learned proposals ---
async def api_policy(request: Request) -> Response:
    officer = _officer(request)
    if not officer:
        return _need_login()
    if request.method == "GET":
        return JSONResponse({"active": POLICIES.active().to_dict(), "history": POLICIES.history()[-20:],
                             "proposals": [{"file": p["file"], "report": p.get("report")} for p in POLICIES.proposals()]})
    body = await _body(request)
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
    body = await _body(request)
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
    body = await _body(request)
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
    body = await _body(request)
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
    Route("/api/login", api_login, methods=["POST"]),
    Route("/api/logout", api_logout, methods=["POST"]),
    Route("/api/me", api_me),
    Route("/api/catalog", api_catalog),
    Route("/api/stats", api_stats),
    Route("/api/districts", api_districts),
    Route("/api/people", api_people),
    Route("/api/person/{hv_id}", api_person, methods=["GET", "PATCH", "DELETE"]),
    Route("/api/person/{hv_id}/card", api_card),
    Route("/api/person/{hv_id}/status", api_status, methods=["POST"]),
    Route("/api/person/{hv_id}/outcome", api_outcome, methods=["POST"]),
    Route("/api/policy", api_policy, methods=["GET", "POST"]),
    Route("/api/policy/ahp", api_ahp, methods=["POST"]),
    Route("/api/policy/activate", api_activate, methods=["POST"]),
    WebSocketRoute("/ws/kiosk", kiosk_ws),
    WebSocketRoute("/ws/console", console_ws),
    WebSocketRoute("/exotel/ws/{token}", exotel_ws),
    Mount("/web", StaticFiles(directory=str(WEB)), name="web"),
])
