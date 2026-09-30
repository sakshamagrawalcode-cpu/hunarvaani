"""Voice prompts for the IVR in Hindi, English and Marathi. Text is sent to Sarvam Bulbul v3.

P13, P15, P21 and P34 contain {placeholders} and are rendered during the call.
Have a native speaker check every line before the demo.
"""

PROMPTS: dict[str, dict[str, str]] = {
    "hi-IN": {
        "P01": (
            "नमस्ते! हुनरवाणी में आपका स्वागत है। हम आपके काम के हिसाब से ट्रेनिंग और रोज़गार "
            "ढूँढ़ने में मदद करते हैं। आगे बढ़ने के लिए 1 दबाइए।"
        ),
        "P02": "क्या आपको आवाज़ आ रही है? तो 1 दबाइए। आपने कॉल नहीं किया था, तो 9 दबाइए।",
        "P03": "इसमें लगभग पाँच मिनट लगेंगे। अभी बात करें, तो 1 दबाइए। बाद में, तो 2।",
        "P04": "कोई बात नहीं। हम आपको बाद में फिर कॉल करेंगे। धन्यवाद।",
        "P05": "हिंदी के लिए 1 दबाइए।",
        "P06": (
            "आपकी बात ठीक से समझने के लिए यह कॉल रिकॉर्ड होगी। ठीक है, तो 1 दबाइए। नहीं, तो 2। "
            "आप कभी भी 9 दबाकर अपनी सारी जानकारी मिटा सकते हैं।"
        ),
        "P07": (
            "क्या हम आपकी जानकारी ट्रेनिंग सेंटर या बैंक को दे सकते हैं, ताकि वे आपकी मदद करें? "
            "हाँ, तो 1 दबाइए। नहीं, तो 2।"
        ),
        "P08": (
            "क्या हम आपकी बातचीत, नाम और नंबर हटाकर, अपने कंप्यूटर सिस्टम को सिखाने में इस्तेमाल "
            "कर सकते हैं? इससे आपको मिलने वाली मदद नहीं बदलेगी। हाँ, तो 1 दबाइए। नहीं, तो 2।"
        ),
        "P09": (
            "आपने कहाँ तक पढ़ाई की है? स्कूल नहीं गए, तो 1। पाँचवीं तक, 2। आठवीं तक, 3। "
            "दसवीं, 4। बारहवीं, 5। आईटीआई या डिप्लोमा, 6। ग्रेजुएट, 7।"
        ),
        "P10": (
            "ट्रेनिंग के लिए रोज़ कितनी दूर जा सकते हैं? गाँव में ही, तो 1। दस किलोमीटर तक, 2। "
            "तीस किलोमीटर तक, 3। ज़िले के शहर तक, 4। हॉस्टल में रह सकते हैं, तो 5।"
        ),
        "P11": "आगे क्या चाहते हैं? नौकरी, तो 1 दबाइए। अपना काम, तो 2। अभी पता नहीं, तो 3।",
        "P12": (
            "अब अपने काम के बारे में बताइए: आप क्या काम करते हैं, कितने साल से, और क्या-क्या "
            "आता है। बीप के बाद बोलिए, फिर हैश दबाइए।"
        ),
        "P13": "हमारी समझ से आपका काम इनमें से एक है। {options} कोई नहीं, तो {none_key} दबाइए।",
        "P14": (
            "आपका काम किसके सबसे क़रीब है? खेती, तो 1। सिलाई, 2। बिजली का काम, 3। राजमिस्त्री, "
            "4। मोबाइल या बिजली का सामान ठीक करना, 5।"
        ),
        "P15": "धन्यवाद। हमने लिख लिया है: {education}, और काम: {occupation}।",
        "P16": "माफ़ कीजिए, जवाब नहीं मिला। फिर से सुनिए।",
        "P17": "धन्यवाद। एक पल रुकिए।",
        "P18": "आपकी सारी जानकारी मिटा दी गई है। अब हम आपको कॉल नहीं करेंगे। धन्यवाद।",
        "P19": "ठीक है, हमारे अधिकारी आपसे बात करेंगे। तब तक सवाल जारी रखते हैं।",
        "P20": "धन्यवाद। आपकी जानकारी सेव हो गई है।",
        "P21": "आपने बताया: {heard}।",
        "P22": "माफ़ कीजिए, आवाज़ साफ़ नहीं आई।",
        "P23": ("बीप के बाद अपना काम थोड़ा और बताइए, जैसे आप क्या बनाते या ठीक करते हैं। फिर हैश दबाइए।"),
        "P24": "माफ़ कीजिए, आपका काम ठीक से समझ नहीं आया।",
        "P25": (
            "आपकी उम्र कितनी है? 18 से कम, तो 1। 18 से 25, 2। 26 से 35, 3। 36 से 45, 4। "
            "46 से 60, 5। 60 से ज़्यादा, 6।"
        ),
        "P26": "आप महिला हैं, तो 1 दबाइए। पुरुष, 2। अन्य, 3। नहीं बताना चाहते, 4।",
        "P27": ("क्या चलने, देखने, सुनने या भारी काम में कोई दिक्कत है? नहीं, तो 1 दबाइए। हाँ, तो 2।"),
        "P28": "अब कुछ आसान सवाल, ताकि आपके लिए सही ट्रेनिंग और सरकारी योजना ढूँढ़ सकें।",
        "P29": "माफ़ कीजिए, यह बटन सही नहीं है। फिर से सुनिए।",
        "P30": "हम अभी भी समझ रहे हैं। कृपया लाइन पर बने रहिए।",
        "P31": "अपने इलाके का छह अंकों का पिन कोड दबाइए। याद नहीं, तो स्टार दबाइए।",
        "P32": "माफ़ कीजिए, यह पिन कोड सही नहीं लगा। छह अंक फिर से दबाइए।",
        "P33": "धन्यवाद, आपकी पसंद सेव हो गई है।",
        "P34": (
            "आपके लिए {count} रास्ते हैं। {options} जो पसंद हो, उसका नंबर दबाइए। कोई नहीं, तो {none_key}।"
        ),
        "P35": "आपने बताया:",
        "P36": "सब सही है, तो 1 दबाइए। कुछ बदलना है, तो 2।",
        "P37": (
            "क्या बदलना है? उम्र, तो 1। महिला या पुरुष, 2। पढ़ाई, 3। दूरी, 4। दिक्कत, 5। "
            "पिन कोड, 6। नौकरी या अपना काम, 7।"
        ),
        "P38": "आपका रेफ़रेंस नंबर है:",
        "P39": (
            "यह नंबर लिख लीजिए। ट्रेनिंग सेंटर या सीएससी केंद्र पर यह नंबर बताइए। साथ ले जाइए: "
            "आधार कार्ड, बैंक पासबुक, पढ़ाई का सर्टिफ़िकेट और दो फ़ोटो। जाति या आय प्रमाण पत्र हो, "
            "तो वह भी। हुनरवाणी कभी पैसे या ओटीपी नहीं माँगता। धन्यवाद!"
        ),
        "P40": "फिर से:",
    },
    "en-IN": {
        "P01": (
            "Hello, welcome to HunarVaani. We help you find training and work that fit your "
            "skills. To continue, press 1."
        ),
        "P02": "Can you hear us? Then press 1. If you did not call us, press 9.",
        "P03": "This takes about five minutes. To talk now, press 1. Later, press 2.",
        "P04": "No problem. We will call you again later. Thank you.",
        "P05": "For English, press 2.",
        "P06": (
            "This call will be recorded so we understand you properly. If that is okay, press 1. "
            "If not, press 2. You can press 9 at any time to delete all your information."
        ),
        "P07": (
            "May we share your details with a training centre or a bank, so they can help you? "
            "If yes, press 1. If not, press 2."
        ),
        "P08": (
            "May we use this conversation, without your name and number, to improve our computer "
            "system? It does not change the help you get. If yes, press 1. If not, press 2."
        ),
        "P09": (
            "How far have you studied? No school, press 1. Up to fifth class, 2. Up to eighth, 3. "
            "Tenth, 4. Twelfth, 5. ITI or diploma, 6. Graduate, 7."
        ),
        "P10": (
            "How far can you travel each day for training? Only in your village, press 1. Up to "
            "ten kilometres, 2. Up to thirty, 3. To the district town, 4. You can stay in a "
            "hostel, 5."
        ),
        "P11": "What do you want next? A job, press 1. Your own work, 2. Not sure yet, 3.",
        "P12": (
            "Now tell us about your work: what you do, for how many years, and what else you can "
            "do. Speak after the beep, then press hash."
        ),
        "P13": "We think your work is one of these. {options} If none, press {none_key}.",
        "P14": (
            "Which is closest to your work? Farming, press 1. Tailoring, 2. Electrical work, 3. "
            "Masonry, 4. Mobile or electrical repair, 5."
        ),
        "P15": "Thank you. We have noted: {education}, and work: {occupation}.",
        "P16": "Sorry, we did not get an answer. Please listen again.",
        "P17": "Thank you. One moment, please.",
        "P18": "All your information has been deleted. We will not call you again. Thank you.",
        "P19": "Okay, one of our officers will speak with you. Let us continue meanwhile.",
        "P20": "Thank you. Your details are saved.",
        "P21": "You said: {heard}.",
        "P22": "Sorry, we could not hear you clearly.",
        "P23": (
            "After the beep, tell us a little more about your work, like what you make or repair. "
            "Then press hash."
        ),
        "P24": "Sorry, we could not understand your work.",
        "P25": (
            "How old are you? Under 18, press 1. 18 to 25, 2. 26 to 35, 3. 36 to 45, 4. "
            "46 to 60, 5. Over 60, 6."
        ),
        "P26": "If you are a woman, press 1. A man, 2. Other, 3. Prefer not to say, 4.",
        "P27": (
            "Do you have any difficulty walking, seeing, hearing or doing heavy work? No, press 1. "
            "Yes, press 2."
        ),
        "P28": "Now a few simple questions, so we can find the right training and schemes for you.",
        "P29": "Sorry, that key is not an option. Please listen again.",
        "P30": "We are still working on it. Please stay on the line.",
        "P31": (
            "Please press the six-digit PIN code of your area. If you do not know it, press star."
        ),
        "P32": "Sorry, that PIN code does not look right. Please press the six digits again.",
        "P33": "Thank you, your choice is saved.",
        "P34": (
            "Here are {count} options for you. {options} Press the number of the one you like. "
            "If none, press {none_key}."
        ),
        "P35": "You told us:",
        "P36": "If all this is correct, press 1. To change something, press 2.",
        "P37": (
            "What do you want to change? Age, press 1. Woman or man, 2. Education, 3. Travel, 4. "
            "Difficulty, 5. PIN code, 6. Job or own work, 7."
        ),
        "P38": "Your reference number is:",
        "P39": (
            "Please write this number down. Tell it at a training centre or a CSC centre. Take "
            "your Aadhaar card, bank passbook, education certificate and two photos, and your "
            "caste or income certificate if you have one. HunarVaani never asks for money or an "
            "OTP. Thank you!"
        ),
        "P40": "Once more:",
    },
    "mr-IN": {
        "P01": (
            "नमस्कार! हुनरवाणीमध्ये तुमचं स्वागत आहे. तुमच्या कामानुसार प्रशिक्षण आणि रोजगार "
            "शोधायला आम्ही मदत करतो. पुढे जाण्यासाठी 1 दाबा."
        ),
        "P02": "तुम्हाला आवाज येतोय का? तर 1 दाबा. तुम्ही कॉल केला नसेल, तर 9 दाबा.",
        "P03": "याला सुमारे पाच मिनिटं लागतील. आत्ता बोलायचं असेल, तर 1 दाबा. नंतर, तर 2.",
        "P04": "काही हरकत नाही. आम्ही तुम्हाला नंतर पुन्हा कॉल करू. धन्यवाद.",
        "P05": "मराठीसाठी 3 दाबा.",
        "P06": (
            "तुमचं बोलणं नीट समजण्यासाठी हा कॉल रेकॉर्ड होईल. चालेल, तर 1 दाबा. नाही, तर 2. "
            "तुम्ही कधीही 9 दाबून तुमची सगळी माहिती पुसू शकता."
        ),
        "P07": (
            "तुमची माहिती प्रशिक्षण केंद्र किंवा बँकेला देऊ का, म्हणजे ते तुम्हाला मदत करतील? "
            "हो, तर 1 दाबा. नाही, तर 2."
        ),
        "P08": (
            "तुमचं नाव आणि नंबर काढून, हे बोलणं आमची संगणक प्रणाली सुधारण्यासाठी वापरू का? "
            "यामुळे तुम्हाला मिळणारी मदत बदलणार नाही. हो, तर 1 दाबा. नाही, तर 2."
        ),
        "P09": (
            "तुमचं शिक्षण किती झालं आहे? शाळेत गेलो नाही, तर 1. पाचवीपर्यंत, 2. आठवीपर्यंत, 3. "
            "दहावी, 4. बारावी, 5. आयटीआय किंवा डिप्लोमा, 6. पदवीधर, 7."
        ),
        "P10": (
            "प्रशिक्षणासाठी रोज किती लांब जाऊ शकता? गावातच, तर 1. दहा किलोमीटरपर्यंत, 2. तीस "
            "किलोमीटरपर्यंत, 3. जिल्ह्याच्या शहरापर्यंत, 4. वसतिगृहात राहू शकता, तर 5."
        ),
        "P11": "पुढे काय हवं आहे? नोकरी, तर 1 दाबा. स्वतःचं काम, 2. अजून माहीत नाही, 3.",
        "P12": (
            "आता तुमच्या कामाबद्दल सांगा: तुम्ही काय काम करता, किती वर्षांपासून, आणि अजून काय "
            "येतं. बीपनंतर बोला, मग हॅश दाबा."
        ),
        "P13": "आमच्या समजुतीनुसार तुमचं काम यापैकी एक आहे. {options} यापैकी काही नसेल, तर {none_key} दाबा.",
        "P14": (
            "तुमचं काम कशाच्या सगळ्यात जवळ आहे? शेती, तर 1. शिवणकाम, 2. वीजकाम, 3. गवंडीकाम, 4. "
            "मोबाइल किंवा विजेचं सामान दुरुस्ती, 5."
        ),
        "P15": "धन्यवाद. आम्ही लिहून घेतलं आहे: {education}, आणि काम: {occupation}.",
        "P16": "माफ करा, उत्तर मिळालं नाही. पुन्हा ऐका.",
        "P17": "धन्यवाद. एक क्षण थांबा.",
        "P18": "तुमची सगळी माहिती पुसून टाकली आहे. आता आम्ही तुम्हाला कॉल करणार नाही. धन्यवाद.",
        "P19": "ठीक आहे, आमचे अधिकारी तुमच्याशी बोलतील. तोपर्यंत प्रश्न पुढे चालू ठेवू.",
        "P20": "धन्यवाद. तुमची माहिती सेव्ह झाली आहे.",
        "P21": "तुम्ही सांगितलं: {heard}.",
        "P22": "माफ करा, आवाज स्पष्ट आला नाही.",
        "P23": (
            "बीपनंतर तुमच्या कामाबद्दल थोडं अजून सांगा, जसं तुम्ही काय बनवता किंवा दुरुस्त करता. मग हॅश दाबा."
        ),
        "P24": "माफ करा, तुमचं काम नीट समजलं नाही.",
        "P25": (
            "तुमचं वय किती आहे? 18 पेक्षा कमी, तर 1. 18 ते 25, 2. 26 ते 35, 3. 36 ते 45, 4. "
            "46 ते 60, 5. 60 पेक्षा जास्त, 6."
        ),
        "P26": "तुम्ही महिला असाल, तर 1 दाबा. पुरुष, 2. इतर, 3. सांगायचं नसेल, 4.",
        "P27": ("चालणं, पाहणं, ऐकणं किंवा जड काम करण्यात काही अडचण आहे का? नाही, तर 1 दाबा. हो, तर 2."),
        "P28": "आता काही सोपे प्रश्न, म्हणजे तुमच्यासाठी योग्य प्रशिक्षण आणि सरकारी योजना शोधता येतील.",
        "P29": "माफ करा, हे बटण बरोबर नाही. पुन्हा ऐका.",
        "P30": "आम्ही अजून समजून घेत आहोत. कृपया लाईनवर थांबा.",
        "P31": "तुमच्या भागाचा सहा अंकी पिन कोड दाबा. आठवत नसेल, तर स्टार दाबा.",
        "P32": "माफ करा, हा पिन कोड बरोबर वाटत नाही. सहा अंक पुन्हा दाबा.",
        "P33": "धन्यवाद, तुमची निवड सेव्ह झाली आहे.",
        "P34": (
            "तुमच्यासाठी {count} पर्याय आहेत. {options} जो आवडेल, त्याचा नंबर दाबा. "
            "कोणताच नाही, तर {none_key}."
        ),
        "P35": "तुम्ही सांगितलं:",
        "P36": "सगळं बरोबर असेल, तर 1 दाबा. काही बदलायचं असेल, तर 2.",
        "P37": (
            "काय बदलायचं आहे? वय, तर 1. महिला किंवा पुरुष, 2. शिक्षण, 3. अंतर, 4. अडचण, 5. "
            "पिन कोड, 6. नोकरी किंवा स्वतःचं काम, 7."
        ),
        "P38": "तुमचा रेफरन्स नंबर आहे:",
        "P39": (
            "हा नंबर लिहून ठेवा. प्रशिक्षण केंद्र किंवा सीएससी केंद्रावर हा नंबर सांगा. सोबत "
            "न्या: आधार कार्ड, बँक पासबुक, शिक्षणाचं प्रमाणपत्र आणि दोन फोटो. जातीचा किंवा "
            "उत्पन्नाचा दाखला असेल, तर तोही. हुनरवाणी कधीही पैसे किंवा ओटीपी मागत नाही. धन्यवाद!"
        ),
        "P40": "पुन्हा एकदा:",
    },
}

