"""Rule-based reading of short spoken answers: numbers, age, studies, travel, yes/no, either/or,
gender, name and training time, in Hindi, Marathi and English.

Two uses: the no-GPU mode (no LLM), and a fast path in real mode: a short answer such as
"पैंतीस साल" or "दसवीं पास" is read here in a millisecond, so the LLM is only called for answers
that need understanding (stories, reasons, preferences). Every result is checked by code anyway.
"""

import re
import unicodedata

from .prompts import NUMBERS

EDUCATION_LEVELS = ("none", "upto_5th", "upto_8th", "10th", "12th", "graduate")


def norm(text: str) -> str:
    """Lower-case, no punctuation, and spelling variants merged (nukta dropped, chandrabindu = anusvara)."""
    text = unicodedata.normalize("NFC", text or "").lower()
    text = text.replace("़", "").replace("ँ", "ं")  # ़ nukta, ँ -> ं
    text = "".join(" " if unicodedata.category(ch)[0] in "PS" else ch for ch in text)
    return re.sub(r"\s+", " ", text).strip()


def _words(text: str) -> list[str]:
    return norm(text).split()


def has(text: str, phrases) -> bool:
    t = f" {norm(text)} "
    return any(f" {norm(ph)} " in t or (len(norm(ph)) > 4 and norm(ph) in t) for ph in phrases)


# numbers --------------------------------------------------------------------------------------
_NUM_WORDS: dict[str, int] = {}
for _lang in ("hi", "mr"):
    for _n, _w in NUMBERS[_lang].items():
        _NUM_WORDS[norm(_w)] = _n
_NUM_WORDS.update({norm(w): n for w, n in (("छः", 6), ("छे", 6), ("पांच", 5), ("उनतीस", 29), ("उन्नतीस", 29),
                                           ("एकसो", 100), ("सौ", 100), ("डेढ", 1), ("दोनो", 2))})
_EN_ONES = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve "
                                       "thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())}
_EN_TENS = {w: 10 * i for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()) if i >= 2}


def numbers(text: str) -> list[tuple[int, int]]:
    """Every number in the text as (value, word position): digits, Hindi/Marathi words, English words."""
    out = []
    words = _words(text.replace("-", " "))
    i = 0
    while i < len(words):
        w = words[i]
        if w.isdigit():
            out.append((int(w), i))
        elif re.fullmatch(r"\d+[a-zऀ-ॿ]+", w):  # "35साल", "10th"
            out.append((int(re.match(r"\d+", w).group(0)), i))
        elif w in _NUM_WORDS:
            out.append((_NUM_WORDS[w], i))
        elif w in _EN_TENS:
            v = _EN_TENS[w]
            if i + 1 < len(words) and words[i + 1] in _EN_ONES and _EN_ONES[words[i + 1]] < 10:
                v += _EN_ONES[words[i + 1]]
                i += 1
            out.append((v, i))
        elif w in _EN_ONES:
            out.append((_EN_ONES[w], i))
        i += 1
    return out


NEG = ["नहीं", "नही", "नाही", "नको", "not", "no", "never", "didn't", "didnt", "can't", "cannot", "dont", "don't",
       "मत", "न"]


def negated(text: str, phrases) -> bool:
    """Is one of the phrases negated ("कॉलेज नहीं", "बाहर रह नहीं सकती", "not to college")?"""
    words = _words(text)
    joined = " ".join(words)
    for ph in phrases:
        ph_n = norm(ph)
        pos = joined.find(ph_n)
        if pos < 0:
            continue
        start = len(joined[:pos].split())
        end = start + len(ph_n.split())
        around = words[max(0, start - 2): start] + words[end: end + 3]
        if any(w in NEG for w in around):
            return True
    return False


AGE_WORDS = ["साल", "वर्ष", "वर्षं", "वर्षे", "years", "year", "yrs", "उम्र", "वय", "age", "बरस"]
_AGE_MARK = ["उम्र", "वय", "age", "aged"]
_SINCE = ["से", "पासून", "from", "since", "वर्षांपासून", "वर्षापासून"]


def parse_age(text: str) -> int | None:
    """'पैंतीस साल' -> 35; 'बीस साल से सिलाई, उम्र पचास' -> 50 (years of work are not an age)."""
    nums = [(v, i) for v, i in numbers(text) if 14 <= v <= 80]
    if not nums:
        return None
    words = _words(text)
    marked = [v for v, i in nums if any(w in _AGE_MARK for w in words[max(0, i - 3): i])
              or words[i + 1: i + 3][-1:] in (["की"], ["का"], ["old"], ["चा"], ["ची"])]
    if marked:
        return marked[0]
    not_since = [(v, i) for v, i in nums if not any(w in _SINCE for w in words[i + 1: i + 3])]
    near = [v for v, i in not_since if any(w in AGE_WORDS for w in words[max(0, i - 2): i + 3])]
    if near:
        return near[0]
    return not_since[0][0] if not_since else None


