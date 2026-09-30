"""The training / livelihood options said on the call (P34), in the caller's language.

Only facts from the sample dataset are spoken (the SkillCall "SATYA" rule): what the option is,
roughly how long it takes, the fee, and how far the centre is. Everything else (reasons, skill
gap, scheme details) is shown to the team on the console.
"""

import math
from functools import lru_cache

from core import geo, sample_data
from core.dialogue.prompts import fill, local_title
from core.dialogue.summary import EDUCATION, NO_EDUCATION, NO_OCCUPATION
from core.recommend import Option
from core.search.seed import load_seed

WHAT = {
    "upskill": {
        "hi-IN": "{trade} की एडवांस ट्रेनिंग",
        "en-IN": "advanced training as a {trade}",
        "mr-IN": "{trade} चे पुढचे प्रशिक्षण",
    },
    "certificate": {
        "hi-IN": "आपके {trade} के हुनर का सरकारी सर्टिफ़िकेट",
        "en-IN": "a government certificate for your skills as a {trade}",
        "mr-IN": "तुमच्या {trade} कौशल्याचे सरकारी प्रमाणपत्र",
    },
    "vishwakarma": {
        "hi-IN": "पीएम विश्वकर्मा: ट्रेनिंग, औज़ारों के लिए मदद और लोन",
        "en-IN": "PM Vishwakarma: training, help for tools, and a loan",
        "mr-IN": "पीएम विश्वकर्मा: प्रशिक्षण, अवजारांसाठी मदत आणि कर्ज",
    },
    "startup": {
        "hi-IN": "अपना काम शुरू करने की ट्रेनिंग, और {loan} से लोन में मदद",
        "en-IN": "training to start your own work, with loan help from {loan}",
        "mr-IN": "स्वतःचे काम सुरू करण्याचे प्रशिक्षण, आणि {loan} मधून कर्जासाठी मदत",
    },
}
LINE = {
    "hi-IN": "रास्ता {n}: {what}, {parts}।",
    "en-IN": "Option {n}: {what}, {parts}.",
    "mr-IN": "पर्याय {n}: {what}, {parts}.",
}
# (one, many) for days, weeks and months
UNITS = {
    "hi-IN": (("दिन", "दिन"), ("हफ़्ता", "हफ़्ते"), ("महीना", "महीने")),
    "en-IN": (("day", "days"), ("week", "weeks"), ("month", "months")),
    "mr-IN": (("दिवस", "दिवस"), ("आठवडा", "आठवडे"), ("महिना", "महिने")),
}
FREE = {"hi-IN": "मुफ़्त", "en-IN": "free", "mr-IN": "मोफत"}
FEE = {"hi-IN": "{fee} रुपये फ़ीस", "en-IN": "fee {fee} rupees", "mr-IN": "{fee} रुपये फी"}
KM = {"hi-IN": "{km} किलोमीटर दूर", "en-IN": "{km} kilometres away", "mr-IN": "{km} किलोमीटर दूर"}
HOSTEL = {
    "hi-IN": "{district} में, हॉस्टल के साथ",
    "en-IN": "in {district}, with a hostel",
    "mr-IN": "{district} मध्ये, वसतिगृहासह",
}


def _lang(language: str) -> str:
    return language if language in LINE else "hi-IN"


@lru_cache(maxsize=1)
def _titles() -> dict[str, tuple[str, str, str]]:
    return {r.nco_code: (r.title_en, r.title_hi, r.title_mr) for r in load_seed()}


def trade_name(code: str, language: str) -> str:
    en, hi, mr = _titles().get(code, (code, code, code))
    return local_title(_lang(language), en, hi, mr)


def duration(hours: int, language: str) -> str:
    """Roughly how long a course takes, in the words a caller uses."""
    if hours <= 48:
        count, unit = math.ceil(hours / 8), 0
    elif hours <= 160:
        count, unit = math.ceil(hours / 40), 1
    else:
        count, unit = max(1, round(hours / 100)), 2
    one, many = UNITS[_lang(language)][unit]
    return f"{count} {one if count == 1 else many}"


