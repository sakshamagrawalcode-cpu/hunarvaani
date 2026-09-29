import math
import struct
import warnings
import wave

from apps.voice.exotel import MAX_PEAK, TARGET_RMS, even_level
from core import prompt_check
from core.dialogue.prompts import PROMPTS

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    import audioop


def tone(amplitude, seconds=1.0, rate=8000, lead=0.0):
    silence = b"\x00\x00" * int(rate * lead)
    n = int(rate * seconds)
    return silence + b"".join(
        struct.pack("<h", int(amplitude * math.sin(2 * math.pi * 440 * i / rate))) for i in range(n)
    )


def write(path, pcm, rate=8000):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)


def test_quiet_and_loud_prompts_come_out_at_the_same_level():
    quiet, loud = even_level(tone(1500)), even_level(tone(30000))
    assert abs(audioop.rms(quiet, 2) - TARGET_RMS) < 150
    assert abs(audioop.rms(loud, 2) - TARGET_RMS) < 150
    assert audioop.max(loud, 2) <= MAX_PEAK


def test_silence_and_already_even_audio_are_left_alone():
    assert even_level(b"\x00\x00" * 800) == b"\x00\x00" * 800
    right = even_level(tone(1500))
    assert even_level(right) == right


def test_check_all_reports_length_level_and_problems(tmp_path):
    audio = tmp_path / "audio"
    write(audio / "hi" / "P01.wav", tone(9000, 2.0))
    write(audio / "hi" / "P02.wav", tone(300, 1.0))  # far too quiet
    write(audio / "hi" / "P03.wav", tone(9000, 1.0, lead=1.5))  # long silence first
    (audio / "hi" / "rendered.json").write_text(
        '{"P01": "%s", "P02": "old-fingerprint"}'
        % prompt_check.fingerprint(PROMPTS["hi-IN"]["P01"], "")
    )
    out = prompt_check.check_all(audio, ("hi-IN",))
    by_id = {p["id"]: p for p in out["prompts"]}
    assert [p["id"] for p in out["prompts"]][:3] == ["P05", "P01", "P02"]  # call order

    p01 = by_id["P01"]["languages"]["hi-IN"]
    assert p01["seconds"] == 2.0 and p01["issues"] == [] and p01["audio"] == "/audio/hi/P01.wav"
    assert -15 < p01["level_db"] < -9

    p02 = by_id["P02"]["languages"]["hi-IN"]["issues"]
    assert "text changed since it was rendered" in p02 and any(
        "silence" in i or i in ("quiet", "silent") for i in p02
    )

    p03 = by_id["P03"]["languages"]["hi-IN"]
    assert p03["silence_start"] == 1.5 and "1.5 s silence at the start" in p03["issues"]

    assert by_id["P04"]["languages"]["hi-IN"]["issues"] == ["not rendered"]
    assert by_id["P13"]["dynamic"] and "audio" not in by_id["P13"]["languages"]["hi-IN"]
