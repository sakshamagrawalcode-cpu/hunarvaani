from core.dialogue.prompts import local_title
from core.dialogue.summary import NO_EDUCATION, NO_OCCUPATION, summary_text


def test_summary_says_what_we_wrote():
    text = summary_text("hi-IN", "upto_8th", "मोबाइल मिस्त्री")
    assert "आठवीं तक पढ़ाई, और काम: मोबाइल मिस्त्री" in text


def test_summary_with_missing_answers():
    text = summary_text("hi-IN", "", None)
    assert NO_EDUCATION["hi-IN"] in text and NO_OCCUPATION["hi-IN"] in text


def test_summary_in_english_and_marathi():
    en = summary_text("en-IN", "10th", local_title("en-IN", "Tailor, dressmaker", "दर्ज़ी", "शिंपी"))
    assert "We have noted: tenth pass, and work: tailor, dressmaker." in en
    mr = summary_text("mr-IN", "12th", local_title("mr-IN", "Tailor, dressmaker", "दर्ज़ी", "शिंपी"))
    assert "बारावी पास, आणि काम: शिंपी" in mr


def test_unknown_language_falls_back_to_hindi():
    assert summary_text("ta-IN", "10th", None).startswith("धन्यवाद।")
    assert local_title("mr-IN", "Tailor", "दर्ज़ी", "") == "दर्ज़ी"
