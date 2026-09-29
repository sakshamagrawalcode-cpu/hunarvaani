import numpy as np
import pytest

from core.search.nco_search import THRESHOLD, NcoIndex, Occupation
from core.search.seed import load_seed
from core.search.text import normalise, to_latin


@pytest.fixture(scope="module")
def index():
    return NcoIndex(
        [
            Occupation(r.nco_code, r.title_en, r.title_hi, r.aliases, None, r.title_mr)
            for r in load_seed()
        ]
    )


def test_normalise_keeps_hindi_words_whole():
    assert normalise("आज मौसम बहुत अच्छा है।") == "आज मौसम बहुत अच्छा है"
    assert normalise("दर्ज़ी, हूँ!") == "दर्जी हूं"


def test_to_latin_drops_the_silent_a():
    assert to_latin("सिलाई") == "silai"
    assert to_latin("बिजली") == "bijli"


CASES = [
    ("मैं सिलाई का काम करती हूं, ब्लाउज़ और सूट सिलती हूं", "7531"),
    ("मैं बिजली का काम करता हूँ, घरों में वायरिंग करता हूं", "7411"),
    ("खेती करता हूं", "9211"),
    ("मेरी मोबाइल रिपेयर की दुकान है", "7422"),
    ("राज मिस्त्री हूं, चिनाई और प्लास्टर करता हूं", "7112"),
    ("मैं टैक्सी चलाता हूं, ड्राइवर हूं", "8322"),
    ("मोटरसाइकिल और स्कूटर ठीक करता हूं गैराज में", "7231"),
    ("नल और पाइप लगाने का काम", "7126"),
    ("मैं पार्लर में मेहंदी और मेकअप करती हूं", "5142"),
    ("हलवाई हूं मिठाई बनाता हूं", "7512"),
    ("मैं लकड़ी का फर्नीचर बनाता हूं", "7115"),
    ("गाय और बकरी पालती हूं, दूध बेचती हूं", "6121"),
    ("बाल काटता हूं, सैलून है मेरा", "5141"),
    ("कंस्ट्रक्शन साइट पर बेलदारी करता हूं", "9313"),
    ("मैं दुकान पर काउंटर संभालता हूं", "5223"),
    ("ट्रैक्टर और पंप की मोटर ठीक करता हूं", "7233"),
    ("main silai ka kaam karti hoon", "7531"),
    ("main naai hoon, baal kaatta hoon", "5141"),
    ("मैं कपड़े सीती हूं घर पर", "7531"),
]


@pytest.mark.parametrize("text,code", CASES)
def test_finds_the_occupation(index, text, code):
    top = index.search(text)
    assert top[0].code == code and top[0].score >= THRESHOLD


@pytest.mark.parametrize(
    "text",
    [
        "मैं कुछ नहीं करता, घर पर रहता हूं",
        "आज मौसम बहुत अच्छा है",
        "मैं काम करता हूं",
        "मैंने नई नौकरी शुरू की है",  # नई (new) is romanised "nai", like नाई (barber)
        "",
    ],
)
def test_no_occupation_stays_below_threshold(index, text):
    top = index.search(text)
    assert not top or top[0].score < THRESHOLD


def test_mixed_story_offers_both_occupations(index):
    codes = {c.code for c in index.search("खेती करता हूं और भैंस का दूध बेचता हूं")}
    assert codes == {"9211", "6121"}


def test_cosine_is_rescaled_from_the_e5_band():
    a = np.array([1.0, 0.0], dtype=np.float32)
    occ = [Occupation("1", "x", "क", ("zz",), a), Occupation("2", "y", "ख", ("yy",), -a)]
    top = NcoIndex(occ).search("कुछ और", query_vec=a)
    assert top[0].code == "1" and top[0].cosine == 1.0 and top[1].cosine == 0.0


OTHER_LANGUAGES = [
    ("I stitch clothes, I make blouses and suits for women in my village", "7531"),
    ("I repair motorcycles and scooters at a small garage", "7231"),
    ("I repair water motors and pumps", "7233"),
    ("I work on other people's farms, cutting crops", "9211"),
    ("I do electrical wiring in houses", "7411"),
    ("I drive an auto rickshaw", "8322"),
    ("मी कपडे शिवते, ब्लाउज आणि ड्रेस बनवते", "7531"),
    ("मी गवंडी काम करतो, विटा लावतो", "7112"),
    ("मी शेतात मजुरी करतो", "9211"),
    ("माझ्याकडे दोन म्हशी आहेत, दूध विकतो", "6121"),
    ("मी मोबाईल दुरुस्ती करतो", "7422"),
    ("मी सुतार आहे, फर्निचर बनवतो", "7115"),
]


@pytest.mark.parametrize("story,code", OTHER_LANGUAGES)
def test_english_and_marathi_stories(index, story, code):
    top = index.search(story, None, 2)
    assert top[0].code == code and top[0].score >= THRESHOLD


@pytest.mark.parametrize(
    "story", ["I am studying in college", "मी कॉलेजमध्ये शिकतो", "आज हवामान चांगलं आहे"]
)
def test_english_and_marathi_small_talk_is_not_an_occupation(index, story):
    assert index.search(story, None, 2)[0].score < THRESHOLD
