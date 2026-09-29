"""Normalising Hindi text so a phone transcript can be matched against occupation aliases."""

import re
import unicodedata

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_NUKTA = "़"
_PUNCT = re.compile(r"[^\w\s]|_|[।॥]")
_SPACES = re.compile(r"\s+")
_VOWEL = "aeiou"

STOPWORDS = frozenset(
    """
    का की के को में से पर है हैं था थी थे हूं हो और या भी तो ही मैं हम मेरा मेरी मेरे हमारा
    हमारी आप वो वह यह ये कुछ बहुत अभी आज कल काम करता करती करते करना करके किया करूं
    रहता रहती रहते जाता जाती जाते नहीं हां हाँ जी
    ka ki ke ko me mein se par hai hain tha thi the hum hun hu ho aur ya bhi to hi main maim
    mera meri mere aap vo voh yah ye kuch bahut abhi aj aja kal kam kaam karat karta karti
    karte karna kiya rahat rahta rahti jat jata jati nahi nah ha han ji
    """.split()
)


def normalise(text: str) -> str:
    """Lower-case, strip punctuation and nukta, unify chandrabindu with anusvara."""
    t = unicodedata.normalize("NFC", text or "")
    t = unicodedata.normalize("NFD", t).replace(_NUKTA, "")
    t = unicodedata.normalize("NFC", t)
    t = t.replace("ँ", "ं").replace("‌", "").replace("‍", "")
    t = "".join(" " if unicodedata.category(c)[0] in "PSZC" else c for c in t.lower())
    return _SPACES.sub(" ", t).strip()


def _drop_schwa(word: str) -> str:
    if len(word) > 3 and word.endswith("a") and word[-2] not in _VOWEL:
        word = word[:-1]
    out = list(word)
    for i in range(2, len(word) - 2):
        if (
            word[i] == "a"
            and word[i - 1] not in _VOWEL
            and word[i - 2] in _VOWEL
            and word[i + 1] not in _VOWEL
            and word[i + 2] in _VOWEL
        ):
            out[i] = ""
    return "".join(out)


def to_latin(text: str) -> str:
    """Rough romanisation of Devanagari, close to how Hindi is typed in Latin ('silai')."""
    from indic_transliteration import sanscript

    t = sanscript.transliterate(normalise(text), sanscript.DEVANAGARI, sanscript.ITRANS).lower()
    for a, b in (("aa", "a"), ("ii", "i"), ("uu", "u"), (".n", "n"), (".m", "m"), (".h", "")):
        t = t.replace(a, b)
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return " ".join(_drop_schwa(w) for w in _SPACES.sub(" ", t).split())


def is_devanagari(text: str) -> bool:
    return bool(DEVANAGARI.search(text))


def content_tokens(text: str) -> list[str]:
    return [w for w in text.split() if w not in STOPWORDS and len(w) > 1]
