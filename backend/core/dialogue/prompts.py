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
            "क्या अभी बात करने का समय है? इसमें लगभग चार मिनट लगेंगे। हाँ, तो 1 दबाइए। "
            "बाद में बात करनी हो, तो 2 दबाइए।"
        ),
        "P04": "कोई बात नहीं। हम आपको कल फिर कॉल करेंगे। धन्यवाद।",
        "P05": "हिंदी के लिए 1 दबाइए।",
        "P06": (
            "आपकी बात ठीक से समझने के लिए यह कॉल रिकॉर्ड होगी। आप कभी भी 9 दबाकर अपनी सारी "
            "जानकारी मिटा सकते हैं। रिकॉर्डिंग के लिए हाँ, तो 1 दबाइए। नहीं, तो 2 दबाइए। "
            "नहीं कहने पर भी आप बटन दबाकर जवाब दे सकते हैं।"
        ),
        "P07": (
            "क्या हम आपकी जानकारी ट्रेनिंग सेंटर या बैंक को दे सकते हैं, ताकि वे आपसे "
            "संपर्क करके आपकी मदद कर सकें? हाँ, तो 1 दबाइए। नहीं, तो 2 दबाइए।"
        ),
        "P08": (
            "एक आख़िरी अनुमति। क्या हम आपकी बातचीत, आपका नाम और नंबर हटाकर, अपने कंप्यूटर "
            "सिस्टम, यानी एआई को, सिखाने के लिए इस्तेमाल कर सकते हैं? इससे यह सिस्टम लोगों "
            "की बात बेहतर समझेगा और सबको बेहतर सलाह देगा। आपके जवाब से आपको मिलने वाली मदद "
            "पर कोई असर नहीं पड़ेगा। हाँ, तो 1 दबाइए। नहीं, तो 2 दबाइए।"
        ),
        "P09": (
            "आपने कहाँ तक पढ़ाई की है? स्कूल नहीं गए, तो 1 दबाइए। पाँचवीं तक, 2। आठवीं तक, "
            "3। दसवीं पास, 4। बारहवीं पास, 5। आई टी आई या डिप्लोमा, 6। ग्रेजुएट, 7।"
        ),
        "P10": (
            "ट्रेनिंग के लिए आप रोज़ कितनी दूर जा सकते हैं? सिर्फ़ अपने गाँव में, तो 1 "
            "दबाइए। दस किलोमीटर तक, 2। तीस किलोमीटर तक, 3। ज़िला मुख्यालय तक, 4। हॉस्टल में"
            " रहकर भी सीख सकते हैं, तो 5।"
        ),
        "P11": (
            "आप आगे क्या करना चाहते हैं? किसी के यहाँ पक्की नौकरी, तो 1 दबाइए। अपना खुद का "
            "काम, तो 2 दबाइए। अभी पता नहीं, तो 3 दबाइए।"
        ),
        "P12": (
            "अब अपने काम के बारे में अपने शब्दों में बताइए। आजकल आप क्या काम करते हैं, कितने समय "
            "से करते हैं, और क्या-क्या करना जानते हैं? आप जितना ज़्यादा बताएँगे, हम उतनी सही "
            "सलाह दे पाएँगे। बीप के बाद बोलिए, और बोलने के बाद हैश का बटन दबाइए।"
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
        "P25": (
            "आपकी उम्र कितनी है? 18 साल से कम, तो 1 दबाइए। 18 से 25 साल, 2। 26 से 35 साल, "
            "3। 36 से 45 साल, 4। 46 से 60 साल, 5। 60 साल से ज़्यादा, 6।"
        ),
        "P26": ("आप महिला हैं, तो 1 दबाइए। पुरुष हैं, तो 2। अन्य, तो 3। नहीं बताना चाहते, तो 4 दबाइए।"),
        "P27": (
            "क्या आपको चलने-फिरने, देखने, सुनने या भारी काम करने में कोई दिक्कत है? कोई "
            "दिक्कत नहीं, तो 1 दबाइए। हाँ, कुछ दिक्कत है, तो 2 दबाइए।"
        ),
        "P28": (
            "अब आपके बारे में कुछ आसान सवाल। आपकी उम्र, पढ़ाई और आप कितनी दूर जा सकते हैं, "
            "इससे हम आपके लिए सही ट्रेनिंग, काम और सरकारी योजनाएँ ढूँढ़ पाएँगे। कुछ योजनाएँ"
            " ख़ास महिलाओं के लिए होती हैं, इसलिए यह भी पूछेंगे कि आप महिला हैं या पुरुष।"
        ),
        "P29": "माफ़ कीजिए, यह बटन इस सवाल के लिए नहीं है। कृपया फिर से सुनिए।",
    },
    "en-IN": {
        "P01": (
            "Hello! This is a call from HunarVaani. We would like to talk to you about your work "
            "and training. To continue, please press 1."
        ),
        "P02": "Can you hear us? To talk, press 1. If you did not call us, press 9.",
        "P03": (
            "Is this a good time to talk? It will take about four minutes. If yes, press 1. "
            "To talk later, press 2."
        ),
        "P04": "No problem. We will call you again tomorrow. Thank you.",
        "P05": "For English, press 2.",
        "P06": (
            "To understand you properly, this call will be recorded. You can press 9 at any"
            " time to delete all your information. If you agree to the recording, press 1. "
            "If not, press 2. Even if you say no, you can still answer by pressing buttons."
        ),
        "P07": (
            "May we share your information with a training centre or a bank, so that they "
            "can contact you and help you? If yes, press 1. If not, press 2."
        ),
        "P08": (
            "One last permission. May we use your conversation, without your name and "
            "number, to train our computer system, the AI that understands callers and "
            "recommends training? This helps it understand people better and give everyone "
            "better advice. Your answer does not change the help you get. If yes, press 1. "
            "If not, press 2."
        ),
        "P09": (
            "How far have you studied? If you did not go to school, press 1. Up to fifth "
            "class, 2. Up to eighth class, 3. Tenth pass, 4. Twelfth pass, 5. ITI or "
            "diploma, 6. Graduate, 7."
        ),
        "P10": (
            "How far can you travel each day for training? Only within your village, press "
            "1. Up to ten kilometres, 2. Up to thirty kilometres, 3. Up to the district "
            "headquarters, 4. If you can stay in a hostel, 5."
        ),
        "P11": (
            "What would you like to do next? A regular job with an employer, press 1. Your "
            "own work or business, press 2. If you are not sure yet, press 3."
        ),
        "P12": (
            "Now please tell us about your work, in your own words. What work do you do these "
            "days, for how long, and what else can you do? The more you tell us, the better our "
            "advice will be. Speak after the beep, and press the hash key when you finish."
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
        "P25": (
            "How old are you? Below 18 years, press 1. 18 to 25 years, 2. 26 to 35 years, "
            "3. 36 to 45 years, 4. 46 to 60 years, 5. Above 60 years, 6."
        ),
        "P26": (
            "If you are a woman, press 1. A man, 2. Other, 3. If you do not want to say, press 4."
        ),
        "P27": (
            "Do you have any difficulty walking, seeing, hearing, or doing heavy work? No "
            "difficulty, press 1. Yes, some difficulty, press 2."
        ),
        "P28": (
            "Now a few simple questions about you. Your age, education and how far you can "
            "travel help us find the right training, work and government schemes for you. "
            "Some schemes are only for women, so we will also ask whether you are a woman "
            "or a man."
        ),
        "P29": "Sorry, that key is not one of the options. Please listen again.",
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
            "आत्ता बोलायला वेळ आहे का? यासाठी साधारण चार मिनिटं लागतील. हो असल्यास 1 दाबा. "
            "नंतर बोलायचं असल्यास 2 दाबा."
        ),
        "P04": "काही हरकत नाही. आम्ही तुम्हाला उद्या पुन्हा कॉल करू. धन्यवाद.",
        "P05": "मराठीसाठी 3 दाबा.",
        "P06": (
            "तुमचं बोलणं नीट समजण्यासाठी हा कॉल रेकॉर्ड होईल. कधीही 9 दाबून तुम्ही तुमची "
            "सगळी माहिती पुसू शकता. रेकॉर्डिंगसाठी हो असल्यास 1 दाबा. नाही असल्यास 2 दाबा. "
            "नाही म्हटलं तरी तुम्ही बटण दाबून उत्तरं देऊ शकता."
        ),
        "P07": (
            "तुमची माहिती प्रशिक्षण केंद्र किंवा बँकेला देऊ का, म्हणजे ते तुमच्याशी संपर्क "
            "करून तुमची मदत करू शकतील? हो असल्यास 1 दाबा. नाही असल्यास 2 दाबा."
        ),
        "P08": (
            "शेवटची एक परवानगी. तुमचं नाव आणि नंबर काढून, तुमचं बोलणं आमच्या कॉम्प्युटर "
            "सिस्टमला, म्हणजे एआयला, शिकवण्यासाठी वापरू का? यामुळे ही सिस्टम लोकांचं बोलणं "
            "जास्त चांगलं समजेल आणि सगळ्यांना जास्त चांगला सल्ला देईल. तुमच्या उत्तरामुळे "
            "तुम्हाला मिळणाऱ्या मदतीवर काही परिणाम होणार नाही. हो असल्यास 1 दाबा. नाही "
            "असल्यास 2 दाबा."
        ),
        "P09": (
            "तुमचं शिक्षण किती झालं आहे? शाळेत गेला नसाल, तर 1 दाबा. पाचवीपर्यंत, 2. "
            "आठवीपर्यंत, 3. दहावी पास, 4. बारावी पास, 5. आय टी आय किंवा डिप्लोमा, 6. "
            "पदवीधर, 7."
        ),
        "P10": (
            "प्रशिक्षणासाठी तुम्ही रोज किती लांब जाऊ शकता? फक्त गावातच, तर 1 दाबा. दहा "
            "किलोमीटरपर्यंत, 2. तीस किलोमीटरपर्यंत, 3. जिल्ह्याच्या ठिकाणापर्यंत, 4. "
            "वसतिगृहात राहून शिकू शकत असाल, तर 5."
        ),
        "P11": (
            "पुढे तुम्हाला काय करायला आवडेल? कुठेतरी पक्की नोकरी, तर 1 दाबा. स्वतःचा "
            "व्यवसाय, तर 2 दाबा. अजून ठरलं नसेल, तर 3 दाबा."
        ),
        "P12": (
            "आता तुमच्या कामाबद्दल तुमच्या शब्दांत सांगा. सध्या तुम्ही कोणतं काम करता, किती "
            "दिवसांपासून करता, आणि अजून काय काय करता येतं? तुम्ही जितकं जास्त सांगाल, तितका "
            "आमचा सल्ला योग्य असेल. बीपनंतर बोला, आणि बोलून झाल्यावर हॅशचं बटण दाबा."
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
        "P25": (
            "तुमचं वय किती आहे? 18 वर्षांपेक्षा कमी, तर 1 दाबा. 18 ते 25 वर्षं, 2. 26 ते 35"
            " वर्षं, 3. 36 ते 45 वर्षं, 4. 46 ते 60 वर्षं, 5. 60 वर्षांपेक्षा जास्त, 6."
        ),
        "P26": ("तुम्ही महिला असाल, तर 1 दाबा. पुरुष, तर 2. इतर, तर 3. सांगायचं नसेल, तर 4 दाबा."),
        "P27": (
            "तुम्हाला चालण्यात, पाहण्यात, ऐकण्यात किंवा जड काम करण्यात काही अडचण आहे का? "
            "काही अडचण नाही, तर 1 दाबा. हो, थोडी अडचण आहे, तर 2 दाबा."
        ),
        "P28": (
            "आता तुमच्याबद्दल काही सोपे प्रश्न. तुमचं वय, शिक्षण आणि तुम्ही किती लांब जाऊ "
            "शकता, यावरून आम्ही तुमच्यासाठी योग्य प्रशिक्षण, काम आणि सरकारी योजना शोधू. "
            "काही योजना फक्त महिलांसाठी असतात, म्हणून तुम्ही महिला आहात की पुरुष, हेही "
            "विचारू."
        ),
        "P29": "माफ करा, हे बटण या प्रश्नासाठी नाही. कृपया पुन्हा ऐका.",
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
