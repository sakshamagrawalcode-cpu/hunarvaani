"""The closing summary (P15): what we wrote down, said back to the caller."""

from core.dialogue.prompts import fill

EDUCATION = {
    "hi-IN": {
        "none": "पढ़ाई नहीं की",
        "upto_5th": "पाँचवीं तक पढ़ाई",
        "upto_8th": "आठवीं तक पढ़ाई",
        "10th": "दसवीं पास",
        "12th": "बारहवीं पास",
        "iti_or_diploma": "आईटीआई या डिप्लोमा",
        "graduate": "ग्रेजुएट",
    },
    "en-IN": {
        "none": "no schooling",
        "upto_5th": "studied up to fifth class",
        "upto_8th": "studied up to eighth class",
        "10th": "tenth pass",
        "12th": "twelfth pass",
        "iti_or_diploma": "ITI or diploma",
        "graduate": "graduate",
    },
    "mr-IN": {
        "none": "शिक्षण झालं नाही",
        "upto_5th": "पाचवीपर्यंत शिक्षण",
        "upto_8th": "आठवीपर्यंत शिक्षण",
        "10th": "दहावी पास",
        "12th": "बारावी पास",
        "iti_or_diploma": "आयटीआय किंवा डिप्लोमा",
        "graduate": "पदवीधर",
    },
}
NO_EDUCATION = {
    "hi-IN": "पढ़ाई की जानकारी नहीं मिली",
    "en-IN": "education not given",
    "mr-IN": "शिक्षणाची माहिती मिळाली नाही",
}
NO_OCCUPATION = {
    "hi-IN": "काम की जानकारी नहीं मिली",
    "en-IN": "work not given",
    "mr-IN": "कामाची माहिती मिळाली नाही",
}


def summary_text(language: str, education: str, occupation_title: str | None) -> str:
    lang = language if language in EDUCATION else "hi-IN"
    return fill(
        lang,
        "P15",
        education=EDUCATION[lang].get(education, NO_EDUCATION[lang]),
        occupation=occupation_title or NO_OCCUPATION[lang],
    )