# studies ---------------------------------------------------------------------------------------
_ORDINALS = {
    1: ["पहली", "पहिली", "first", "1st"], 2: ["दूसरी", "दुसरी", "second", "2nd"], 3: ["तीसरी", "तिसरी", "third", "3rd"],
    4: ["चौथी", "fourth", "4th"], 5: ["पांचवीं", "पांचवी", "पाचवी", "fifth", "5th"], 6: ["छठी", "छठवीं", "सहावी", "sixth", "6th"],
    7: ["सातवीं", "सातवी", "seventh", "7th"], 8: ["आठवीं", "आठवी", "eighth", "8th"], 9: ["नौवीं", "नववी", "नवमी", "ninth", "9th"],
    10: ["दसवीं", "दसवी", "दहावी", "tenth", "10th", "मैट्रिक", "matric", "ssc", "एसएससी", "हाईस्कूल", "हाई स्कूल"],
    11: ["ग्यारहवीं", "अकरावी", "eleventh", "11th"],
    12: ["बारहवीं", "बारहवी", "बारावी", "twelfth", "12th", "इंटर", "inter", "hsc", "एचएससी", "इंटरमीडिएट"],
}
_GRADUATE = ["ग्रेजुएट", "graduate", "graduation", "बीए", "बी ए", "ba", "bcom", "बीकॉम", "बी कॉम", "bsc", "बीएससी",
             "degree", "डिग्री", "पदवी", "पदवीधर", "एमए", "ma", "कॉलेज", "college"]
_AFTER_10TH = ["डिप्लोमा", "diploma", "आईटीआई", "iti", "पॉलिटेक्निक", "polytechnic"]  # counted like class 12
_NO_SCHOOL = ["अनपढ़", "अनपढ", "नहीं पढ़", "नहीं पढ", "पढ़ाई नहीं", "पढाई नहीं", "निरक्षर", "शिक्षण नाही", "शाळा नाही",
              "शाळेत गेलो नाही", "शाळेत गेले नाही", "no school", "no schooling", "never studied", "illiterate", "नहीं पढ़ी",
              "नहीं पढ़ा", "स्कूल नहीं"]
_FAIL = ["फेल", "fail", "failed", "नापास", "अनुत्तीर्ण"]


def _class_level(n: int) -> str:
    if n <= 0:
        return "none"
    if n <= 5:
        return "upto_5th"
    if n <= 9:
        return "upto_8th"
    if n <= 11:
        return "10th"
    return "12th"


def parse_education(text: str) -> str | None:
    fail = has(text, _FAIL)
    if has(text, _GRADUATE) and not negated(text, _GRADUATE):
        return "graduate"
    if has(text, _AFTER_10TH) and not negated(text, _AFTER_10TH):
        return "12th"
    for n in sorted(_ORDINALS, reverse=True):  # "आठवीं के बाद पढ़ाई नहीं की" is class 8, not no schooling
        if has(text, _ORDINALS[n]):
            return _class_level(n - 1 if fail else n)
    words = _words(text)
    for v, i in numbers(text):  # "कक्षा 7", "class 9", "7 तक"
        ctx = words[max(0, i - 2): i + 3]
        if 1 <= v <= 12 and (any(w in ("कक्षा", "class", "इयत्ता", "क्लास", "तक", "पर्यंत", "पास", "pass", "standard", "std")
                                 for w in ctx) or len(words) <= 3):
            return _class_level(v - 1 if fail else v)
    if has(text, _NO_SCHOOL):
        return "none"
    return None


# travel ----------------------------------------------------------------------------------------
_KM = ["किलोमीटर", "किमी", "km", "kms", "kilometre", "kilometres", "kilometer", "kilometers", "किलो"]
_MIN = ["मिनट", "minute", "minutes", "mins", "min", "मिनिट", "मिनिटं"]
_HOUR = ["घंटा", "घंटे", "घण्टा", "hour", "hours", "तास"]
_HOSTEL = ["हॉस्टल", "होस्टल", "hostel", "वसतिगृह", "बाहर रह", "बाहर भी रह", "रह सकता", "रह सकती", "राहू शकतो", "राहू शकते",
           "बाहेर राहू", "बाहर रहना ठीक", "stay outside", "can stay"]
