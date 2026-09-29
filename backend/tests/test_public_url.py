import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "set_public_url", Path(__file__).resolve().parents[2] / "scripts" / "set_public_url.py"
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_find_tunnel_url_picks_the_latest():
    logs = (
        "tunnel-1 | 2026 INF |  https://old-name-one.trycloudflare.com  |\n"
        "tunnel-1 | 2026 INF |  https://new-name-two.trycloudflare.com  |\n"
        "tunnel-1 | 2026 INF | api.cloudflare.com is not a tunnel address\n"
    )
    assert mod.find_tunnel_url(logs) == "https://new-name-two.trycloudflare.com"


def test_find_tunnel_url_none_when_absent():
    assert mod.find_tunnel_url("starting tunnel\nconnecting") is None


def test_set_env_value_replaces_and_appends():
    text = "A=1\nPUBLIC_BASE_URL=\nB=2\n"
    assert mod.set_env_value(text, "PUBLIC_BASE_URL", "https://x.test") == (
        "A=1\nPUBLIC_BASE_URL=https://x.test\nB=2\n"
    )
    assert mod.set_env_value("A=1\n", "PUBLIC_BASE_URL", "https://x.test") == (
        "A=1\nPUBLIC_BASE_URL=https://x.test\n"
    )
