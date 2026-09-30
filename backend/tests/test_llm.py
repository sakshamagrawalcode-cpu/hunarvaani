import pytest

from core import llm, story_job

CODES = {"7531", "7231", "7411"}


def test_the_answer_is_checked_before_it_is_used():
    content = (
        "<think>the caller repairs bikes</think> Here: "
        '{"occupations": ["7231", "9999", "7231", "7411"], "years": 10, '
        '"skills": ["engine repair", "brakes"], "wants": "own_work", '
        '"said": "मैं दस साल से बाइक ठीक करता हूं।"}'
    )
    out = llm.parse(content, CODES)
    assert out == {
        "occupations": ["7231", "7411"],
        "years": 10,
        "skills": ["engine repair", "brakes"],
        "wants": "own_work",
        "said": "मैं दस साल से बाइक ठीक करता हूं।",
    }
    odd = llm.parse(
        '{"occupations": [], "years": 300, "wants": "sleep", "said": "' + "a " * 60 + '"}', CODES
    )
    assert odd["years"] is None and odd["wants"] is None and odd["said"] == ""
    with pytest.raises(llm.LlmError):
        llm.parse("sorry, I cannot help", CODES)


def test_the_request_goes_to_sarvam_with_our_list_only(monkeypatch):
    seen = {}

    class Reply:
        status_code = 200

        @staticmethod
        def json():
            return {
                "choices": [
                    {"message": {"content": '{"occupations": ["7531"], "said": "मैं सिलाई करती हूं।"}'}}
                ]
            }

    def post(url, headers, json, timeout):
        seen.update(url=url, headers=headers, body=json, timeout=timeout)
        return Reply()

    monkeypatch.setattr(llm.requests, "post", post)
    out = llm.understand(
        "मैं सिलाई करती हूं",
        "I do tailoring",
        "hi-IN",
        [("7531", "Tailor"), ("7411", "Electrician")],
        "sk_x",
        "sarvam-105b",
        5,
    )
    assert out["occupations"] == ["7531"]
    assert seen["url"] == llm.CHAT_URL and seen["headers"]["api-subscription-key"] == "sk_x"
    assert seen["body"]["model"] == "sarvam-105b" and seen["timeout"] == 5
    system, user = seen["body"]["messages"]
    assert "7531: Tailor" in system["content"] and "Hindi" in system["content"]
    assert "I do tailoring" in user["content"]


def test_errors_are_reported_not_raised_into_the_call(monkeypatch):
    class Reply:
        status_code = 402
        text = "no credits"

    monkeypatch.setattr(llm.requests, "post", lambda *a, **k: Reply())
    with pytest.raises(llm.LlmError, match="402"):
        llm.understand("x", None, "hi-IN", [("7531", "Tailor")], "k", "m")
    with pytest.raises(llm.LlmError, match="empty"):
        llm.understand("x", None, "hi-IN", [("7531", "Tailor")], "", "m")


def process_with(understand, transcript):
    from test_story_job import INDEX, JOB, SETTINGS

    rendered = []

    def render(text, language):
        rendered.append(text)
        return f"DYN:{len(rendered)}"

    out = story_job.process(
        JOB, SETTINGS, INDEX, None, lambda *a: transcript, render, understand=understand
    )
    return out, rendered


def test_the_llm_leads_the_read_back_and_its_sentence_is_said_back():
    def understand(transcript, transcript_en, language):
        return {
            "occupations": ["7231"],
            "years": 10,
            "skills": [],
            "wants": None,
            "said": "मैं दस साल से बाइक ठीक करता हूं।",
        }

    out, rendered = process_with(understand, "बाइक और स्कूटर का काम दस साल से")
    assert out["candidates"][0] == "7231" and out["years"] == 10
    assert rendered[0] == "आपने बताया: मैं दस साल से बाइक ठीक करता हूं।"
    assert story_job.story_fields(out)["llm"]["years"] == 10


def test_the_llm_rescues_a_story_the_word_search_was_unsure_about():
    out, _ = process_with(
        lambda *a: {
            "occupations": ["7531"],
            "years": None,
            "skills": [],
            "wants": None,
            "said": "",
        },
        "हम्म, वो वाला काम",
    )
    assert out["candidates"] == ["7531"] and out["readback"]


def test_a_failing_llm_changes_nothing():
    def broken(*a):
        raise llm.LlmError("Sarvam chat HTTP 402")

    with_llm, _ = process_with(broken, "मैं सिलाई का काम करती हूं")
    without, _ = process_with(None, "मैं सिलाई का काम करती हूं")
    assert with_llm["candidates"] == without["candidates"] and "402" in with_llm["llm_error"]
    assert "llm" not in with_llm
