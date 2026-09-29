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


# Occupations added in Step 11d (common rural work and traditional crafts)
MORE_OCCUPATIONS = [
    ("मैं अपने खेत में सब्ज़ी उगाता हूं, टमाटर और भिंडी", "6111"),
    ("मैं माली हूं, नर्सरी में पौधे लगाता हूं", "6113"),
    ("मैं मुर्गी पालन करती हूं, अंडे बेचती हूं", "6122"),
    ("मैं तालाब में मछली पालन करता हूं", "6222"),
    ("जंगल से तेंदू पत्ता और महुआ इकट्ठा करते हैं", "6210"),
    ("मैं हथकरघा पर साड़ी बुनता हूं, बुनकर हूं", "7318"),
    ("मैं मोची हूं, जूते और चप्पल ठीक करता हूं", "7536"),
    ("चमड़े का काम करता हूं, खाल साफ करते हैं", "7535"),
    ("मैं कुम्हार हूं, मिट्टी के बर्तन और मटके बनाता हूं", "7314"),
    ("बांस की टोकरी और चटाई बनाते हैं", "7317"),
    ("मैं साड़ियों पर कढ़ाई और ज़री का काम करती हूं", "7533"),
    ("मैं वेल्डिंग करता हूं, गैस वेल्डिंग", "7212"),
    ("लोहे का गेट और ग्रिल बनाता हूं", "7214"),
    ("मैं लोहार हूं, खेती के औज़ार बनाता हूं", "7221"),
    ("फैक्ट्री में लेथ मशीन चलाता हूं, फिटर हूं", "7223"),
    ("घरों की पुताई और पेंटर का काम करता हूं", "7131"),
    ("मैं टाइल और मार्बल लगाता हूं", "7122"),
    ("एसी और फ्रिज ठीक करता हूं", "7127"),
    ("टीवी रिपेयर करता हूं", "7421"),
    ("सोलर पैनल लगाता हूं और मोटर वाइंडिंग करता हूं", "7412"),
    ("मैं ढाबे पर खाना बनाता हूं, रसोइया हूं", "5120"),
    ("होटल में वेटर हूं", "5131"),
    ("ऑफिस में सफाई और हाउसकीपिंग करती हूं", "9112"),
    ("मैं नगर पालिका में सफाई कर्मचारी हूं", "9613"),
    ("लोगों के घर में बर्तन धोने और घरेलू काम करती हूं", "9111"),
    ("आंगनवाड़ी में बच्चों की देखभाल करती हूं", "5311"),
    ("अस्पताल में मरीजों की देखभाल करता हूं, वार्ड बॉय हूं", "5321"),
    ("मैं गांव में आशा दीदी हूं", "3253"),
    ("मैं सिक्योरिटी गार्ड हूं, रात में ड्यूटी करता हूं", "5414"),
    ("मैं डिलीवरी बॉय हूं, पार्सल पहुंचाता हूं", "9621"),
    ("मैं ट्रक ड्राइवर हूं", "8332"),
    ("मैं ट्रैक्टर चलाता हूं खेतों में", "8341"),
    ("जेसीबी चलाता हूं", "8342"),
    ("कंप्यूटर पर डाटा एंट्री करती हूं", "4132"),
    ("कॉल सेंटर में काम करती हूं, कस्टमर केयर", "4222"),
    ("ठेले पर सब्ज़ी बेचता हूं", "5211"),
    ("मेरी किराने की दुकान है", "5221"),
    ("मॉल में कैशियर हूं, बिलिंग करती हूं", "5230"),
    ("मनरेगा में सड़क का काम करता हूं", "9312"),
    ("फैक्ट्री में पैकिंग का काम करती हूं", "9329"),
    ("मंडी में हमाल हूं, माल उठाता हूं", "9333"),
    ("मैं सुनार हूं, गहने बनाता हूं", "7313"),
    ("अचार और पापड़ बनाकर बेचती हूं", "7514"),
    ("मैं ट्रैक्टर रिपेयर करता हूं", "7233"),
    ("I make shoes and repair chappals, I am a cobbler", "7536"),
    ("I work as a security guard in a building", "5414"),
    ("I am a delivery boy for Swiggy", "9621"),
    ("I weave sarees on a handloom", "7318"),
    ("I cook food at a dhaba", "5120"),
    ("मी चांभार आहे, चप्पल शिवतो", "7536"),
    ("मी कुंभार आहे, मातीची भांडी बनवतो", "7314"),
    ("मी घरकाम करते, धुणीभांडी करते", "9111"),
    ("मी कोंबड्या पाळतो, अंडी विकतो", "6122"),
    ("मी रोजगार हमीच्या कामावर जातो, खोदकाम करतो", "9312"),
    ("मी हातगाडीवर भाजी विकतो", "5211"),
    ("मी सुरक्षा रक्षक आहे", "5414"),
    ("मी स्वयंपाकाचं काम करते, आचारी आहे", "5120"),
]

NOT_OCCUPATIONS = [
    "मेरा नाम आशा है",
    "मैं कल बाजार आया था",
    "आज मौसम अच्छा है",
    "मैं पढ़ाई करता हूँ।",
    "I am studying in college",
    "मी कॉलेजमध्ये शिकतो",
    "मेरे घर में चार लोग हैं",
    "मुझे काम चाहिए",
    "मैं अभी कुछ नहीं करता",
    "हम गाँव में रहते हैं",
]


@pytest.mark.parametrize("story,code", MORE_OCCUPATIONS)
def test_more_occupations(index, story, code):
    top = index.search(story, None, 2)
    assert top[0].code == code and top[0].score >= THRESHOLD


@pytest.mark.parametrize("story", NOT_OCCUPATIONS)
def test_names_and_small_talk_are_not_occupations(index, story):
    assert index.search(story, None, 2)[0].score < THRESHOLD


def test_work_that_is_two_occupations_offers_both(index):
    codes = {c.code for c in index.search("I do welding and gate fabrication", None, 2)}
    assert codes == {"7212", "7214"}


def test_every_occupation_has_all_three_names():
    for r in load_seed():
        assert r.title_en and r.title_hi and r.title_mr and r.aliases, r.nco_code
    codes = [r.nco_code for r in load_seed()]
    assert len(codes) == len(set(codes)) >= 59
