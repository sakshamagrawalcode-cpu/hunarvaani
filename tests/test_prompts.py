import re

import pytest

from core.dialogue.prompts import DYNAMIC, PROMPTS, audio_dir_name, fill, prerendered_ids
from core.tts import MAX_CHARS

DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def test_all_eighteen_hindi_prompts_exist():
    assert list(PROMPTS["hi-IN"]) == [f"P{i:02d}" for i in range(1, 19)]


def test_prompts_are_hindi_and_within_the_tts_limit():
    for pid, text in PROMPTS["hi-IN"].items():
        assert DEVANAGARI.search(text), pid
        assert len(text) <= MAX_CHARS, pid


def test_only_dynamic_prompts_have_placeholders():
    for pid, text in PROMPTS["hi-IN"].items():
        assert ("{" in text) == (pid in DYNAMIC), pid


def test_prerendered_ids_exclude_dynamic():
    ids = prerendered_ids("hi-IN")
    assert len(ids) == 16 and not set(ids) & DYNAMIC


def test_fill_dynamic_prompts():
    p13 = fill("hi-IN", "P13", occupation_1="सिलाई", occupation_2="बिजली का काम")
    assert "सिलाई" in p13 and "{" not in p13
    p15 = fill("hi-IN", "P15", education="दसवीं", occupation="दर्ज़ी")
    assert "दसवीं" in p15 and "ओटीपी" in p15


def test_fill_rejects_missing_values():
    with pytest.raises(KeyError):
        fill("hi-IN", "P13", occupation_1="सिलाई")


def test_audio_dir_name():
    assert audio_dir_name("hi-IN") == "hi"
