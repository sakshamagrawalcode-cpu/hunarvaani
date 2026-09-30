import re

import pytest

from core.dialogue.prompts import DYNAMIC, PROMPTS, audio_dir_name, fill, prerendered_ids
from core.tts import MAX_CHARS

DEVANAGARI = re.compile(r"[ऀ-ॿ]")


IDS = [f"P{i:02d}" for i in range(1, 35)]


@pytest.mark.parametrize("language", ["hi-IN", "en-IN", "mr-IN"])
def test_every_language_has_every_prompt(language):
    assert list(PROMPTS[language]) == IDS


@pytest.mark.parametrize("language", ["hi-IN", "en-IN", "mr-IN"])
def test_prompts_are_in_their_script_and_within_the_tts_limit(language):
    for pid, text in PROMPTS[language].items():
        assert bool(DEVANAGARI.search(text)) == (language != "en-IN"), (language, pid)
        assert len(text) <= MAX_CHARS, (language, pid)


@pytest.mark.parametrize("language", ["hi-IN", "en-IN", "mr-IN"])
def test_only_dynamic_prompts_have_placeholders(language):
    for pid, text in PROMPTS[language].items():
        assert ("{" in text) == (pid in DYNAMIC), (language, pid)


def test_options_always_name_their_key():
    """Every yes/no question says which key means what, in every language."""
    for language in PROMPTS:
        for pid in ("P03", "P06", "P07", "P08"):
            assert "1" in PROMPTS[language][pid] and "2" in PROMPTS[language][pid]


def test_prerendered_ids_exclude_dynamic():
    ids = prerendered_ids("hi-IN")
    assert len(ids) == 30 and not set(ids) & DYNAMIC


def test_fill_dynamic_prompts():
    p13 = fill("hi-IN", "P13", options="सिलाई के लिए 1 दबाइए।", none_key="2")
    assert "सिलाई" in p13 and "{" not in p13
    p15 = fill("hi-IN", "P15", education="दसवीं", occupation="दर्ज़ी")
    assert "दसवीं" in p15 and "ओटीपी" in p15


def test_fill_rejects_missing_values():
    with pytest.raises(KeyError):
        fill("hi-IN", "P13", options="सिलाई के लिए 1 दबाइए।")


def test_audio_dir_name():
    assert audio_dir_name("hi-IN") == "hi"
