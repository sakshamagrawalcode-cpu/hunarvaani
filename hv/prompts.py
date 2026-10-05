"""Everything the system says, in Hindi, Marathi and English, as short fixed pieces.

Every piece has a key; scripts/render_audio.py turns each key into audio/<lang>/<key>.wav once with
Indic Parler-TTS, so a live call only plays pre-recorded audio (fast, and no TTS on the GPU while
calls run). Dynamic parts (numbers, job titles, sectors, districts, centre types) are pieces too.
Native speakers should check the Hindi and Marathi wording before a pilot.
"""

import re
from dataclasses import dataclass

from .data import Data

LANGS = ("hi", "mr", "en")


@dataclass(frozen=True)
class Part:
    key: str  # audio file name (without .wav)
    text: str  # what is shown on the kiosk screen and logged


# key: (Hindi, Marathi, English)
T: dict[str, tuple[str, str, str]] = {
    "lang_hi": ("हिंदी के लिए 1 दबाइए।", "", ""),
    "lang_mr": ("", "मराठीसाठी 2 दाबा.", ""),
    "lang_en": ("", "", "For English, press 3."),
    "greet": ("नमस्ते! हुनरवाणी में आपका स्वागत है। हम आपके लिए सही ट्रेनिंग और काम ढूँढने में मदद करेंगे। यह सेवा मुफ़्त है।",
              "नमस्कार! हुनरवाणीमध्ये तुमचं स्वागत आहे. तुमच्यासाठी योग्य प्रशिक्षण आणि काम शोधायला आम्ही मदत करू. ही सेवा मोफत आहे.",
              "Namaste! Welcome to HunarVaani. We will help you find the right training and work. This service is free."),
    "keys_help": ("किसी भी समय: अधिकारी से बात के लिए 0, अपनी जानकारी मिटाने के लिए 9।",
                  "कधीही: अधिकाऱ्याशी बोलायला 0, तुमची माहिती पुसायला 9.",
                  "At any time: press 0 to reach an officer, 9 to delete your information."),
    "consent": ("आपकी बातें रिकॉर्ड होंगी और योजना कार्यालय के साथ साझा होंगी, ताकि वे आपकी मदद कर सकें। ठीक है तो 1 दबाइए, नहीं तो 2।",
                "तुमचं बोलणं रेकॉर्ड होईल आणि योजना कार्यालयासोबत शेअर होईल, म्हणजे ते तुम्हाला मदत करू शकतील. चालेल तर 1 दाबा, नाहीतर 2.",
                "Your answers will be recorded and shared with the scheme office so they can help you. Press 1 if that is okay, 2 if not."),
    "consent_ai": ("क्या हम आपकी आवाज़, बिना नाम और नंबर के, अपनी मशीन बेहतर बनाने में इस्तेमाल कर सकते हैं? हाँ के लिए 1, नहीं के लिए 2। आपकी मदद दोनों तरह से होगी।",
                   "तुमचा आवाज, नाव आणि नंबरशिवाय, आमची प्रणाली सुधारण्यासाठी वापरू का? हो साठी 1, नाही साठी 2. दोन्ही बाबतीत तुमची मदत होईल.",
                   "May we use your voice, without your name or number, to improve our system? Press 1 for yes, 2 for no. We will help you either way."),
    "consent_no": ("कोई बात नहीं। आप कभी भी दोबारा कॉल कर सकते हैं। धन्यवाद।",
                   "हरकत नाही. तुम्ही कधीही पुन्हा कॉल करू शकता. धन्यवाद.",
                   "No problem. You can call again any time. Thank you."),
    "returning": ("अगर आपके पास हुनरवाणी कार्ड है तो 1 दबाइए। पहली बार हैं तो 2।",
                  "तुमच्याकडे हुनरवाणी कार्ड असेल तर 1 दाबा. पहिल्यांदाच असाल तर 2.",
                  "If you have a HunarVaani card, press 1. If this is your first time, press 2."),
    "ask_id": ("अपने कार्ड पर लिखा 9 अंकों का नंबर दबाइए।", "कार्डवरचा 9 अंकी नंबर दाबा.",
               "Press the 9-digit number on your card."),
    "id_not_found": ("यह नंबर नहीं मिला। हम नई शुरुआत करते हैं।", "हा नंबर सापडला नाही. आपण नव्याने सुरुवात करू.",
                     "We could not find that number. Let us start fresh."),
    "ask_pin": ("अपना 4 अंकों का पिन दबाइए।", "तुमचा 4 अंकी पिन दाबा.", "Press your 4-digit PIN."),
    "pin_wrong": ("पिन सही नहीं है। फिर से कोशिश कीजिए।", "पिन बरोबर नाही. पुन्हा प्रयत्न करा.",
                  "That PIN is not right. Please try again."),
    "pin_locked": ("बहुत बार गलत पिन। कृपया अपने नज़दीकी केंद्र पर संपर्क करें।",
                   "खूप वेळा चुकीचा पिन. कृपया जवळच्या केंद्रावर संपर्क करा.",
                   "Too many wrong PINs. Please contact your nearest centre."),
    "welcome_back": ("फिर से स्वागत है! आपके पिछले विकल्प ये हैं।", "पुन्हा स्वागत! तुमचे मागचे पर्याय हे आहेत.",
                     "Welcome back! These are your earlier options."),
    "ask_name": ("सबसे पहले, अपना नाम बताइए।", "सर्वात आधी, तुमचं नाव सांगा.", "First, please tell us your name."),
    "after_beep": ("बीप के बाद बोलिए।", "बीपनंतर बोला.", "Speak after the beep."),
    "ask_age": ("आपकी उम्र कितनी है? दो अंकों में दबाइए। हर कोर्स की उम्र सीमा होती है, इसलिए पूछ रहे हैं।",
                "तुमचं वय किती आहे? दोन अंकांत दाबा. प्रत्येक कोर्सला वयाची मर्यादा असते, म्हणून आम्ही विचारतो.",
                "How old are you? Press two digits. Every course has an age limit, that is why we ask."),
    "ask_gender": ("महिला हैं तो 1, पुरुष हैं तो 2, बताना नहीं चाहते तो 3 दबाइए। महिलाओं के लिए अलग बैच भी होते हैं।",
                   "महिला असाल तर 1, पुरुष असाल तर 2, सांगायचं नसेल तर 3 दाबा. महिलांसाठी वेगळ्या बॅचही असतात.",
                   "Press 1 if you are a woman, 2 if a man, 3 if you prefer not to say. There are women-only batches too."),
    "ask_pincode": ("अपने इलाके का 6 अंकों का डाक पिन कोड दबाइए, ताकि हम पास के केंद्र ढूँढ सकें।",
                    "तुमच्या भागाचा 6 अंकी डाक पिन कोड दाबा, म्हणजे जवळची केंद्रं शोधता येतील.",
                    "Press your 6-digit postal PIN code, so we can find centres near you."),
    "pincode_unknown": ("यह पिन कोड हमारी सूची में नहीं है। फिर से दबाइए।", "हा पिन कोड आमच्या यादीत नाही. पुन्हा दाबा.",
                        "That PIN code is not in our list. Please press it again."),
    "ask_story": ("अब अपने बारे में बताइए: आप क्या काम करते हैं, और आगे क्या करना चाहते हैं? आराम से बोलिए।",
                  "आता तुमच्याबद्दल सांगा: तुम्ही काय काम करता, आणि पुढे काय करायचं आहे? निवांत बोला.",
                  "Now tell us about yourself: what work do you do, and what would you like to do next? Take your time."),
    "ask_aspiration": ("अगर ट्रेनिंग मुफ़्त और पास में हो, तो आप कौन-सा काम सीखना या करना चाहेंगे?",
                       "प्रशिक्षण मोफत आणि जवळ असेल, तर तुम्हाला कोणतं काम शिकायला किंवा करायला आवडेल?",
                       "If training were free and nearby, what work would you like to learn or do?"),
    "ask_family": ("आपके परिवार में पहले से कौन-सा काम होता है? बताना ज़रूरी नहीं, आप चुप भी रह सकते हैं।",
                   "तुमच्या घरात आधीपासून कोणतं काम होतं? सांगणं गरजेचं नाही, तुम्ही गप्प राहू शकता.",
                   "What work has your family done? You do not have to say; you can stay silent."),
    "ask_education": ("आप कहाँ तक पढ़े हैं? पढ़ाई नहीं की तो 1, पाँचवीं तक 2, आठवीं तक 3, दसवीं 4, बारहवीं 5, उससे ज़्यादा 6।",
                      "तुमचं शिक्षण किती झालं? शिक्षण नाही तर 1, पाचवीपर्यंत 2, आठवीपर्यंत 3, दहावी 4, बारावी 5, त्यापेक्षा जास्त 6.",
                      "How far did you study? No schooling 1, up to class 5 press 2, class 8 press 3, class 10 press 4, class 12 press 5, more press 6."),
    "ask_travel": ("रोज़ कितनी दूर आ-जा सकते हैं? पाँच किलोमीटर तक 1, पंद्रह तक 2, तीस तक 3, हॉस्टल में रह सकते हैं तो 4। यह इसलिए, ताकि ट्रेनिंग पास में मिले।",
                   "रोज किती दूर ये-जा करू शकता? पाच किलोमीटरपर्यंत 1, पंधरापर्यंत 2, तीसपर्यंत 3, वसतिगृहात राहू शकत असाल तर 4. प्रशिक्षण जवळ मिळावं म्हणून आम्ही विचारतो.",
                   "How far can you travel each day? Up to 5 kilometres press 1, 15 press 2, 30 press 3, if you can stay in a hostel press 4. This helps us find training near you."),
    "ask_health": ("क्या भारी काम या देर तक खड़े रहने में कोई शारीरिक तकलीफ़ है? नहीं तो 1, थोड़ी 2, ज़्यादा 3।",
                   "जड काम किंवा खूप वेळ उभं राहण्यात काही शारीरिक त्रास आहे का? नाही तर 1, थोडा 2, जास्त 3.",
                   "Do you have any trouble with heavy work or standing for long? None press 1, a little 2, a lot 3."),
    "ask_lean": ("आप नौकरी चाहते हैं या अपना काम? नौकरी 1, अपना काम 2, दोनों ठीक 3।",
                 "तुम्हाला नोकरी हवी आहे की स्वतःचं काम? नोकरी 1, स्वतःचं काम 2, दोन्ही चालेल 3.",
                 "Do you want a job or your own work? Job 1, own work 2, either 3."),
    "n_left_pre": ("बस", "अजून फक्त", "Just"),
    "n_left_post": ("छोटे सवाल और।", "छोटे प्रश्न.", "short questions left."),
    "ack_0": ("अच्छा।", "बरं.", "Okay."),
    "ack_1": ("समझ गए।", "समजलं.", "Understood."),
    "ack_2": ("बहुत बढ़िया।", "खूप छान.", "Very good."),
    "ack_3": ("ठीक है।", "ठीक आहे.", "All right."),
    "ack_4": ("धन्यवाद, यह जानकर अच्छा लगा।", "धन्यवाद, हे ऐकून छान वाटलं.", "Thank you, good to know."),
    "empathy_upset": ("यह सुनकर दुख हुआ। हम पूरी कोशिश करेंगे कि आपको सही काम मिले।",
                      "हे ऐकून वाईट वाटलं. तुम्हाला योग्य काम मिळावं यासाठी आम्ही पूर्ण प्रयत्न करू.",
                      "Sorry to hear that. We will do our best to help you find the right work."),
    "empathy_worried": ("चिंता मत कीजिए, यह सेवा मुफ़्त है और बस कुछ मिनट लगेंगे।",
                        "काळजी करू नका, ही सेवा मोफत आहे आणि फक्त काही मिनिटं लागतील.",
                        "Don't worry: it is free and takes only a few minutes."),
    "empathy_hopeful": ("यह तो बहुत अच्छी बात है, इस पर आगे बढ़ सकते हैं।", "ही खूप छान गोष्ट आहे, यावरून पुढे जाऊ शकतो.",
                        "That is great, we can build on that."),
    "didnt_hear": ("माफ़ कीजिए, आवाज़ साफ़ नहीं आई। एक बार फिर बोलिए।", "माफ करा, आवाज नीट आला नाही. पुन्हा एकदा बोला.",
                   "Sorry, we could not hear you clearly. Please say it once more."),
    "use_keys": ("कोई बात नहीं, हम बटन से आगे बढ़ते हैं।", "हरकत नाही, आपण बटणांनी पुढे जाऊ.",
                 "No problem, let us continue with the keypad."),
    "wrong_key": ("यह बटन विकल्प में नहीं है।", "हे बटण पर्यायात नाही.", "That key is not one of the choices."),
    "no_answer": ("हमें कोई जवाब नहीं मिला।", "आम्हाला उत्तर मिळालं नाही.", "We did not get an answer."),
    "readback_intro": ("आपने बताया:", "तुम्ही सांगितलं:", "You told us:"),
    "rb_work": ("आपका काम:", "तुमचं काम:", "your work:"),
    "rb_want": ("आप करना चाहते हैं:", "तुम्हाला करायचं आहे:", "you want to do:"),
    "years_pre": ("", "", "for"),
    "years_post": ("साल से।", "वर्षांपासून.", "years."),
    "rb_radius_pre": ("दूरी:", "अंतर:", "distance: up to"),
    "rb_radius_post": ("किलोमीटर तक।", "किलोमीटरपर्यंत.", "kilometres."),
    "rb_home": ("घर के पास ही, हॉस्टल नहीं।", "घराजवळच, वसतिगृह नाही.", "close to home, no hostel."),
    "readback_ok": ("सही है तो 1, बदलना है तो 2।", "बरोबर असेल तर 1, बदलायचं असेल तर 2.",
                    "Press 1 if this is right, 2 to change it."),
    "thinking": ("एक पल रुकिए, हम आपके लिए विकल्प देख रहे हैं।", "एक क्षण थांबा, तुमच्यासाठी पर्याय शोधत आहोत.",
                 "One moment, we are finding options for you."),
    "no_options": ("अभी आपके इलाके में सही विकल्प नहीं मिला। अधिकारी आपसे संपर्क करेंगे।",
                   "आत्ता तुमच्या भागात योग्य पर्याय सापडला नाही. अधिकारी तुमच्याशी संपर्क करतील.",
                   "We could not find a good option near you right now. An officer will contact you."),
    "options_intro": ("आपके लिए ये विकल्प हैं।", "तुमच्यासाठी हे पर्याय आहेत.", "Here are your options."),
    "option_word": ("विकल्प", "पर्याय", "Option"),
    "kind_upskill": ("ट्रेनिंग:", "प्रशिक्षण:", "training in"),
    "kind_certificate": ("आपके हुनर का सरकारी प्रमाणपत्र:", "तुमच्या कौशल्याचं सरकारी प्रमाणपत्र:",
                         "a government certificate for your skill in"),
    "kind_startup": ("अपना काम शुरू करने की ट्रेनिंग", "स्वतःचं काम सुरू करण्याचं प्रशिक्षण", "training to start your own work"),
    "ctype_block": ("ब्लॉक कौशल केंद्र में,", "ब्लॉक कौशल केंद्रात,", "at the block skill centre,"),
    "ctype_pmkk": ("प्रधानमंत्री कौशल केंद्र में,", "प्रधानमंत्री कौशल केंद्रात,", "at the PM Kaushal Kendra,"),
    "ctype_rseti": ("बैंक के प्रशिक्षण संस्थान, आरसेटी में,", "बँकेच्या प्रशिक्षण संस्थेत, आरसेटीमध्ये,",
                    "at RSETI, the bank training institute,"),
    "ctype_iti": ("सरकारी आईटीआई में,", "सरकारी आयटीआयमध्ये,", "at the government ITI,"),
    "km_pre": ("लगभग", "सुमारे", "about"),
    "km_post": ("किलोमीटर दूर,", "किलोमीटर दूर,", "kilometres away,"),
    "weeks_post": ("हफ़्ते,", "आठवडे,", "weeks,"),
    "free": ("मुफ़्त।", "मोफत.", "free."),
    "choose_prompt": ("किसी विकल्प के बारे में और सुनने या उसे चुनने के लिए उसका नंबर दबाइए। सब फिर से सुनने के लिए 8।",
                      "एखाद्या पर्यायाबद्दल अधिक ऐकायला किंवा तो निवडायला त्याचा नंबर दाबा. सगळे पुन्हा ऐकायला 8.",
                      "Press an option's number to hear more or choose it. To hear them all again, press 8."),
    "why_intro": ("यह क्यों:", "हे का:", "Why:"),
    "reason_aspiration": ("यह वही काम है जो आप करना चाहते हैं।", "हेच काम तुम्हाला करायचं आहे.", "it is the work you want to do."),
    "reason_skill": ("यह आपके अभी के काम पर आगे बढ़ता है।", "हे तुमच्या आत्ताच्या कामावर आधारित आहे.",
                     "it builds on the work you already do."),
    "reason_demand": ("आपके ज़िले में इस काम की माँग है।", "तुमच्या जिल्ह्यात या कामाला मागणी आहे.",
                      "this work is in demand in your district."),
    "reason_access": ("यह आपके घर के पास है।", "हे तुमच्या घराजवळ आहे.", "it is close to your home."),
    "reason_completion": ("यह छोटा और मुफ़्त है, पूरा करना आसान है।", "हे छोटं आणि मोफत आहे, पूर्ण करणं सोपं आहे.",
                          "it is short and free, easy to finish."),
    "reason_income": ("इसमें कमाई बेहतर है।", "यात कमाई चांगली आहे.", "it pays better."),
    "new_skills": ("इसमें आप नई बातें भी सीखेंगे।", "यात तुम्ही नवीन गोष्टीही शिकाल.", "You will also learn new skills."),
    "confirm_choice": ("इसे चुनने के लिए 1, बाकी विकल्पों पर लौटने के लिए 2।",
                       "हा निवडायला 1, बाकीच्या पर्यायांकडे परत जायला 2.",
                       "To choose this, press 1. To go back to the options, press 2."),
    "chosen": ("बहुत अच्छा। आपका चुनाव दर्ज हो गया।", "खूप छान. तुमची निवड नोंदवली आहे.", "Great. Your choice is saved."),
    "your_id": ("आपका हुनरवाणी नंबर है:", "तुमचा हुनरवाणी नंबर आहे:", "Your HunarVaani number is:"),
    "once_more": ("फिर से:", "पुन्हा:", "Once more:"),
    "write_down": ("इसे लिख लीजिए। यही आपकी पहचान है।", "हा लिहून ठेवा. हीच तुमची ओळख आहे.",
                   "Please write it down. This is your ID."),
    "set_pin": ("अब अपना 4 अंकों का गुप्त पिन चुनिए और दबाइए। इसे किसी को न बताएँ।",
                "आता तुमचा 4 अंकी गुप्त पिन निवडा आणि दाबा. तो कोणालाही सांगू नका.",
                "Now choose a 4-digit secret PIN and press it. Do not tell anyone."),
    "set_pin_again": ("वही पिन फिर से दबाइए।", "तोच पिन पुन्हा दाबा.", "Press the same PIN again."),
    "pin_mismatch": ("दोनों पिन अलग थे। फिर से कोशिश कीजिए।", "दोन्ही पिन वेगळे होते. पुन्हा प्रयत्न करा.",
                     "The two PINs did not match. Please try again."),
    "pin_saved": ("आपका पिन सेव हो गया।", "तुमचा पिन सेव्ह झाला.", "Your PIN is saved."),
    "documents": ("केंद्र पर ये साथ ले जाइए: आधार कार्ड, बैंक पासबुक, पढ़ाई का प्रमाणपत्र, दो फोटो, और जाति प्रमाणपत्र अगर है।",
                  "केंद्रावर हे सोबत न्या: आधार कार्ड, बँक पासबुक, शिक्षणाचं प्रमाणपत्र, दोन फोटो, आणि जातीचा दाखला असेल तर.",
                  "Take these to the centre: Aadhaar card, bank passbook, education certificate, two photos, and a caste certificate if you have one."),
    "officer_next": ("आपके ज़िले के अधिकारी आपका रिकॉर्ड देखेंगे और आपसे संपर्क करेंगे।",
                     "तुमच्या जिल्ह्याचे अधिकारी तुमची नोंद पाहतील आणि तुमच्याशी संपर्क करतील.",
                     "Officers in your district will see your record and contact you."),
    "never_money": ("हुनरवाणी कभी पैसे या ओटीपी नहीं माँगता।", "हुनरवाणी कधीही पैसे किंवा ओटीपी मागत नाही.",
                    "HunarVaani never asks for money or an OTP."),
    "goodbye": ("धन्यवाद! आपका दिन शुभ हो।", "धन्यवाद! तुमचा दिवस छान जावो.", "Thank you, and have a good day."),
    "human_flag": ("ठीक है, एक अधिकारी आपको जल्द वापस कॉल करेंगे। तब तक हम आगे बढ़ते हैं।",
                   "ठीक आहे, एक अधिकारी तुम्हाला लवकरच परत कॉल करतील. तोपर्यंत आपण पुढे जाऊ.",
                   "Okay, an officer will call you back soon. Meanwhile, let us continue."),
    "delete_confirm": ("आपकी सारी जानकारी मिटाने के लिए फिर से 9 दबाइए। रुकने के लिए कोई और बटन।",
                       "तुमची सगळी माहिती पुसायला पुन्हा 9 दाबा. थांबायला दुसरं कोणतंही बटण.",
                       "To delete all your information, press 9 again. Any other key to stop."),
    "deleted": ("आपकी जानकारी मिटा दी गई है। धन्यवाद।", "तुमची माहिती पुसली आहे. धन्यवाद.",
                "Your information has been deleted. Thank you."),
    "tradeoff_q": ("आपके लिए क्या ज़्यादा ज़रूरी है?", "तुमच्यासाठी काय जास्त महत्त्वाचं आहे?", "Which matters more to you?"),
    "tf_aspiration": ("मनचाहा काम", "आवडीचं काम", "doing the work you want"),
    "tf_skill": ("अपने हुनर का इस्तेमाल", "स्वतःच्या कौशल्याचा वापर", "using the skills you have"),
    "tf_demand": ("पास में ज़्यादा नौकरियाँ", "जवळपास जास्त नोकऱ्या", "more jobs nearby"),
    "tf_access": ("घर के पास होना", "घराजवळ असणं", "staying close to home"),
    "tf_completion": ("छोटा और आसान कोर्स", "छोटा आणि सोपा कोर्स", "a short, easy course"),
    "tf_income": ("ज़्यादा कमाई", "जास्त कमाई", "better pay"),
    "tf_press_1": ("के लिए 1 दबाइए,", "साठी 1 दाबा,", ": press 1;"),
    "tf_press_2": ("के लिए 2 दबाइए।", "साठी 2 दाबा.", ": press 2."),
    "card_ready": ("आपका कार्ड तैयार है।", "तुमचं कार्ड तयार आहे.", "Your card is ready."),
    # mood-adapted versions of questions (hv/engine.py picks them from the LLM's mood label)
    "ask_aspiration_soft": ("कोई जल्दी नहीं। अगर आप कुछ नया सीख सकें, तो कौन-सा काम आपको अच्छा लगेगा?",
                            "काही घाई नाही. जर काही नवीन शिकता आलं, तर कोणतं काम तुम्हाला आवडेल?",
                            "There is no hurry. If you could learn something new, what work would you like?"),
    "ask_aspiration_hope": ("बहुत अच्छा! आपका सपना क्या है, आगे चलकर कौन-सा काम करना चाहेंगे?",
                            "खूप छान! तुमचं स्वप्न काय आहे, पुढे कोणतं काम करायला आवडेल?",
                            "Wonderful! What is your dream, what work would you like to do in the future?"),
    "ask_family_soft": ("अगर आप चाहें तो बताइए, आपके घर में कौन-सा काम होता है। न बताना भी बिल्कुल ठीक है।",
                        "तुम्हाला वाटलं तर सांगा, तुमच्या घरात कोणतं काम होतं. न सांगणंही अगदी ठीक आहे.",
                        "Only if you wish: what work does your family do? It is completely fine not to say."),
    "keys_soft_intro": ("आराम से। बस कुछ आसान सवाल बचे हैं।", "निवांत. फक्त काही सोपे प्रश्न उरले आहेत.",
                        "Take it easy. Only a few simple questions are left."),
    # skills to learn (hv/skills.py)
    "skill_tip_pre": ("एक सलाह: कुछ नए हुनर सीखकर आप इस काम में आगे बढ़ सकते हैं:",
                      "एक सल्ला: काही नवीन कौशल्यं शिकून तुम्ही या कामात पुढे जाऊ शकता:",
                      "One tip: a few new skills can take you further in"),
    "skill_tip_mid": ("सीखने में लगभग", "शिकायला सुमारे", "Learning takes about"),
    "skill_tip_post": ("लगेंगे। पूरी जानकारी आपके कार्ड पर और अधिकारी के पास है।",
                       "लागतील. पूर्ण माहिती तुमच्या कार्डवर आणि अधिकाऱ्यांकडे आहे.",
                       "The details are on your card and with the officer."),
    "one_moment": ("एक पल, हम समझ रहे हैं।", "एक क्षण, आम्ही समजून घेत आहोत.", "One moment, we are listening to that."),
    "weeks_word": ("हफ़्ते", "आठवडे", "weeks."),
    # spoken versions of the questions (the keypad versions above are the fallback)
    "say_age": ("आपकी उम्र कितनी है? बस बोलिए, जैसे 'पैंतीस साल'।", "तुमचं वय किती आहे? फक्त सांगा, जसं 'पस्तीस वर्षं'.",
                "How old are you? Just say it, for example 'thirty-five'."),
    "say_gender": ("आप महिला हैं या पुरुष? न बताना चाहें तो 'नहीं बताना' कहिए। महिलाओं के लिए अलग बैच भी होते हैं।",
                   "तुम्ही महिला आहात की पुरुष? सांगायचं नसेल तर 'सांगायचं नाही' म्हणा. महिलांसाठी वेगळ्या बॅचही असतात.",
                   "Are you a woman or a man? If you prefer not to say, just say so. There are women-only batches too."),
    "say_education": ("आप कहाँ तक पढ़े हैं? जैसे 'आठवीं तक', 'दसवीं', या 'पढ़ाई नहीं की'।",
                      "तुमचं शिक्षण किती झालं? जसं 'आठवीपर्यंत', 'दहावी', किंवा 'शिक्षण नाही'.",
                      "How far did you study? For example 'up to class eight', 'class ten', or 'no schooling'."),
    "say_travel": ("ट्रेनिंग के लिए रोज़ कितनी दूर जा सकते हैं? किलोमीटर या समय में बताइए, और यह भी कि हॉस्टल में रह सकते हैं या नहीं।",
                   "प्रशिक्षणासाठी रोज किती दूर जाऊ शकता? किलोमीटर किंवा वेळेत सांगा, आणि वसतिगृहात राहू शकता का तेही.",
                   "How far can you travel each day for training? Say it in kilometres or minutes, and whether you could stay in a hostel."),
    "say_health": ("क्या भारी काम या देर तक खड़े रहने में कोई शारीरिक तकलीफ़ है? 'नहीं', 'थोड़ी' या 'ज़्यादा' बोलिए।",
                   "जड काम किंवा खूप वेळ उभं राहण्यात काही शारीरिक त्रास आहे का? 'नाही', 'थोडा' किंवा 'जास्त' म्हणा.",
                   "Do you have any trouble with heavy work or standing for long? Say 'no', 'a little' or 'a lot'."),
    "say_lean": ("आप तनख़्वाह वाली नौकरी चाहते हैं या अपना काम? 'नौकरी', 'अपना काम' या 'दोनों' बोलिए।",
                 "तुम्हाला पगाराची नोकरी हवी की स्वतःचं काम? 'नोकरी', 'स्वतःचं काम' किंवा 'दोन्ही' म्हणा.",
                 "Do you want a salaried job or your own work? Say 'job', 'own work' or 'either'."),
    "or_press_12": ("आप 1 या 2 भी दबा सकते हैं।", "तुम्ही 1 किंवा 2 सुद्धा दाबू शकता.", "You can also press 1 or 2."),
    # follow-up questions that guide towards the best work (hv/questions.py picks them)
    "q_goal": ("क्या आप अपने अभी के काम में ही आगे बढ़ना चाहते हैं, या कोई नया काम सीखना चाहते हैं?",
               "तुम्हाला सध्याच्या कामातच पुढे जायचं आहे, की काही नवीन काम शिकायचं आहे?",
               "Do you want to grow in the work you do now, or learn something new?"),
    "q_lead_pre": ("अब तक की बातों से लगता है कि यह काम आपके लिए अच्छा रहेगा:",
                   "आत्तापर्यंतच्या बोलण्यावरून असं वाटतं की हे काम तुमच्यासाठी चांगलं राहील:",
                   "From what you have told us, this work could suit you:"),
    "q_lead_post": ("क्या यह आपको ठीक लगता है? 'हाँ' या 'नहीं' बोलिए।", "हे तुम्हाला ठीक वाटतं का? 'हो' किंवा 'नाही' म्हणा.",
                    "Does that sound right? Say yes or no."),
    "q_home": ("आप घर से काम करना पसंद करेंगे, या बाहर किसी दुकान या कंपनी में जाकर?",
               "तुम्हाला घरून काम करायला आवडेल, की बाहेर एखाद्या दुकानात किंवा कंपनीत जाऊन?",
               "Would you rather work from home, or go out to a shop or a company?"),
    "q_duration": ("ट्रेनिंग के लिए आप कितना समय दे सकते हैं? जैसे एक महीना, तीन महीने, या छह महीने?",
                   "प्रशिक्षणासाठी तुम्ही किती वेळ देऊ शकता? जसं एक महिना, तीन महिने, किंवा सहा महिने?",
                   "How much time can you give to training? For example one month, three months or six months?"),
    "q_earn_soon": ("क्या आपको जल्दी कमाई शुरू करनी है, या पहले अच्छे से सीखना ठीक है?",
                    "तुम्हाला लवकर कमाई सुरू करायची आहे, की आधी नीट शिकलं तरी चालेल?",
                    "Do you need to start earning soon, or is it fine to learn properly first?"),
    "q_certificate": ("आप जो काम पहले से जानते हैं, क्या उसका सरकारी प्रमाणपत्र लेना चाहेंगे? इससे बेहतर काम मिलने में मदद मिलती है।",
                      "तुम्हाला जे काम आधीपासून येतं, त्याचं सरकारी प्रमाणपत्र घ्यायला आवडेल का? त्यामुळे चांगलं काम मिळायला मदत होते.",
                      "Would you like a government certificate for the work you already know? It helps you get better work."),
    "q_own_business": ("क्या आप सरकारी मदद या लोन से अपना छोटा काम शुरू करना चाहेंगे?",
                       "सरकारी मदत किंवा कर्ज घेऊन स्वतःचं छोटं काम सुरू करायला आवडेल का?",
                       "Would you like to start a small business of your own with government support or a loan?"),
    "q_years": ("यह काम आप कितने साल से कर रहे हैं?", "हे काम तुम्ही किती वर्षांपासून करता?",
                "For how many years have you done this work?"),
    "q_ctx_work": ("आपने बताया कि आप यह काम करते हैं:", "तुम्ही सांगितलं की तुम्ही हे काम करता:", "You told us you do this work:"),
    "follow_intro": ("आपकी बात से एक-दो और सवाल हैं।", "तुमच्या बोलण्यावरून अजून एक-दोन प्रश्न आहेत.",
                     "Based on what you said, a couple more questions."),
    # the review at the end: everything we understood, shown and read back, so it can be corrected
    "review_intro": ("एक बार देख लेते हैं, हमने क्या समझा:", "एकदा पाहूया, आम्ही काय समजलो:", "Let us check what we understood:"),
    "rv_age_pre": ("उम्र", "वय", "age"),
    "rv_age_post": ("साल,", "वर्षं,", "years,"),
    "rv_edu": ("पढ़ाई:", "शिक्षण:", "studies:"),
    "edu_none": ("पढ़ाई नहीं की,", "शिक्षण नाही,", "no schooling,"),
    "edu_upto_5th": ("पाँचवीं तक,", "पाचवीपर्यंत,", "up to class five,"),
    "edu_upto_8th": ("आठवीं तक,", "आठवीपर्यंत,", "up to class eight,"),
    "edu_10th": ("दसवीं,", "दहावी,", "class ten,"),
    "edu_12th": ("बारहवीं,", "बारावी,", "class twelve,"),
    "edu_graduate": ("ग्रेजुएट या उससे ज़्यादा,", "पदवी किंवा त्याहून जास्त,", "graduate or more,"),
    "rv_travel_pre": ("रोज़", "रोज", "travel up to"),
    "rv_travel_post": ("किलोमीटर तक आ-जा सकते हैं,", "किलोमीटरपर्यंत ये-जा करू शकता,", "kilometres a day,"),
    "rv_hostel": ("हॉस्टल में रह सकते हैं,", "वसतिगृहात राहू शकता,", "can stay in a hostel,"),
    "review_ok": ("सब सही है तो 'हाँ' बोलिए या 1 दबाइए। कुछ बदलना है तो 'नहीं' बोलिए या 2 दबाइए।",
                  "सगळं बरोबर असेल तर 'हो' म्हणा किंवा 1 दाबा. काही बदलायचं असेल तर 'नाही' म्हणा किंवा 2 दाबा.",
                  "If all of this is right, say yes or press 1. To change something, say no or press 2."),
    "review_which": ("क्या बदलना है? नाम 1, उम्र 2, पढ़ाई 3, दूरी 4, काम 5, महिला या पुरुष 6, शारीरिक तकलीफ़ 7।",
                     "काय बदलायचं आहे? नाव 1, वय 2, शिक्षण 3, अंतर 4, काम 5, महिला किंवा पुरुष 6, शारीरिक त्रास 7.",
                     "What should we change? Name 1, age 2, studies 3, travel 4, work 5, woman or man 6, health 7."),
    "rv_health_some": ("भारी काम में थोड़ी तकलीफ़,", "जड कामात थोडा त्रास,", "a little trouble with heavy work,"),
    "rv_health_severe": ("भारी काम में ज़्यादा तकलीफ़,", "जड कामात जास्त त्रास,", "a lot of trouble with heavy work,"),
    "review_work": ("ठीक है, फिर से बताइए आप क्या काम करते हैं और क्या करना चाहते हैं।",
                    "ठीक आहे, पुन्हा सांगा तुम्ही काय काम करता आणि काय करायचं आहे.",
                    "All right, tell us again what work you do and what you want to do."),
    "location_pre": ("आपका इलाका:", "तुमचा भाग:", "Your area:"),
}