_NO_HOSTEL = ["हॉस्टल नहीं", "बाहर नहीं रह", "घर नहीं छोड़", "घर नहीं छोड", "वसतिगृह नाही", "घर सोडू शकत नाही",
              "no hostel", "cannot stay", "can't stay"]
_NEAR = ["पास में ही", "पास ही", "गाँव में ही", "गांव में ही", "घर के पास", "जवळच", "गावातच", "nearby only", "close to home",
         "near my home", "मोहल्ले में"]
_ANY = ["कहीं भी", "कितना भी", "कितनी भी", "कुठेही", "कितीही", "anywhere", "any distance", "दूर भी"]
_SPEED = [(["पैदल", "चलकर", "चालत", "walk", "walking", "on foot"], 4), (["साइकिल", "सायकल", "cycle", "bicycle"], 10),
          (["बाइक", "मोटरसाइकिल", "स्कूटी", "स्कूटर", "गाड़ी", "गाडी", "bike", "scooter", "motorcycle", "car"], 25)]
_HALF = ["आधा घंटा", "आधे घंटे", "अर्धा तास", "half an hour", "half hour"]
_ONE_HALF = ["डेढ़ घंटा", "डेढ घंटा", "दीड तास", "one and a half hour", "an hour and a half"]


def parse_travel(text: str) -> dict:
    """{'km': int|None, 'hostel_ok': bool|None, 'cannot_leave_home': bool|None}."""
    out: dict = {"km": None, "hostel_ok": None, "cannot_leave_home": None}
    words = _words(text)
    speed = next((v for phrases, v in _SPEED if has(text, phrases)), 20)  # bus by default
    for v, i in numbers(text):
        ctx = words[i + 1: i + 3]
        if any(w in _KM for w in ctx) and 0 < v <= 200:
            out["km"] = v
            break
        if any(w in _MIN for w in ctx) and 0 < v <= 240:
            out["km"] = max(1, round(v / 60 * speed))
            break
        if any(w in _HOUR for w in ctx) and 0 < v <= 5:
            out["km"] = round(v * speed)
            break
    if out["km"] is None:
        if has(text, _HALF):
            out["km"] = round(0.5 * speed)
        elif has(text, _ONE_HALF):
            out["km"] = round(1.5 * speed)
        elif has(text, ["एक घंटा", "एक तास", "one hour", "an hour"]):
            out["km"] = speed
        elif has(text, _NEAR):
            out["km"] = 5
        elif has(text, _ANY):
            out["km"] = 30
        else:  # a bare number: "दस", "15"
            nums = [v for v, _ in numbers(text) if 1 <= v <= 100]
            if nums and len(words) <= 4:
                out["km"] = nums[0]
    any_negated = has(text, _ANY) and negated(text, _ANY)  # "कहीं भी नहीं जा सकती"
    if any_negated and out["km"] == 30:
        out["km"] = 5
    if has(text, _NO_HOSTEL) or (has(text, _HOSTEL) and negated(text, _HOSTEL)) or any_negated:
        out["hostel_ok"] = False
        out["cannot_leave_home"] = has(text, ["घर नहीं छोड़", "घर नहीं छोड", "घर सोडू शकत नाही", "बच्चे", "मुलं",
                                              "बाहर रह नहीं", "बाहेर राहू शकत नाही", "can't stay", "cannot stay"]) or None
    elif has(text, _HOSTEL) or has(text, _ANY):
        out["hostel_ok"] = True
    return out


# yes / no, either / or, gender, name ----------------------------------------------------------
_YES_IDIOMS = ["कोई बात नहीं", "कोई दिक्कत नहीं", "कोई परेशानी नहीं", "क्यों नहीं", "हरकत नाही", "काही हरकत नाही",
               "का नाही", "no problem", "why not", "not a problem", "कोई प्रॉब्लम नहीं"]
_NO = ["नहीं", "नही", "नाही", "नको", "no", "nahi", "nope", "बिल्कुल नहीं", "मत", "never"]
_YES = ["हाँ", "हां", "हो", "होय", "yes", "yeah", "yep", "haan", "han", "बिल्कुल", "ज़रूर", "जरूर", "हाँ जी",
        "जी हाँ", "जी हां", "ठीक है", "चलेगा", "चालेल", "okay", "ok", "sure", "पसंद", "हव", "हवं", "हवे", "बरोबर", "सही"]


