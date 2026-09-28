from core.plivo_sig import is_valid
from tests.plivo_signing import plivo_headers

BASE = "https://hv.example"
PARAMS = {"From": "919876543210", "To": "918000000000", "CallUUID": "abc-123"}


def _check(path, params, headers, token="tok"):
    return is_valid(
        BASE,
        path,
        params,
        headers.get("X-Plivo-Signature-V3"),
        headers.get("X-Plivo-Signature-V3-Nonce"),
        token,
    )


def test_valid_signature_passes():
    h = plivo_headers(BASE + "/pv/answer", PARAMS, "tok")
    assert _check("/pv/answer", PARAMS, h)


def test_query_string_is_part_of_the_signature():
    h = plivo_headers(BASE + "/pv/hangup?call=1111", PARAMS, "tok")
    assert _check("/pv/hangup?call=1111", PARAMS, h)
    assert not _check("/pv/hangup?call=2222", PARAMS, h)


def test_tampered_param_fails():
    h = plivo_headers(BASE + "/pv/answer", PARAMS, "tok")
    assert not _check("/pv/answer", {**PARAMS, "From": "919999999999"}, h)


def test_wrong_token_fails():
    h = plivo_headers(BASE + "/pv/answer", PARAMS, "other-token")
    assert not _check("/pv/answer", PARAMS, h)


def test_missing_headers_or_token_fail_closed():
    h = plivo_headers(BASE + "/pv/answer", PARAMS, "tok")
    assert not _check("/pv/answer", PARAMS, {})
    assert not _check("/pv/answer", PARAMS, h, token="")
    assert not is_valid("", "/pv/answer", PARAMS, "x", "y", "tok")