# Short pieces joined together (no speech made during the call): the caller's saved answers in
# the review (P35 ... P36), and digits for the PIN code and the reference number.
FRAGMENTS: dict[str, dict[str, str]] = {
    "hi-IN": {
        "V_q_age_under_18": "उम्र 18 साल से कम।",
        "V_q_age_18_25": "उम्र 18 से 25 साल।",
        "V_q_age_26_35": "उम्र 26 से 35 साल।",
        "V_q_age_36_45": "उम्र 36 से 45 साल।",
        "V_q_age_46_60": "उम्र 46 से 60 साल।",
        "V_q_age_over_60": "उम्र 60 साल से ज़्यादा।",
        "V_q_gender_female": "आप महिला हैं।",
        "V_q_gender_male": "आप पुरुष हैं।",
        "V_q_gender_other": "लिंग: अन्य।",
        "V_q_gender_not_said": "लिंग नहीं बताया।",
        "V_q_education_none": "पढ़ाई: स्कूल नहीं गए।",
        "V_q_education_upto_5th": "पढ़ाई: पाँचवीं तक।",
        "V_q_education_upto_8th": "पढ़ाई: आठवीं तक।",
        "V_q_education_10th": "पढ़ाई: दसवीं।",
        "V_q_education_12th": "पढ़ाई: बारहवीं।",
        "V_q_education_iti_or_diploma": "पढ़ाई: आईटीआई या डिप्लोमा।",
        "V_q_education_graduate": "पढ़ाई: ग्रेजुएट।",
        "V_q_travel_village": "ट्रेनिंग के लिए गाँव में ही।",
        "V_q_travel_10km": "ट्रेनिंग के लिए दस किलोमीटर तक।",
        "V_q_travel_30km": "ट्रेनिंग के लिए तीस किलोमीटर तक।",
        "V_q_travel_district_hq": "ट्रेनिंग के लिए ज़िले के शहर तक।",
        "V_q_travel_hostel": "हॉस्टल में रह सकते हैं।",
        "V_q_physical_none": "कोई दिक्कत नहीं।",
        "V_q_physical_some": "कुछ दिक्कत है।",
        "V_q_lean_job": "आप नौकरी चाहते हैं।",
        "V_q_lean_own_work": "आप अपना काम चाहते हैं।",
        "V_q_lean_unsure": "आगे का अभी पता नहीं।",
        "V_pin": "पिन कोड:",
        "V_pin_none": "पिन कोड नहीं बताया।",
        "D0": "शून्य",
        "D1": "एक",
        "D2": "दो",
        "D3": "तीन",
        "D4": "चार",
        "D5": "पाँच",
        "D6": "छह",
        "D7": "सात",
        "D8": "आठ",
        "D9": "नौ",
    },
    "en-IN": {
        "V_q_age_under_18": "Age under 18.",
        "V_q_age_18_25": "Age 18 to 25.",
        "V_q_age_26_35": "Age 26 to 35.",
        "V_q_age_36_45": "Age 36 to 45.",
        "V_q_age_46_60": "Age 46 to 60.",
        "V_q_age_over_60": "Age over 60.",
        "V_q_gender_female": "A woman.",
        "V_q_gender_male": "A man.",
        "V_q_gender_other": "Gender: other.",
        "V_q_gender_not_said": "Gender not given.",
        "V_q_education_none": "Education: no school.",
        "V_q_education_upto_5th": "Education: up to fifth class.",
        "V_q_education_upto_8th": "Education: up to eighth class.",
        "V_q_education_10th": "Education: tenth.",
        "V_q_education_12th": "Education: twelfth.",
        "V_q_education_iti_or_diploma": "Education: ITI or diploma.",
        "V_q_education_graduate": "Education: graduate.",
        "V_q_travel_village": "Training only in your village.",
        "V_q_travel_10km": "Training up to ten kilometres away.",
        "V_q_travel_30km": "Training up to thirty kilometres away.",
        "V_q_travel_district_hq": "Training up to the district town.",
        "V_q_travel_hostel": "You can stay in a hostel.",
        "V_q_physical_none": "No difficulty.",
        "V_q_physical_some": "Some difficulty.",
        "V_q_lean_job": "You want a job.",
        "V_q_lean_own_work": "You want your own work.",
        "V_q_lean_unsure": "Not sure yet what you want.",
        "V_pin": "PIN code:",
        "V_pin_none": "PIN code not given.",
        "D0": "zero",
        "D1": "one",
        "D2": "two",
        "D3": "three",
        "D4": "four",
        "D5": "five",
        "D6": "six",
        "D7": "seven",
        "D8": "eight",
        "D9": "nine",
    },
    "mr-IN": {
        "V_q_age_under_18": "वय 18 पेक्षा कमी.",
        "V_q_age_18_25": "वय 18 ते 25.",
        "V_q_age_26_35": "वय 26 ते 35.",
        "V_q_age_36_45": "वय 36 ते 45.",
        "V_q_age_46_60": "वय 46 ते 60.",
        "V_q_age_over_60": "वय 60 पेक्षा जास्त.",
        "V_q_gender_female": "तुम्ही महिला आहात.",
        "V_q_gender_male": "तुम्ही पुरुष आहात.",
        "V_q_gender_other": "लिंग: इतर.",
        "V_q_gender_not_said": "लिंग सांगितलं नाही.",
        "V_q_education_none": "शिक्षण: शाळेत गेलो नाही.",
        "V_q_education_upto_5th": "शिक्षण: पाचवीपर्यंत.",
        "V_q_education_upto_8th": "शिक्षण: आठवीपर्यंत.",
        "V_q_education_10th": "शिक्षण: दहावी.",
        "V_q_education_12th": "शिक्षण: बारावी.",
        "V_q_education_iti_or_diploma": "शिक्षण: आयटीआय किंवा डिप्लोमा.",
        "V_q_education_graduate": "शिक्षण: पदवीधर.",
        "V_q_travel_village": "प्रशिक्षण गावातच.",
        "V_q_travel_10km": "प्रशिक्षण दहा किलोमीटरपर्यंत.",
        "V_q_travel_30km": "प्रशिक्षण तीस किलोमीटरपर्यंत.",
        "V_q_travel_district_hq": "प्रशिक्षण जिल्ह्याच्या शहरापर्यंत.",
        "V_q_travel_hostel": "वसतिगृहात राहू शकता.",
        "V_q_physical_none": "काही अडचण नाही.",
        "V_q_physical_some": "थोडी अडचण आहे.",
        "V_q_lean_job": "तुम्हाला नोकरी हवी आहे.",
        "V_q_lean_own_work": "तुम्हाला स्वतःचं काम हवं आहे.",
        "V_q_lean_unsure": "पुढचं अजून माहीत नाही.",
        "V_pin": "पिन कोड:",
        "V_pin_none": "पिन कोड सांगितला नाही.",
        "D0": "शून्य",
        "D1": "एक",
        "D2": "दोन",
        "D3": "तीन",
        "D4": "चार",
        "D5": "पाच",
        "D6": "सहा",
        "D7": "सात",
        "D8": "आठ",
        "D9": "नऊ",
    },
}


