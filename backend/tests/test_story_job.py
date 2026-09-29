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
INDEX = NcoIndex(
    [
        Occupation(r.nco_code, r.title_en, r.title_hi, r.aliases, None, r.title_mr)
        for r in load_seed()
    ]
)
JOB = {"call_id": "c1", "path": "/x.wav", "language": "hi-IN"}


def run(transcript=None, error=None, index=INDEX, language="hi-IN", fail_tts=False):
    rendered = []

    def stt(path, language, key):
        if error:
            raise error
        return transcript

    def render(text, language):
        if fail_tts:
            raise RuntimeError("tts down")
        rendered.append(text)
        return f"DYN:{len(rendered)}" if text.startswith(("आपने", "You", "तुम्ही")) else "DYN:q"

    job = {**JOB, "language": language}
    return story_job.process(job, SETTINGS, index, None, stt, render), rendered


def test_confident_story_says_what_we_heard_and_reads_back():
    out, rendered = run("मैं सिलाई का काम करती हूं।")
    assert out["candidates"][0] == "7531" and 1 <= len(out["candidates"]) <= 3
    assert out["readback"] == ["DYN:q"] and len(out["heard"]) == 1
    assert "आपने बताया: मैं सिलाई का काम करती हूं।" in rendered
    n = len(out["candidates"])
    assert any(
        r.startswith("हमारी समझ से, आपका काम इनमें से एक है। दर्ज़ी के लिए 1 दबाइए।")
        and r.endswith(f"अगर इनमें से कोई नहीं, तो {n + 1} दबाइए।")
        for r in rendered
    )
    assert "error" not in out and out["stt_ms"] >= 0 and out["tts_ms"] >= 0


def test_read_back_in_english_and_marathi():
    _, rendered = run("I repair motorcycles and scooters at a small garage", language="en-IN")
    assert "You said: I repair motorcycles and scooters at a small garage." in rendered
    assert any("one of these. For motor vehicle mechanic, press 1." in r for r in rendered)
    _, rendered = run("मी कपडे शिवते, ब्लाउज आणि ड्रेस बनवते", language="mr-IN")
    assert "तुम्ही सांगितलं: मी कपडे शिवते, ब्लाउज आणि ड्रेस बनवते." in rendered
    assert any("शिंपी साठी 1 दाबा." in r for r in rendered)


def test_long_story_is_trimmed_when_read_back():
    long = " ".join(["सिलाई"] * 40)
    _, rendered = run(long)
    heard = next(r for r in rendered if r.startswith("आपने बताया"))
    assert heard.count("सिलाई") == story_job.HEARD_MAX_WORDS


def test_unclear_story_is_still_said_back():
    out, rendered = run("आज मौसम बहुत अच्छा है")
    assert out["candidates"] == [] and out["readback"] == []
    assert rendered == ["आपने बताया: आज मौसम बहुत अच्छा है।"] and len(out["heard"]) == 1
    assert out["scores"][0]["score"] < story_job.THRESHOLD


def test_empty_transcript_and_errors_never_raise():
    out, rendered = run("")
    assert out["candidates"] == [] and out["transcript"] == "" and rendered == []
    out, _ = run(error=RuntimeError("sarvam down"))
    assert out["readback"] == [] and "sarvam down" in out["error"]
    assert "transcript" not in out
    out, _ = run("सिलाई", index=None)
    assert "seed_nco" in out["error"]
    out, _ = run("मैं सिलाई का काम करती हूं", fail_tts=True)
    assert out["candidates"] == [] and out["heard"] == [] and "tts down" in out["error"]


def test_english_translation_and_spoken_texts_for_the_console():
    def translate(text, language, key):
        assert language == "hi-IN"
        return "I stitch clothes."

    out = story_job.process(
        JOB,
        SETTINGS,
        INDEX,
        None,
        lambda *a: "मैं कपड़े सिलती हूं।",
        lambda text, language: f"DYN:{len(text):024x}",
        translate=translate,
    )
    assert out["transcript_en"] == "I stitch clothes." and out["translate_ms"] >= 0
    assert out["scores"][0]["title_en"] == "Tailor, dressmaker"
    heard, question = out["texts"][out["heard"][0]], out["texts"][out["readback"][0]]
    assert heard == {"text": "आपने बताया: मैं कपड़े सिलती हूं।", "text_en": "You said: I stitch clothes."}
    assert question["text_en"].startswith(
        "We think your work is one of these. For tailor, dressmaker"
    )


def test_translation_failure_never_breaks_the_call():
    def broken(*a):
        raise RuntimeError("translate down")

    out = story_job.process(
        JOB,
        SETTINGS,
        INDEX,
        None,
        lambda *a: "मैं सिलाई का काम करती हूं",
        lambda text, language: "DYN:1",
        translate=broken,
    )
    assert out["candidates"] and out["transcript_en"] is None
    assert "translate down" in out["translate_error"] and "error" not in out


def test_the_english_words_are_searched_too():
    def translate(text, language, key):
        return "I am a tailor, I stitch clothes"

    out = story_job.process(
        JOB,
        SETTINGS,
        INDEX,
        None,
        lambda *a: "मेरा काम ज़रा अलग है",  # no occupation word in the Hindi
        lambda text, language: f"DYN:{len(text):024x}",
        translate=translate,
    )
    assert out["candidates"][0] == "7531" and out["transcript_en"].startswith("I am a tailor")


def test_up_to_three_occupations_are_offered_with_the_next_key_for_none():
    from core.dialogue.prompts import readback_text

    three = readback_text("en-IN", ["tailor", "weaver", "embroiderer"])
    assert three == (
        "We think your work is one of these. For tailor, press 1. For weaver, press 2. "
        "For embroiderer, press 3. If it is none of these, press 4."
    )
    assert readback_text("hi-IN", ["दर्ज़ी"]).endswith("अगर इनमें से कोई नहीं, तो 2 दबाइए।")


def test_best_matches_keeps_each_occupations_best_score():
    top = story_job.best_matches(INDEX, None, ["मेरा काम ज़रा अलग है", "I am a tailor"])
    assert top[0].code == "7531" and top[0].score >= story_job.THRESHOLD
    assert len(top) == story_job.TOP_K and len({c.code for c in top}) == 3
