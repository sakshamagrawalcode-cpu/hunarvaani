"""Voice prompts for the IVR in Hindi, English and Marathi. Text is sent to Sarvam Bulbul v3.

P13 and P15 contain {placeholders} and are rendered during the call.
Have a native speaker check every line before the demo.
"""

PROMPTS: dict[str, dict[str, str]] = {
    "hi-IN": {
        "P01": "नमस्ते, हुनरवाणी से कॉल है। बात करने के लिए 1 दबाइए।",
        "P02": "अगर आपने कॉल नहीं किया था, तो 9 दबाइए।",
        "P03": "क्या अभी बात करना ठीक है? हाँ के लिए 1, बाद में के लिए 2 दबाइए।",
        "P04": "ठीक है, हम आपको कल फिर कॉल करेंगे। धन्यवाद।",
        "P05": "हिंदी के लिए 1 दबाइए।",
        "P06": (
            "हम आपकी पढ़ाई, काम और जगह के बारे में पूछेंगे, ताकि सही ट्रेनिंग और काम बता सकें। "
            "कॉल रिकॉर्ड होगी। कभी भी 9 दबाकर अपनी जानकारी मिटा सकते हैं। "
            "सहमत हैं तो 1, नहीं तो 2 दबाइए।"
        ),
        "P07": (
            "क्या हम आपकी जानकारी ट्रेनिंग सेंटर या बैंक से, सिर्फ़ आपकी मदद के लिए, साझा कर सकते हैं? "
            "हाँ के लिए 1, नहीं के लिए 2।"
        ),
        "P08": (
            "क्या आपकी बातचीत, नाम हटाकर, इस सेवा को बेहतर बनाने में इस्तेमाल हो सकती है? "
            "हाँ के लिए 1, नहीं के लिए 2।"
        ),
        "P09": (
            "आपने कहाँ तक पढ़ाई की है? कभी नहीं पढ़े तो 1, पाँचवीं तक 2, आठवीं तक 3, दसवीं 4, "
            "बारहवीं 5, आईटीआई या डिप्लोमा 6, ग्रेजुएट 7।"
        ),
        "P10": (
            "ट्रेनिंग के लिए कितनी दूर जा सकते हैं? गाँव में ही 1, दस किलोमीटर तक 2, "
            "तीस किलोमीटर तक 3, ज़िला मुख्यालय 4, हॉस्टल में रह सकते हैं तो 5।"
        ),
        "P11": "आपको क्या पसंद है? पक्की नौकरी के लिए 1, अपना काम के लिए 2, पता नहीं तो 3।",
        "P12": "आजकल आप क्या काम करते हैं? बीप के बाद अपने शब्दों में बताइए। पूरा होने पर हैश दबाइए।",
        "P13": (
            "क्या आप {occupation_1} का काम करते हैं? हाँ के लिए 1। "
            "अगर {occupation_2}, तो 2। दोनों नहीं, तो 3।"
        ),
        "P14": (
            "कौन सा काम सबसे क़रीब है? खेती 1, सिलाई 2, बिजली का काम 3, मिस्त्री या चिनाई 4, "
            "मोबाइल या बिजली का सामान ठीक करना 5।"
        ),
        "P15": (
            "धन्यवाद। हमने लिखा है: {education}, {occupation}। "
            "आगे की जानकारी के लिए हम आपको फिर कॉल करेंगे। "
            "हुनरवाणी कभी पैसे या ओटीपी नहीं माँगता।"
        ),
        "P16": "जवाब नहीं मिला। फिर से सुनिए।",
        "P17": "एक पल रुकिए।",
        "P18": "आपकी जानकारी मिटा दी गई है। अब हम कॉल नहीं करेंगे। धन्यवाद।",
        "P19": "ठीक है, एक अधिकारी आपसे जल्दी बात करेंगे।",
        "P20": (
            "धन्यवाद। आगे की जानकारी के लिए हम आपको फिर कॉल करेंगे। हुनरवाणी कभी पैसे या ओटीपी नहीं माँगता।"
        ),
    },
    "en-IN": {
        "P01": "Hello, this is HunarVaani calling. Press 1 to talk.",
        "P02": "If you did not call us, press 9.",
        "P03": "Is this a good time to talk? Press 1 for yes, or 2 to talk later.",
        "P04": "Okay, we will call you again tomorrow. Thank you.",
        "P05": "For English, press 2.",
        "P06": (
            "We will ask about your education, work and location, so we can suggest the right "
            "training and work. This call will be recorded. You can press 9 at any time to delete "
            "your information. Press 1 if you agree, or 2 if you do not."
        ),
        "P07": (
            "May we share your information with a training centre or a bank, only to help you? "
            "Press 1 for yes, 2 for no."
        ),
        "P08": (
            "May your conversation, with your name removed, be used to improve this service? "
            "Press 1 for yes, 2 for no."
        ),
        "P09": (
            "How far have you studied? Never went to school, press 1. Up to fifth class, 2. "
            "Up to eighth, 3. Tenth, 4. Twelfth, 5. ITI or diploma, 6. Graduate, 7."
        ),
        "P10": (
            "How far can you travel for training? Only in your village, press 1. "
            "Up to ten kilometres, 2. Up to thirty kilometres, 3. The district headquarters, 4. "
            "If you can stay in a hostel, 5."
        ),
        "P11": (
            "What do you prefer? A regular job, press 1. Your own work, press 2. Not sure, press 3."
        ),
        "P12": (
            "What work do you do these days? After the beep, tell us in your own words. "
            "Press hash when you are done."
        ),
        "P13": (
            "Is your work {occupation_1}? Press 1 for yes. If it is {occupation_2}, press 2. "
            "If neither, press 3."
        ),
        "P14": (
            "Which work is closest to yours? Farming, 1. Tailoring, 2. Electrical work, 3. "
            "Masonry, 4. Mobile or electronics repair, 5."
        ),
        "P15": (
            "Thank you. We have noted: {education}, {occupation}. "
            "We will call you again with more information. "
            "HunarVaani never asks for money or an OTP."
        ),
        "P16": "We did not get your answer. Please listen again.",
        "P17": "One moment, please.",
        "P18": "Your information has been deleted. We will not call you again. Thank you.",
        "P19": "Okay, an officer will speak with you soon.",
        "P20": (
            "Thank you. We will call you again with more information. "
            "HunarVaani never asks for money or an OTP."
        ),
    },
    "mr-IN": {
        "P01": "नमस्कार, हुनरवाणीकडून कॉल आहे. बोलण्यासाठी 1 दाबा.",
        "P02": "तुम्ही कॉल केला नसेल, तर 9 दाबा.",
        "P03": "आत्ता बोलणं ठीक आहे का? हो असल्यास 1, नंतर बोलायचं असल्यास 2 दाबा.",
        "P04": "ठीक आहे, आम्ही तुम्हाला उद्या पुन्हा कॉल करू. धन्यवाद.",
        "P05": "मराठीसाठी 3 दाबा.",
        "P06": (
            "योग्य प्रशिक्षण आणि काम सुचवण्यासाठी आम्ही तुमचं शिक्षण, काम आणि ठिकाण याबद्दल विचारू. "
            "हा कॉल रेकॉर्ड होईल. कधीही 9 दाबून तुम्ही तुमची माहिती पुसू शकता. "
            "मान्य असल्यास 1, नसल्यास 2 दाबा."
        ),
        "P07": (
            "फक्त तुमच्या मदतीसाठी, आम्ही तुमची माहिती प्रशिक्षण केंद्र किंवा बँकेला देऊ शकतो का? "
            "हो साठी 1, नाही साठी 2."
        ),
        "P08": ("तुमचं नाव काढून, तुमचं बोलणं ही सेवा सुधारण्यासाठी वापरू शकतो का? हो साठी 1, नाही साठी 2."),
        "P09": (
            "तुमचं शिक्षण किती झालं आहे? कधीच शाळेत गेला नसाल तर 1, पाचवीपर्यंत 2, आठवीपर्यंत 3, "
            "दहावी 4, बारावी 5, आयटीआय किंवा डिप्लोमा 6, पदवीधर 7."
        ),
        "P10": (
            "प्रशिक्षणासाठी तुम्ही किती लांब जाऊ शकता? फक्त गावातच 1, दहा किलोमीटरपर्यंत 2, "
            "तीस किलोमीटरपर्यंत 3, जिल्ह्याचं ठिकाण 4, वसतिगृहात राहू शकत असाल तर 5."
        ),
        "P11": "तुम्हाला काय आवडेल? पक्की नोकरी 1, स्वतःचा व्यवसाय 2, माहीत नाही तर 3.",
        "P12": "सध्या तुम्ही कोणतं काम करता? बीपनंतर तुमच्या शब्दांत सांगा. झाल्यावर हॅश दाबा.",
        "P13": (
            "तुम्ही {occupation_1} म्हणून काम करता का? हो असल्यास 1. "
            "{occupation_2} म्हणून काम करत असाल, तर 2. दोन्ही नाही, तर 3."
        ),
        "P14": (
            "कोणतं काम तुमच्या कामाच्या सगळ्यात जवळ आहे? शेती 1, शिवणकाम 2, वीजकाम 3, "
            "गवंडीकाम 4, मोबाईल किंवा इलेक्ट्रॉनिक दुरुस्ती 5."
        ),
        "P15": (
            "धन्यवाद. आम्ही नोंद केली आहे: {education}, {occupation}. "
            "पुढील माहितीसाठी आम्ही तुम्हाला पुन्हा कॉल करू. "
            "हुनरवाणी कधीही पैसे किंवा ओटीपी मागत नाही."
        ),
        "P16": "उत्तर मिळालं नाही. पुन्हा ऐका.",
        "P17": "एक क्षण थांबा.",
        "P18": "तुमची माहिती पुसून टाकली आहे. आता आम्ही कॉल करणार नाही. धन्यवाद.",
        "P19": "ठीक आहे, एक अधिकारी लवकरच तुमच्याशी बोलतील.",
        "P20": (
            "धन्यवाद. पुढील माहितीसाठी आम्ही तुम्हाला पुन्हा कॉल करू. "
            "हुनरवाणी कधीही पैसे किंवा ओटीपी मागत नाही."
        ),
    },
}

# The language menu (P05) plays one line per language; each language keeps its own key.
LANGUAGE_KEYS = {"1": "hi-IN", "2": "en-IN", "3": "mr-IN"}

DYNAMIC = {"P13", "P15"}


def prerendered_ids(language: str = "hi-IN") -> list[str]:
    return [pid for pid in PROMPTS[language] if pid not in DYNAMIC]


def fill(language: str, prompt_id: str, **values: str) -> str:
    return PROMPTS[language][prompt_id].format(**values)


def audio_dir_name(language: str) -> str:
    return language.split("-")[0].lower()


def in_language(prompt_id: str, language: str) -> str:
    """A prompt id pinned to one language, e.g. "P05@en-IN" for the language menu."""
    return f"{prompt_id}@{language}"


def split_language(prompt_id: str) -> tuple[str, str | None]:
    pid, _, language = prompt_id.partition("@")
    return pid, language or None


def local_title(language: str, title_en: str, title_hi: str, title_mr: str = "") -> str:
    """The occupation name to speak in the caller's language."""
    if language == "en-IN":
        return title_en.lower()
    if language == "mr-IN" and title_mr:
        return title_mr
    return title_hi
