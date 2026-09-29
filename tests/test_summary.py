from core.dialogue.summary import NO_EDUCATION, NO_OCCUPATION, summary_text


def test_summary_says_what_we_wrote_and_the_safety_line():
    text = summary_text("hi-IN", "upto_8th", "मोबाइल मिस्त्री")
    assert "आठवीं तक पढ़ाई, मोबाइल मिस्त्री" in text
    assert text.endswith("हुनरवाणी कभी पैसे या ओटीपी नहीं माँगता।")


def test_summary_with_missing_answers():
    text = summary_text("hi-IN", "", None)
    assert NO_EDUCATION in text and NO_OCCUPATION in text
