"""Voice prompts for the IVR in Hindi, English and Marathi. Text is sent to Sarvam Bulbul v3.

P13, P15 and P21 contain {placeholders} and are rendered during the call.
Have a native speaker check every line before the demo.
"""

PROMPTS: dict[str, dict[str, str]] = {
    "hi-IN": {
        "P01": (
            "नमस्ते जी! यह हुनरवाणी की ओर से कॉल है। हम आपके काम और ट्रेनिंग के बारे में "
            "बात करना चाहते हैं। आगे बढ़ने के लिए कृपया 1 दबाइए।"
        ),
        "P02": (
            "क्या आप हमें सुन पा रहे हैं? बात करने के लिए 1 दबाइए। अगर आपने हमें कॉल नहीं किया था, तो 9 दबाइए।"
        ),
        "P03": (
            "क्या अभी बात करने का समय है? इसमें लगभग तीन मिनट लगेंगे। हाँ, तो 1 दबाइए। "
            "बाद में बात करनी हो, तो 2 दबाइए।"
        ),
        "P04": "कोई बात नहीं। हम आपको कल फिर कॉल करेंगे। धन्यवाद।",
        "P05": "हिंदी के लिए 1 दबाइए।",
        "P06": (
            "आपको सही ट्रेनिंग और काम बताने के लिए, हम आपकी पढ़ाई, काम और आने-जाने के बारे में "
            "पूछेंगे। यह कॉल रिकॉर्ड होगी। आप कभी भी 9 दबाकर अपनी सारी जानकारी मिटा सकते हैं। "
            "अगर आप सहमत हैं, तो 1 दबाइए। नहीं, तो 2 दबाइए।"
        ),
        "P07": (
            "क्या हम आपकी जानकारी, सिर्फ़ आपकी मदद के लिए, ट्रेनिंग सेंटर या बैंक को दे सकते हैं? "
            "हाँ, तो 1 दबाइए। नहीं, तो 2 दबाइए।"
        ),
        "P08": (
            "क्या आपकी बातचीत, आपका नाम हटाकर, इस सेवा को बेहतर बनाने में इस्तेमाल की जा सकती है? "
            "हाँ, तो 1 दबाइए। नहीं, तो 2 दबाइए।"
        ),
        "P09": (
            "आपने कहाँ तक पढ़ाई की है? स्कूल नहीं गए, तो 1 दबाइए। पाँचवीं तक, 2। आठवीं तक, 3। "
            "दसवीं पास, 4। बारहवीं पास, 5। आई टी आई या डिप्लोमा, 6। ग्रेजुएट, 7।"
        ),
        "P10": (
            "ट्रेनिंग के लिए आप कितनी दूर जा सकते हैं? सिर्फ़ अपने गाँव में, तो 1 दबाइए। "
            "दस किलोमीटर तक, 2। तीस किलोमीटर तक, 3। ज़िला मुख्यालय तक, 4। "
            "हॉस्टल में रहकर भी सीख सकते हैं, तो 5।"
        ),
        "P11": (
            "आप आगे क्या करना चाहते हैं? किसी के यहाँ पक्की नौकरी, तो 1 दबाइए। "
            "अपना खुद का काम, तो 2 दबाइए। अभी पता नहीं, तो 3 दबाइए।"
        ),
        "P12": (
            "अब अपने काम के बारे में बताइए। आजकल आप क्या काम करते हैं, और क्या-क्या करना जानते हैं? "
            "बीप के बाद अपने शब्दों में बोलिए। बोलने के बाद हैश का बटन दबाइए।"
        ),
        "P13": (
            "हमारी समझ से, आप {occupation_1} का काम करते हैं। अगर यह सही है, तो 1 दबाइए। "
            "अगर आप {occupation_2} का काम करते हैं, तो 2 दबाइए। "
            "अगर दोनों में से कोई नहीं, तो 3 दबाइए।"
        ),
        "P14": (
            "कृपया बताइए, आपका काम इनमें से किसके सबसे क़रीब है? खेती का काम, तो 1 दबाइए। "
            "सिलाई, 2। बिजली का काम, 3। राजमिस्त्री या चिनाई, 4। "
            "मोबाइल या बिजली का सामान ठीक करना, 5।"
        ),
        "P15": (
            "धन्यवाद जी। हमने आपकी जानकारी लिख ली है: {education}, और काम: {occupation}। "
            "आपके लिए सही ट्रेनिंग और काम ढूँढ़कर, हम आपको जल्दी फिर कॉल करेंगे। "
            "ध्यान रखिए, हुनरवाणी कभी पैसे या ओटीपी नहीं माँगता। आपका दिन शुभ हो।"
        ),
        "P16": "माफ़ कीजिए, हमें आपका जवाब नहीं मिला। कृपया फिर से सुनिए।",
        "P17": "धन्यवाद। एक पल रुकिए, हम आपकी बात समझ रहे हैं।",
        "P18": "आपकी सारी जानकारी मिटा दी गई है। अब हम आपको कॉल नहीं करेंगे। धन्यवाद।",
        "P19": ("ठीक है। हमारे एक अधिकारी जल्दी ही आपसे बात करेंगे। तब तक, कृपया सवालों के जवाब देते रहिए।"),
        "P20": (
            "धन्यवाद जी। आपके लिए सही ट्रेनिंग और काम ढूँढ़कर, हम आपको जल्दी फिर कॉल करेंगे। "
            "ध्यान रखिए, हुनरवाणी कभी पैसे या ओटीपी नहीं माँगता।"
        ),
        "P21": "आपने बताया: {heard}।",
        "P22": "माफ़ कीजिए, हमें आपकी आवाज़ साफ़ सुनाई नहीं दी।",
        "P23": (
            "कृपया बीप के बाद अपना काम थोड़ा और विस्तार से बताइए। जैसे, आप क्या बनाते हैं, "
            "क्या ठीक करते हैं, या कहाँ काम करते हैं। बोलने के बाद हैश का बटन दबाइए।"
        ),
        "P24": "माफ़ कीजिए, हम आपका काम ठीक से समझ नहीं पाए।",
    },
    "en-IN": {
        "P01": (
            "Hello! This is a call from HunarVaani. We would like to talk to you about your work "
            "and training. To continue, please press 1."
        ),
        "P02": "Can you hear us? To talk, press 1. If you did not call us, press 9.",
        "P03": (
            "Is this a good time to talk? It will take about three minutes. If yes, press 1. "
            "To talk later, press 2."
        ),
        "P04": "No problem. We will call you again tomorrow. Thank you.",
        "P05": "For English, press 2.",
        "P06": (
            "To suggest the right training and work for you, we will ask about your education, "
            "your work, and how far you can travel. This call will be recorded. You can press 9 "
            "at any time to delete all your information. If you agree, press 1. If not, press 2."
        ),
        "P07": (
            "May we share your information with a training centre or a bank, only to help you? "
            "If yes, press 1. If not, press 2."
        ),
        "P08": (
            "May we use your conversation, with your name removed, to improve this service? "
            "If yes, press 1. If not, press 2."
        ),
        "P09": (
            "How far have you studied? If you did not go to school, press 1. Up to fifth class, 2. "
            "Up to eighth class, 3. Tenth pass, 4. Twelfth pass, 5. ITI or diploma, 6. "
            "Graduate, 7."
        ),
        "P10": (
            "How far can you travel for training? Only within your village, press 1. "
            "Up to ten kilometres, 2. Up to thirty kilometres, 3. "
            "Up to the district headquarters, 4. If you can stay in a hostel, 5."
        ),
        "P11": (
            "What would you like to do next? A regular job with an employer, press 1. "
            "Your own work or business, press 2. If you are not sure yet, press 3."
        ),
        "P12": (
            "Now please tell us about your work. What work do you do these days, and what else "
            "can you do? Speak after the beep, in your own words. When you finish, press the "
            "hash key."
        ),
        "P13": (
            "We understood that you work as {occupation_1}. If that is right, press 1. "
            "If you work as {occupation_2}, press 2. If neither, press 3."
        ),
        "P14": (
            "Please tell us which of these is closest to your work. Farming, press 1. "
            "Tailoring, 2. Electrical work, 3. Masonry, 4. Mobile or electronics repair, 5."
        ),
        "P15": (
            "Thank you. We have noted: {education}, and your work: {occupation}. "
            "We will find the right training and work for you and call you again soon. "
            "Please remember, HunarVaani never asks for money or an OTP. Have a good day."
        ),
        "P16": "Sorry, we did not get your answer. Please listen again.",
        "P17": "Thank you. Please wait a moment while we understand your answer.",
        "P18": "All your information has been deleted. We will not call you again. Thank you.",
        "P19": (
            "Okay. One of our officers will speak with you soon. Until then, please continue "
            "answering the questions."
        ),
        "P20": (
            "Thank you. We will find the right training and work for you and call you again soon. "
            "Please remember, HunarVaani never asks for money or an OTP."
        ),
        "P21": "You said: {heard}.",
        "P22": "Sorry, we could not hear you clearly.",
        "P23": (
            "Please tell us about your work in a little more detail after the beep. For example, "
            "what you make, what you repair, or where you work. When you finish, press the "
            "hash key."
        ),
        "P24": "Sorry, we could not understand your work clearly.",
    },
    "mr-IN": {
        "P01": (
            "नमस्कार! हा हुनरवाणीकडून कॉल आहे. आम्हाला तुमच्या कामाबद्दल आणि प्रशिक्षणाबद्दल "
            "बोलायचं आहे. पुढे जाण्यासाठी कृपया 1 दाबा."
        ),
        "P02": (
            "तुम्हाला आमचा आवाज ऐकू येतोय का? बोलण्यासाठी 1 दाबा. तुम्ही आम्हाला कॉल केला नसेल, तर 9 दाबा."
        ),
        "P03": (
            "आत्ता बोलायला वेळ आहे का? यासाठी साधारण तीन मिनिटं लागतील. हो असल्यास 1 दाबा. "
            "नंतर बोलायचं असल्यास 2 दाबा."
        ),
        "P04": "काही हरकत नाही. आम्ही तुम्हाला उद्या पुन्हा कॉल करू. धन्यवाद.",
        "P05": "मराठीसाठी 3 दाबा.",
        "P06": (
            "तुमच्यासाठी योग्य प्रशिक्षण आणि काम सुचवण्यासाठी, आम्ही तुमचं शिक्षण, काम आणि "
            "तुम्ही किती लांब जाऊ शकता याबद्दल विचारू. हा कॉल रेकॉर्ड होईल. कधीही 9 दाबून "
            "तुम्ही तुमची सगळी माहिती पुसू शकता. तुम्ही सहमत असाल, तर 1 दाबा. नसाल, तर 2 दाबा."
        ),
        "P07": (
            "फक्त तुमच्या मदतीसाठी, आम्ही तुमची माहिती प्रशिक्षण केंद्र किंवा बँकेला देऊ शकतो का? "
            "हो असल्यास 1 दाबा. नाही असल्यास 2 दाबा."
        ),
        "P08": (
            "तुमचं नाव काढून, तुमचं बोलणं ही सेवा सुधारण्यासाठी वापरू शकतो का? "
            "हो असल्यास 1 दाबा. नाही असल्यास 2 दाबा."
        ),
        "P09": (
            "तुमचं शिक्षण किती झालं आहे? शाळेत गेला नसाल, तर 1 दाबा. पाचवीपर्यंत, 2. "
            "आठवीपर्यंत, 3. दहावी पास, 4. बारावी पास, 5. आय टी आय किंवा डिप्लोमा, 6. पदवीधर, 7."
        ),
        "P10": (
            "प्रशिक्षणासाठी तुम्ही किती लांब जाऊ शकता? फक्त गावातच, तर 1 दाबा. "
            "दहा किलोमीटरपर्यंत, 2. तीस किलोमीटरपर्यंत, 3. जिल्ह्याच्या ठिकाणापर्यंत, 4. "
            "वसतिगृहात राहून शिकू शकत असाल, तर 5."
        ),
        "P11": (
            "पुढे तुम्हाला काय करायला आवडेल? कुठेतरी पक्की नोकरी, तर 1 दाबा. "
            "स्वतःचा व्यवसाय, तर 2 दाबा. अजून ठरलं नसेल, तर 3 दाबा."
        ),
        "P12": (
            "आता तुमच्या कामाबद्दल सांगा. सध्या तुम्ही कोणतं काम करता, आणि अजून काय काय "
            "करता येतं? बीपनंतर तुमच्या शब्दांत बोला. बोलून झाल्यावर हॅशचं बटण दाबा."
        ),
        "P13": (
            "आम्हाला समजलं की तुम्ही {occupation_1} म्हणून काम करता. हे बरोबर असेल, तर 1 दाबा. "
            "तुम्ही {occupation_2} म्हणून काम करत असाल, तर 2 दाबा. "
            "दोन्हीपैकी काहीच नसेल, तर 3 दाबा."
        ),
        "P14": (
            "कृपया सांगा, तुमचं काम यापैकी कशाच्या सगळ्यात जवळ आहे? शेती, तर 1 दाबा. "
            "शिवणकाम, 2. वीजकाम, 3. गवंडीकाम, 4. मोबाईल किंवा इलेक्ट्रॉनिक दुरुस्ती, 5."
        ),
        "P15": (
            "धन्यवाद. आम्ही तुमची माहिती नोंदवली आहे: {education}, आणि काम: {occupation}. "
            "तुमच्यासाठी योग्य प्रशिक्षण आणि काम शोधून, आम्ही तुम्हाला लवकरच पुन्हा कॉल करू. "
            "लक्षात ठेवा, हुनरवाणी कधीही पैसे किंवा ओटीपी मागत नाही. तुमचा दिवस शुभ जावो."
        ),
        "P16": "माफ करा, तुमचं उत्तर मिळालं नाही. कृपया पुन्हा ऐका.",
        "P17": "धन्यवाद. एक क्षण थांबा, आम्ही तुमचं बोलणं समजून घेत आहोत.",
        "P18": "तुमची सगळी माहिती पुसून टाकली आहे. आता आम्ही तुम्हाला कॉल करणार नाही. धन्यवाद.",
        "P19": ("ठीक आहे. आमचे एक अधिकारी लवकरच तुमच्याशी बोलतील. तोपर्यंत, कृपया प्रश्नांची उत्तरं देत राहा."),
        "P20": (
            "धन्यवाद. तुमच्यासाठी योग्य प्रशिक्षण आणि काम शोधून, आम्ही तुम्हाला लवकरच पुन्हा कॉल "
            "करू. लक्षात ठेवा, हुनरवाणी कधीही पैसे किंवा ओटीपी मागत नाही."
        ),
        "P21": "तुम्ही सांगितलं: {heard}.",
        "P22": "माफ करा, तुमचा आवाज स्पष्ट ऐकू आला नाही.",
        "P23": (
            "कृपया बीपनंतर तुमच्या कामाबद्दल थोडं अजून सविस्तर सांगा. उदाहरणार्थ, तुम्ही काय "
            "बनवता, काय दुरुस्त करता, किंवा कुठे काम करता. बोलून झाल्यावर हॅशचं बटण दाबा."
        ),
        "P24": "माफ करा, आम्हाला तुमचं काम नीट समजलं नाही.",
    },
}

# The language menu (P05) plays one line per language; each language keeps its own key.
LANGUAGE_KEYS = {"1": "hi-IN", "2": "en-IN", "3": "mr-IN"}

DYNAMIC = {"P13", "P15", "P21"}


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
