import base64
import io
import json
import urllib.error
import urllib.parse

import pytest

from core.config import Settings
from core.dialers import DialError, ExotelDialer, PlivoDialer, exotel_number, missing_config


def settings(**kw):
    base = dict(
        public_base_url="https://hv.test",
        database_url="",
        redis_url="",
        default_language="hi-IN",
        second_language="",
        callback_delay_seconds=5,
        max_triggers_per_day=3,
        daily_call_budget=100,
        quiet_hours="",
        phone_enc_key="k",
        exotel_sid="acme1",
        exotel_api_key="key1",
        exotel_api_token="tok1",
        exotel_subdomain="api.exotel.com",
        exotel_caller_id="08012345678",
        exotel_app_id="998877",
        exotel_ws_token="wstoken",
    )
    base.update(kw)
    return Settings(**base)


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_exotel_number_format():
    assert exotel_number("+919876543210") == "09876543210"


def test_exotel_dial_builds_the_connect_request():
    seen = {}

    def opener(req, timeout):
        seen["req"], seen["timeout"] = req, timeout
        return FakeResponse(json.dumps({"Call": {"Sid": "sid-123"}}).encode())

    sid = ExotelDialer(settings(), opener=opener).dial("+919876543210", "call-1")
    req = seen["req"]
    assert sid == "sid-123"
    assert req.full_url == "https://api.exotel.com/v1/Accounts/acme1/Calls/connect.json"
    assert req.get_method() == "POST"
    auth = req.get_header("Authorization").split()[1]
    assert base64.b64decode(auth).decode() == "key1:tok1"
    form = dict(urllib.parse.parse_qsl(req.data.decode()))
    assert form["From"] == "09876543210"
    assert form["CallerId"] == "08012345678"
    assert form["Url"] == "http://my.exotel.com/acme1/exoml/start_voice/998877"
    assert form["CustomField"] == "call-1"
    assert form["StatusCallback"] == "https://hv.test/exotel/status/wstoken"


def test_exotel_http_error_becomes_dial_error_without_secrets():
    def opener(req, timeout):
        raise urllib.error.HTTPError(
            req.full_url, 403, "Forbidden", {}, io.BytesIO(b'{"message":"not verified"}')
        )

    with pytest.raises(DialError) as err:
        ExotelDialer(settings(), opener=opener).dial("+919876543210", "c")
    assert "403" in str(err.value) and "tok1" not in str(err.value)


def test_exotel_reply_without_sid_is_an_error():
    def opener(req, timeout):
        return FakeResponse(b'{"RestException": {"Message": "bad"}}')

    with pytest.raises(DialError):
        ExotelDialer(settings(), opener=opener).dial("+919876543210", "c")


def test_plivo_dialer_uses_per_call_urls():
    class Calls:
        def create(self, **kw):
            self.kw = kw
            return {"request_uuid": "req-9"}

    class Client:
        calls = Calls()

    d = PlivoDialer(settings(plivo_number="+918000000000"), client=Client())
    assert d.dial("+919876543210", "abc") == "req-9"
    kw = Client.calls.kw
    assert kw["answer_url"] == "https://hv.test/pv/ivr/start?call=abc"
    assert kw["hangup_url"] == "https://hv.test/pv/hangup?call=abc"


def test_missing_config_per_provider():
    assert missing_config(settings()) == []
    assert missing_config(settings(exotel_app_id="")) == ["EXOTEL_APP_ID"]
    assert "PLIVO_AUTH_ID" in missing_config(settings(telephony_provider="plivo"))
    assert missing_config(settings(telephony_provider="nope"))[0].startswith("TELEPHONY_PROVIDER")
