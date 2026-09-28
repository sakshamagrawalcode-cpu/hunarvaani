from plivo.utils.signature_v3 import validate_v3_signature


def is_valid(
    public_base_url: str,
    path_and_query: str,
    params: dict,
    signature: str | None,
    nonce: str | None,
    auth_token: str,
) -> bool:
    """Check Plivo's V3 signature against the public URL Plivo actually called.

    Fails closed: a missing token, URL, header or a malformed value is invalid.
    """
    if not (auth_token and public_base_url and signature and nonce):
        return False
    uri = public_base_url.rstrip("/") + path_and_query
    try:
        return bool(validate_v3_signature("POST", uri, nonce, auth_token, signature, dict(params)))
    except Exception:
        return False
