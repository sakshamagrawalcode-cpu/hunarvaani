from core import story_job
from core.config import Settings
from core.search.nco_search import NcoIndex, Occupation
from core.search.seed import load_seed

SETTINGS = Settings(
    public_base_url="",
    database_url="",
    redis_url="",
    default_language="hi-IN",
    languages=("hi-IN",),
    callback_delay_seconds=5,
    max_triggers_per_day=3,
    daily_call_budget=100,
    quiet_hours="",
    sarvam_api_key="k",
)
INDEX = NcoIndex([Occupation(r.nco_code, r.title_en, r.title_hi, r.aliases) for r in load_seed()])
JOB = {"call_id": "c1", "path": "/x.wav", "language": "hi-IN"}


def run(transcript=None, error=None, index=INDEX):
    rendered = []

    def stt(path, language, key):
        if error:
            raise error
        return transcript

    def render(text, language):
        rendered.append(text)
        return "DYN:abcdef012345"

    return story_job.process(JOB, SETTINGS, index, None, stt, render), rendered


def test_confident_story_gets_a_read_back():
    out, rendered = run("मैं सिलाई का काम करती हूं")
    assert out["candidates"][0] == "7531" and len(out["candidates"]) == 2
    assert out["prompt"] == "DYN:abcdef012345"
    assert rendered[0].startswith("क्या आप दर्ज़ी का काम करते हैं?")
    assert "error" not in out and out["stt_ms"] >= 0


def test_unclear_story_falls_back_to_the_trade_list():
    out, rendered = run("आज मौसम बहुत अच्छा है")
    assert out["candidates"] == [] and out["prompt"] is None and rendered == []
    assert out["scores"][0]["score"] < story_job.THRESHOLD


def test_empty_transcript_and_errors_never_raise():
    out, _ = run("")
    assert out["candidates"] == [] and out["transcript"] == ""
    out, _ = run(error=RuntimeError("sarvam down"))
    assert out["prompt"] is None and "sarvam down" in out["error"]
    out, _ = run("सिलाई", index=None)
    assert "seed_nco" in out["error"]