# short button labels on the kiosk screen (shown, not spoken)
LABELS: dict[str, tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = {
    "yes_no": (("हाँ", "नहीं"), ("हो", "नाही"), ("Yes", "No")),
    "q_goal": (("इसी काम में आगे", "नया काम"), ("याच कामात पुढे", "नवीन काम"), ("Grow in my work", "Something new")),
    "q_home": (("घर से", "बाहर जाकर"), ("घरून", "बाहेर जाऊन"), ("From home", "Go out to work")),
    "q_earn_soon": (("जल्दी कमाई", "पहले सीखना"), ("लवकर कमाई", "आधी शिकणं"), ("Earn soon", "Learn first")),
    "say_gender": (("महिला", "पुरुष", "नहीं बताना"), ("महिला", "पुरुष", "सांगायचं नाही"), ("Woman", "Man", "Prefer not to say")),
    "say_lean": (("नौकरी", "अपना काम", "दोनों"), ("नोकरी", "स्वतःचं काम", "दोन्ही"), ("Job", "Own work", "Either")),
    "say_health": (("कोई तकलीफ़ नहीं", "थोड़ी", "ज़्यादा"), ("त्रास नाही", "थोडा", "जास्त"), ("None", "A little", "A lot")),
    "say_education": (("पढ़ाई नहीं", "5वीं तक", "8वीं तक", "10वीं", "12वीं", "ग्रेजुएट"),
                      ("शिक्षण नाही", "5वी पर्यंत", "8वी पर्यंत", "10वी", "12वी", "पदवी"),
                      ("No school", "Up to 5", "Up to 8", "Class 10", "Class 12", "Graduate")),
    "say_travel": (("5 किमी", "15 किमी", "30 किमी", "हॉस्टल भी ठीक"), ("5 किमी", "15 किमी", "30 किमी", "वसतिगृहही चालेल"),
                   ("5 km", "15 km", "30 km", "Hostel is fine")),
    "q_duration": (("1 महीना", "3 महीने", "6 महीने"), ("1 महिना", "3 महिने", "6 महिने"), ("1 month", "3 months", "6 months")),
    "review_which": (("नाम", "उम्र", "पढ़ाई", "दूरी", "काम", "महिला/पुरुष", "शारीरिक तकलीफ़"),
                     ("नाव", "वय", "शिक्षण", "अंतर", "काम", "महिला/पुरुष", "शारीरिक त्रास"),
                     ("Name", "Age", "Studies", "Travel", "Work", "Woman/man", "Health")),
}


def labels(key: str, lang: str) -> tuple[str, ...]:
    entry = LABELS.get(key)
    return entry[_idx(lang)] if entry else ()

_HI_NUMBERS = """शून्य एक दो तीन चार पाँच छह सात आठ नौ दस ग्यारह बारह तेरह चौदह पंद्रह सोलह सत्रह अठारह उन्नीस बीस
इक्कीस बाईस तेईस चौबीस पच्चीस छब्बीस सत्ताईस अट्ठाईस उनतीस तीस इकतीस बत्तीस तैंतीस चौंतीस पैंतीस छत्तीस सैंतीस
अड़तीस उनतालीस चालीस इकतालीस बयालीस तैंतालीस चवालीस पैंतालीस छियालीस सैंतालीस अड़तालीस उनचास पचास इक्यावन बावन
तिरपन चौवन पचपन छप्पन सत्तावन अट्ठावन उनसठ साठ इकसठ बासठ तिरसठ चौंसठ पैंसठ छियासठ सड़सठ अड़सठ उनहत्तर सत्तर
इकहत्तर बहत्तर तिहत्तर चौहत्तर पचहत्तर छिहत्तर सतहत्तर अठहत्तर उन्यासी अस्सी इक्यासी बयासी तिरासी चौरासी पचासी छियासी
सत्तासी अट्ठासी नवासी नब्बे इक्यानवे बानवे तिरानवे चौरानवे पंचानवे छियानवे सत्तानवे अट्ठानवे निन्यानवे सौ""".split()
_MR_NUMBERS = """शून्य एक दोन तीन चार पाच सहा सात आठ नऊ दहा अकरा बारा तेरा चौदा पंधरा सोळा सतरा अठरा एकोणीस वीस
एकवीस बावीस तेवीस चोवीस पंचवीस सव्वीस सत्तावीस अठ्ठावीस एकोणतीस तीस एकतीस बत्तीस तेहतीस चौतीस पस्तीस छत्तीस सदतीस
अडतीस एकोणचाळीस चाळीस एक्केचाळीस बेचाळीस त्रेचाळीस चव्वेचाळीस पंचेचाळीस सेहेचाळीस सत्तेचाळीस अठ्ठेचाळीस एकोणपन्नास पन्नास
एक्कावन्न बावन्न त्रेपन्न चोपन्न पंचावन्न छप्पन्न सत्तावन्न अठ्ठावन्न एकोणसाठ साठ एकसष्ट बासष्ट त्रेसष्ट चौसष्ट पासष्ट
सहासष्ट सदुसष्ट अडुसष्ट एकोणसत्तर सत्तर एक्काहत्तर बाहत्तर त्र्याहत्तर चौऱ्याहत्तर पंच्याहत्तर शहात्तर सत्याहत्तर
अठ्ठ्याहत्तर एकोणऐंशी ऐंशी एक्याऐंशी ब्याऐंशी त्र्याऐंशी चौऱ्याऐंशी पंच्याऐंशी शहाऐंशी सत्त्याऐंशी अठ्ठ्याऐंशी एकोणनव्वद
नव्वद एक्क्याण्णव ब्याण्णव त्र्याण्णव चौऱ्याण्णव पंच्याण्णव शहाण्णव सत्त्याण्णव अठ्ठ्याण्णव नव्व्याण्णव शंभर""".split()
_ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def _en(n: int) -> str:
    if n < 20:
        return _ONES[n]
    if n == 100:
        return "one hundred"
    return _TENS[n // 10] + ("" if n % 10 == 0 else "-" + _ONES[n % 10])


# 0-100 in each language: ages, kilometres and years are read back exactly
NUMBERS = {"hi": dict(enumerate(_HI_NUMBERS)), "mr": dict(enumerate(_MR_NUMBERS)),
           "en": {n: _en(n) for n in range(101)}}
ACKS = [f"ack_{i}" for i in range(5)]


def _idx(lang: str) -> int:
    return LANGS.index(lang) if lang in LANGS else 0


def p(key: str, lang: str) -> Part:
    return Part(key, T[key][_idx(lang)])


def ps(keys: list[str], lang: str) -> list[Part]:
    return [p(k, lang) for k in keys]


def nearest(n: int) -> int:
    return min(NUMBERS["en"], key=lambda k: (abs(k - n), k))


def num(n: int, lang: str) -> Part:
    k = nearest(n)
    return Part(f"num_{k}", NUMBERS.get(lang, NUMBERS["hi"])[k])


def digits(s: str, lang: str) -> list[Part]:
    return [num(int(ch), lang) for ch in s if ch.isdigit()]


def occ(code: int, lang: str, data: Data) -> Part | None:
    o = data.occupations.get(code)
    return Part(f"occ_{code}", o.title(lang)) if o else None


def sector(code: str, lang: str, data: Data) -> Part | None:
    s = data.sectors.get(code)
    return Part(f"sec_{code}", s.title(lang)) if s else None


def district(code: str, lang: str, data: Data) -> Part | None:
    d = data.districts.get(code)
    return Part(f"dist_{code}", d.name(lang)) if d else None


def language_menu() -> list[Part]:
    return [Part("lang_hi", T["lang_hi"][0]), Part("lang_mr", T["lang_mr"][1]), Part("lang_en", T["lang_en"][2])]


def speakable(text: str, lang: str) -> str:
    """Text for the voice model: digits become words ("1 दबाइए" -> "एक दबाइए"), since TTS models often
    misread digits. The screen keeps showing the digits."""
    words = NUMBERS.get(lang, NUMBERS["hi"])

    def say(m: "re.Match") -> str:
        n = int(m.group(0))
        return words[n] if n in words else " ".join(words[int(d)] for d in m.group(0))

    return re.sub(r"\d+", say, text)


def all_pieces(data: Data) -> dict[str, dict[str, str]]:
    """Every audio piece to render: {lang: {key: text}}."""
    out: dict[str, dict[str, str]] = {lang: {} for lang in LANGS}
    for key, texts in T.items():
        for lang, text in zip(LANGS, texts):
            if text:
                out[lang][key] = text
    for key in ("lang_hi", "lang_mr", "lang_en"):  # the language menu plays before a language is chosen
        text = next(t for t in T[key] if t)
        for lang in LANGS:
            out[lang][key] = text
    for lang in LANGS:
        for n, word in NUMBERS[lang].items():
            out[lang][f"num_{n}"] = word
        for code, o in data.occupations.items():
            out[lang][f"occ_{code}"] = o.title(lang)
        for code, s in data.sectors.items():
            out[lang][f"sec_{code}"] = s.title(lang)
        for code, d in data.districts.items():
            out[lang][f"dist_{code}"] = d.name(lang)
    return out
