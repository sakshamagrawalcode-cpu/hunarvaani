"""The closing summary (P15): what we wrote down, said back to the caller."""

from core.dialogue.prompts import fill

EDUCATION_HI = {
    "none": "पढ़ाई नहीं की",
    "upto_5th": "पाँचवीं तक पढ़ाई",
    "upto_8th": "आठवीं तक पढ़ाई",
    "10th": "दसवीं पास",
    "12th": "बारहवीं पास",
    "iti_or_diploma": "आईटीआई या डिप्लोमा",
    "graduate": "ग्रेजुएट",
}
NO_EDUCATION = "पढ़ाई की जानकारी नहीं मिली"
NO_OCCUPATION = "काम की जानकारी नहीं मिली"


def summary_text(language: str, education: str, occupation_title: str | None) -> str:
    return fill(
        language,
        "P15",
        education=EDUCATION_HI.get(education, NO_EDUCATION),
        occupation=occupation_title or NO_OCCUPATION,
    )