def text_of(language: str, prompt_id: str) -> str | None:
    """The words of a fixed prompt or a fragment, or None."""
    lang = language if language in PROMPTS else "hi-IN"
    return PROMPTS[lang].get(prompt_id) or FRAGMENTS[lang].get(prompt_id)


def prerendered_texts(language: str = "hi-IN") -> dict[str, str]:
    """Every sentence rendered once to a file: fixed prompts and fragments."""
    return {pid: PROMPTS[language][pid] for pid in prerendered_ids(language)} | FRAGMENTS[language]


# The language menu (P05) plays one line per language; each language keeps its own key.
LANGUAGE_KEYS = {"1": "hi-IN", "2": "en-IN", "3": "mr-IN"}

DYNAMIC = {"P13", "P15", "P21", "P34"}


def prerendered_ids(language: str = "hi-IN") -> list[str]:
    return [pid for pid in PROMPTS[language] if pid not in DYNAMIC]


def fill(language: str, prompt_id: str, **values: str) -> str:
    return PROMPTS[language][prompt_id].format(**values)


# one line per occupation in the read-back (P13): "For tailor, press 1."
OPTION = {
    "hi-IN": "{name} के लिए {key} दबाइए।",
    "en-IN": "For {name}, press {key}.",
    "mr-IN": "{name} साठी {key} दाबा.",
}


def readback_text(language: str, names: list[str]) -> str:
    """P13 with one option per occupation (keys 1, 2, 3) and the next key for "none of these"."""
    line = OPTION.get(language, OPTION["hi-IN"])
    options = " ".join(line.format(name=n, key=i) for i, n in enumerate(names, 1))
    return fill(language, "P13", options=options, none_key=str(len(names) + 1))


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