def parse_yes_no(text: str) -> bool | None:
    """True / False, or None when unclear (then the LLM, or the person, decides)."""
    words = _words(text)
    if not words:
        return None
    if words in (["ना"], ["न"], ["ना", "जी"]):
        return False
    if has(text, _YES_IDIOMS):  # "हाँ, कोई बात नहीं", "हो, हरकत नाही", "yes, no problem"
        return True
    yes, no = has(text, _YES), has(text, _NO)
    if yes and no:
        return None
    if no:
        return False
    if yes:
        return True
    return None


def parse_choice(text: str, first: list[str], second: list[str], third: list[str] | None = None) -> int | None:
    """Which option of an either/or question the answer picks: 1, 2 (or 3), or None if unclear."""
    hits = [has(text, first), has(text, second), bool(third) and has(text, third)]
    if sum(hits) == 1:
        return hits.index(True) + 1
    if hits[2]:  # "both"/"either" wins over naming both options
        return 3
    return None


def parse_gender(text: str) -> str | None:
    if has(text, ["नहीं बताना", "नहीं बताऊंगी", "नहीं बताऊंगा", "सांगायचं नाही", "prefer not", "don't want to say", "रहने दो"]):
        return "other"
    if has(text, ["महिला", "औरत", "स्त्री", "लड़की", "लडकी", "female", "woman", "lady", "girl", "बाई", "मुलगी", "स्त्रीं"]):
        return "female"
    if has(text, ["पुरुष", "पुरूष", "आदमी", "मर्द", "लड़का", "लडका", "male", "man", "boy", "मुलगा", "gents"]):
        return "male"
    return None


_NAME_FILLER = ["मेरा", "नाम", "है", "हैं", "मैं", "मै", "जी", "हूँ", "हूं", "मुझे", "कहते", "बोलते", "लोग", "my", "name",
                "is", "i", "am", "im", "it's", "its", "this", "माझं", "माझे", "माझा", "नाव", "आहे", "मी", "सर", "मैडम",
                "का", "की", "के", "the", "called", "हमारा", "हम", "ओ", "तो"]


def parse_name(text: str) -> str | None:
    """'मेरा नाम सुनीता कांबले है' -> 'सुनीता कांबले'. At most four words; the person checks it at the end."""
    raw = re.sub(r"[^\w\sऀ-ॿ]", " ", text or "")
    words = [w for w in raw.split() if norm(w) not in {norm(f) for f in _NAME_FILLER} and not w.isdigit()]
    if not words:
        return None
    name = " ".join(words[:4])
    return name.title() if name.isascii() else name


def parse_duration_weeks(text: str) -> int | None:
    """Longest training the person can do, in weeks. 0 means 'any length'."""
    if has(text, _ANY + ["जितना भी", "जितना समय", "कितना भी समय", "any time", "as long as", "कितीही वेळ"]):
        return 0
    words = _words(text)
    for v, i in numbers(text):
        ctx = words[i + 1: i + 3]
        if any(w.startswith(("महीन", "महिन", "month")) for w in ctx):
            return max(1, round(v * 4.3))
        if any(w.startswith(("हफ्त", "हफ़्त", "सप्ताह", "आठवड", "week")) for w in ctx):
            return max(1, v)
        if any(w in ("साल", "वर्ष", "year", "years") for w in ctx):
            return v * 52
        if any(w in ("दिन", "दिवस", "day", "days") for w in ctx):
            return max(1, round(v / 7))
    if has(text, ["एक महीना", "एक महिना", "a month", "one month", "महीना भर"]):
        return 4
    if has(text, ["थोड़ा", "थोडा", "कम", "short", "जल्दी", "लवकर"]):
        return 4
    return None


def parse_health(text: str) -> str | None:
    trouble = ["तकलीफ", "तकलीफ़", "दिक्कत", "परेशानी", "त्रास", "problem", "trouble", "pain", "दर्द"]
    if has(text, ["थोड़ी", "थोड़ा", "थोडी", "थोडा", "a little", "little", "थोडासा", "कभी कभी"]):
        return "some"
    if negated(text, trouble) or has(text, ["कोई तकलीफ नहीं", "कोई दिक्कत नहीं", "त्रास नाही", "no problem", "none",
                                             "fit", "ठीक हूँ", "ठीक हूं", "बरी आहे", "बरा आहे"]):
        return "none"
    if has(text, ["बहुत", "ज़्यादा", "ज्यादा", "a lot", "खूप", "जास्त", "severe", "चल नहीं", "बीमार"]):
        return "severe"
    if has(text, ["घुटने", "घुटना", "कमर", "दर्द", "pain", "गुडघ"]):
        return "some"
    yn = parse_yes_no(text)
    if yn is False:
        return "none"
    if yn is True:
        return "some"
    return None
