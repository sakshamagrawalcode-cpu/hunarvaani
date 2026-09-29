import base64
import shutil
import struct
import wave

import pytest

from core import tts


def _wav(path, rate=22050, seconds=0.2):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack("<h", 0) * int(rate * seconds))
    return path.read_bytes()


def test_extract_audio_from_audios_list():
    body = {"audios": [base64.b64encode(b"abc").decode()]}
    assert tts.extract_audio(body) == b"abc"


def test_extract_audio_from_single_audio_key():
    assert tts.extract_audio({"audio": base64.b64encode(b"xyz").decode()}) == b"xyz"


def test_extract_audio_rejects_empty_and_multiple():
    with pytest.raises(tts.TtsError):
        tts.extract_audio({})
    with pytest.raises(tts.TtsError):
        tts.extract_audio({"audios": ["YQ==", "Yg=="]})


def test_synthesize_rejects_bad_text_before_any_network_call():
    with pytest.raises(tts.TtsError):
        tts.synthesize("", "hi-IN", "k")
    with pytest.raises(tts.TtsError):
        tts.synthesize("a" * (tts.MAX_CHARS + 1), "hi-IN", "k")


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_to_8k_mono(tmp_path):
    out = tts.to_8k_mono(_wav(tmp_path / "in.wav"))
    (tmp_path / "out.wav").write_bytes(out)
    with wave.open(str(tmp_path / "out.wav")) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (8000, 1, 2)
