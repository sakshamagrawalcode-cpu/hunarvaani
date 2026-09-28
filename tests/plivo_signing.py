"""Sign test requests exactly the way Plivo does, using the SDK's own V3 helpers."""

from plivo.utils.signature_v3 import construct_post_url, get_signature_v3


def plivo_headers(url: str, params: dict, auth_token: str, nonce: str = "12345678") -> dict:
    base_url = construct_post_url(url, dict(params)).decode("utf-8")
    sig = get_signature_v3(auth_token.encode(), base_url, nonce.encode()).decode()
    return {"X-Plivo-Signature-V3": sig, "X-Plivo-Signature-V3-Nonce": nonce}
