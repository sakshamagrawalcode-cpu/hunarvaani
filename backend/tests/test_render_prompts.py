import importlib.util
import sys
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "render_prompts", Path(__file__).resolve().parents[2] / "scripts" / "render_prompts.py"
)
render = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render)


@pytest.fixture
def fake(tmp_path, monkeypatch):
    calls = []

    def synthesize(text, lang, key, speaker):
        calls.append((lang, text))
        if fake.fail and len(calls) > fake.fail:
            raise render.TtsError('Sarvam returned HTTP 402: {"message":"No credits available."}')
        return b"wav"

    fake.fail = 0
    monkeypatch.setattr(render, "ROOT", tmp_path)
    monkeypatch.setattr(render, "synthesize", synthesize)
    monkeypatch.setattr(render, "to_8k_mono", lambda b: b)
    monkeypatch.setattr(render, "load_env", lambda: None)
    monkeypatch.setenv("SARVAM_API_KEY", "k")
    monkeypatch.setenv("SARVAM_SPEAKER", "")
    fake.calls = calls
    return fake


def run(*args):
    sys.argv = ["render_prompts.py", "--lang", "hi-IN", *args]
    render.main()


def test_renders_only_missing_or_changed_prompts(fake, monkeypatch):
    run()
    first = len(fake.calls)
    assert first == len(render.prerendered_texts("hi-IN"))
    run()
    assert len(fake.calls) == first  # nothing changed, no credits used
    monkeypatch.setitem(render.PROMPTS["hi-IN"], "P04", "नया वाक्य।")
    run()
    assert fake.calls[first:] == [("hi-IN", "नया वाक्य।")]
    run("--force")
    assert len(fake.calls) == 2 * first + 1


def test_old_files_without_a_record_count_as_up_to_date(fake, tmp_path):
    folder = tmp_path / "audio" / "hi"
    folder.mkdir(parents=True)
    (folder / "P01.wav").write_bytes(b"old")
    run("--only", "P01")
    assert fake.calls == [] and (folder / "rendered.json").exists()


def test_stops_at_the_first_no_credits_answer(fake):
    fake.fail = 2
    with pytest.raises(SystemExit):
        run()
    assert len(fake.calls) == 3  # two rendered, the third said no credits, then it stopped
    fake.fail = 0
    run()  # after adding credits: only what is missing
    assert len(fake.calls) == 3 + len(render.prerendered_texts("hi-IN")) - 2
