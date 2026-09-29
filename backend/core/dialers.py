"""Outbound callbacks. Each dialer rings a number and connects it to our interview."""

import base64
import json
import urllib.error
import urllib.parse
import urllib.request

from core.config import Settings


class DialError(RuntimeError):
    pass


def exotel_number(e164: str) -> str:
    """+919876543210 -> 09876543210, the national format used in Exotel's API examples."""
    return "0" + e164[-10:]


class ExotelDialer:
    def __init__(self, settings: Settings, opener=urllib.request.urlopen):
        self.s = settings
        self.opener = opener

    def flow_url(self) -> str:
        return f"http://my.exotel.com/{self.s.exotel_sid}/exoml/start_voice/{self.s.exotel_app_id}"

    def dial(self, number: str, call_id: str) -> str | None:
        s = self.s
        url = f"https://{s.exotel_subdomain}/v1/Accounts/{s.exotel_sid}/Calls/connect.json"
        form = {
            "From": exotel_number(number),
            "CallerId": s.exotel_caller_id,
            "Url": self.flow_url(),
            "CallType": "trans",
            "TimeOut": "30",
            "TimeLimit": "900",
            "CustomField": call_id,
            "StatusCallback": f"{s.public_base_url}/exotel/status/{s.exotel_ws_token}",
        }
        auth = base64.b64encode(f"{s.exotel_api_key}:{s.exotel_api_token}".encode()).decode()
        req = urllib.request.Request(
            url,
            data=urllib.parse.urlencode(form).encode(),
            headers={"Authorization": f"Basic {auth}", "Accept": "application/json"},
            method="POST",
        )
        try:
            with self.opener(req, timeout=20) as resp:
                body = json.load(resp)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            raise DialError(f"Exotel HTTP {exc.code}: {detail}") from None
        except urllib.error.URLError as exc:
            raise DialError(f"could not reach Exotel: {exc.reason}") from None
        sid = (body.get("Call") or {}).get("Sid")
        if not sid:
            raise DialError(f"Exotel reply had no Call.Sid: {str(body)[:300]}")
        return sid


class PlivoDialer:
    def __init__(self, settings: Settings, client=None):
        self.s = settings
        if client is None:
            import plivo

            client = plivo.RestClient(settings.plivo_auth_id, settings.plivo_auth_token)
        self.client = client

    def dial(self, number: str, call_id: str) -> str | None:
        base = self.s.public_base_url
        resp = self.client.calls.create(
            from_=self.s.plivo_number,
            to_=number,
            answer_url=f"{base}/pv/ivr/start?call={call_id}",
            answer_method="POST",
            hangup_url=f"{base}/pv/hangup?call={call_id}",
            hangup_method="POST",
            ring_timeout=30,
        )
        value = getattr(resp, "request_uuid", None)
        if value is None and isinstance(resp, dict):
            value = resp.get("request_uuid")
        if isinstance(value, list):
            value = value[0] if value else None
        return str(value) if value else None


REQUIRED = {
    "exotel": {
        "EXOTEL_SID": "exotel_sid",
        "EXOTEL_API_KEY": "exotel_api_key",
        "EXOTEL_API_TOKEN": "exotel_api_token",
        "EXOTEL_CALLER_ID": "exotel_caller_id",
        "EXOTEL_APP_ID": "exotel_app_id",
        "EXOTEL_WS_TOKEN": "exotel_ws_token",
    },
    "plivo": {
        "PLIVO_AUTH_ID": "plivo_auth_id",
        "PLIVO_AUTH_TOKEN": "plivo_auth_token",
        "PLIVO_NUMBER": "plivo_number",
    },
}


def missing_config(settings: Settings) -> list[str]:
    fields = {"PUBLIC_BASE_URL": "public_base_url", "PHONE_ENC_KEY": "phone_enc_key"}
    fields.update(REQUIRED.get(settings.telephony_provider, {}))
    if settings.telephony_provider not in REQUIRED:
        return [f"TELEPHONY_PROVIDER (unknown: {settings.telephony_provider!r})"]
    return [env for env, attr in fields.items() if not getattr(settings, attr)]


def make_dialer(settings: Settings):
    if settings.telephony_provider == "plivo":
        return PlivoDialer(settings)
    return ExotelDialer(settings)