def _district_name(code: str, language: str) -> str:
    for row in geo.table().values():
        if row["district_code"] == code:
            return geo.district_name(row, _lang(language))
    return code


def option_line(n: int, option: Option, occupation: str, language: str) -> str:
    lang = _lang(language)
    data = sample_data.load()
    course = option.course
    if course.kind == "startup" and course.scheme == "PM-VISHWAKARMA":
        what = WHAT["vishwakarma"][lang]
    elif course.kind == "startup":
        scheme = data.schemes.get(option.loan_scheme or "")
        loan = {"hi-IN": scheme.name_hi, "mr-IN": scheme.name_mr}.get(lang) if scheme else None
        loan = loan or (scheme.name_en if scheme else "")
        what = WHAT["startup"][lang].format(loan=loan)
    else:
        trade = occupation if option.fit == "same_trade" else next(iter(course.nco_codes))
        what = WHAT[course.kind][lang].format(trade=trade_name(trade, lang))
    parts = [duration(course.hours, lang)]
    parts.append(FREE[lang] if course.fee_inr == 0 else FEE[lang].format(fee=course.fee_inr))
    centre = option.centre
    if centre is not None:
        if any(code == "hostel" for code, _ in option.reasons):  # in another district
            parts.append(HOSTEL[lang].format(district=_district_name(centre.district_code, lang)))
        else:
            parts.append(KM[lang].format(km=centre.distance_km))
    return LINE[lang].format(n=n, what=what, parts=", ".join(parts))


def options_text(language: str, education: str, occupation: str, options: list[Option]) -> str:
    """P34: what we noted, then each option with its key, then "none of these"."""
    lang = _lang(language)
    lines = " ".join(option_line(i, o, occupation, lang) for i, o in enumerate(options, 1))
    return fill(
        lang,
        "P34",
        education=EDUCATION[lang].get(education, NO_EDUCATION[lang]),
        occupation=trade_name(occupation, lang) if occupation else NO_OCCUPATION[lang],
        count=str(len(options)),
        options=lines,
        none_key=str(len(options) + 1),
    )


KIND_EN = {
    "upskill": "a training course",
    "certificate": "a government certificate for the skills you already have",
    "startup": "help to start your own work",
}


def detail_text_en(option: Option, occupation: str) -> str:
    """Everything about one option, in plain English, only from the dataset. It is translated
    into the caller's language before it is spoken."""
    data = sample_data.load()
    c = option.course
    parts = [f"{c.title_en}. This is {KIND_EN.get(c.kind, 'a course')}."]
    if c.skills:
        parts.append(f"You will learn: {', '.join(c.skills)}.")
    if c.kind == "certificate":
        parts.append(
            "There is a short test of what you already know, and then you get the "
            "certificate. It helps you get better work and pay."
        )
    parts.append(
        f"It takes about {duration(c.hours, 'en-IN')}, and it is "
        f"{'free' if c.fee_inr == 0 else f'{c.fee_inr} rupees'}."
    )
    if option.centre is not None:
        where = (
            f"It is at the {option.centre.name_en}, about {option.centre.distance_km} "
            "kilometres away."
        )
        if option.centre.hostel:
            where += " There is a hostel."
        parts.append(where)
    if c.placement:
        parts.append("After the course, the centre helps you find a job.")
    scheme = data.schemes.get(c.scheme)
    if scheme:
        parts.append(f"It is under {scheme.name_en}: {scheme.benefit_en}.")
    loan = data.schemes.get(option.loan_scheme or "")
    if loan and loan.scheme != c.scheme and c.kind == "startup":
        parts.append(f"For a loan, {loan.name_en} can help: {loan.benefit_en}.")
    return " ".join(parts)


def detail_fallback(option: Option, occupation: str, language: str) -> str:
    """A short local-language version (no translation needed) for when Sarvam cannot translate:
    the same words as the option in P34, without its number."""
    line = option_line(1, option, occupation, language)
    return line.split(":", 1)[1].strip() if ":" in line else line
