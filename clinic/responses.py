"""User-facing text, kept in one place.

Every canned reply lives here keyed by (message, language). Putting them
together means adding a language or reworording a message is a single edit and
never touches the logic. `say()` falls back to English if a translation is
missing so the app never crashes on a lookup.
"""
from __future__ import annotations

LANGS = ("en", "hi", "hinglish")

RESPONSES: dict[str, dict[str, str]] = {
    "emergency": {
        "en": (
            "This sounds like a medical emergency. Please call your local "
            "emergency number (112 in India) or go to the nearest emergency "
            "room right now. I can't help with this over chat — please get "
            "help immediately."
        ),
        "hi": (
            "यह एक मेडिकल इमरजेंसी लगती है। कृपया तुरंत अपने आपातकालीन नंबर "
            "(भारत में 112) पर कॉल करें या नज़दीकी अस्पताल की इमरजेंसी में जाएं। "
            "मैं चैट पर इसमें मदद नहीं कर सकता — कृपया तुरंत मदद लें।"
        ),
        "hinglish": (
            "Yeh ek medical emergency lag rahi hai. Kripya turant apne emergency "
            "number (India mein 112) par call karein ya nazdeeki hospital ki "
            "emergency mein jaayein. Main chat par ismein madad nahi kar sakta — "
            "please turant madad lein."
        ),
    },
    "medical_advice": {
        "en": (
            "I'm not able to diagnose conditions or suggest medicines — I'm not "
            "a doctor. What I can do is book you an appointment with the right "
            "department so a clinician can help. Would you like me to do that?"
        ),
        "hi": (
            "मैं बीमारी की पहचान या दवा की सलाह नहीं दे सकता — मैं डॉक्टर नहीं हूँ। "
            "लेकिन मैं आपके लिए सही विभाग में अपॉइंटमेंट बुक कर सकता हूँ ताकि डॉक्टर "
            "आपकी मदद कर सकें। क्या मैं यह करूँ?"
        ),
        "hinglish": (
            "Main bimari ki pehchan ya dawa ki salah nahi de sakta — main doctor "
            "nahi hoon. Lekin main aapke liye sahi department mein appointment "
            "book kar sakta hoon taaki doctor aapki madad kar sakein. Kya main "
            "yeh karoon?"
        ),
    },
    # Shown when the safety classifier itself fails and we fail closed.
    "safety_degraded": {
        "en": (
            "I couldn't safely check your message just now, so to be careful I "
            "won't act on it. If this is urgent or an emergency, please call 112 "
            "(India) or your local emergency number. Otherwise please try again "
            "in a moment."
        ),
        "hi": (
            "मैं अभी आपके संदेश की सुरक्षित जाँच नहीं कर सका, इसलिए सावधानी के तौर पर "
            "मैं इस पर कार्रवाई नहीं कर रहा। अगर यह ज़रूरी या इमरजेंसी है, तो कृपया 112 "
            "(भारत) पर कॉल करें। वरना कृपया थोड़ी देर बाद फिर कोशिश करें।"
        ),
        "hinglish": (
            "Main abhi aapke message ki safe jaanch nahi kar paaya, isliye ehtiyaat "
            "ke taur par main ispar action nahi le raha. Agar yeh zaroori ya "
            "emergency hai to kripya 112 (India) par call karein. Warna thodi der "
            "baad phir koshish karein."
        ),
    },
    "tool_cap": {
        "en": (
            "I've done as much as I safely can in one go. What's the single next "
            "thing you'd like — log a symptom, book an appointment, or see your "
            "appointments?"
        ),
        "hi": (
            "मैंने एक बार में जितना सुरक्षित रूप से कर सकता था, कर दिया। अब आप एक चीज़ "
            "बताएं — लक्षण दर्ज करना, अपॉइंटमेंट बुक करना, या अपनी अपॉइंटमेंट देखना?"
        ),
        "hinglish": (
            "Maine ek baar mein jitna safe tarike se ho sakta tha kar diya. Ab ek "
            "cheez batayein — symptom log karna, appointment book karna, ya apni "
            "appointments dekhna?"
        ),
    },
    "error_generic": {
        "en": "Sorry, something went wrong on my side. Could you try rephrasing that?",
        "hi": "माफ़ करें, मेरी तरफ़ से कुछ गड़बड़ हो गई। क्या आप इसे दोबारा कह सकते हैं?",
        "hinglish": "Maaf karein, meri taraf se kuch gadbad ho gayi. Kya aap ise dobara keh sakte hain?",
    },
    "ask_date": {
        "en": "Sure — what date should I book it for? Please use a date like 2026-10-15.",
        "hi": "ज़रूर — किस तारीख के लिए बुक करूँ? कृपया 2026-10-15 जैसी तारीख बताएं।",
        "hinglish": "Zaroor — kis date ke liye book karoon? Kripya 2026-10-15 jaisi date batayein.",
    },
    "ask_department": {
        "en": "Which department would you like the appointment with?",
        "hi": "आप किस विभाग में अपॉइंटमेंट लेना चाहेंगे?",
        "hinglish": "Aap kis department mein appointment lena chahenge?",
    },
    "ask_severity": {
        "en": "How severe is it on a scale of 1 to 5?",
        "hi": "यह 1 से 5 के पैमाने पर कितना गंभीर है?",
        "hinglish": "Yeh 1 se 5 ke scale par kitna serious hai?",
    },
    "greeting": {
        "en": "Hi! I can log a symptom, book an appointment, or show your appointments. What would you like?",
        "hi": "नमस्ते! मैं लक्षण दर्ज कर सकता हूँ, अपॉइंटमेंट बुक कर सकता हूँ, या आपकी अपॉइंटमेंट दिखा सकता हूँ। आप क्या करना चाहेंगे?",
        "hinglish": "Namaste! Main symptom log kar sakta hoon, appointment book kar sakta hoon, ya aapki appointments dikha sakta hoon. Aap kya karna chahenge?",
    },
    "fallback": {
        "en": "I can log a symptom, book an appointment, or show your appointments. Which one would you like?",
        "hi": "मैं लक्षण दर्ज कर सकता हूँ, अपॉइंटमेंट बुक कर सकता हूँ, या आपकी अपॉइंटमेंट दिखा सकता हूँ। आप कौन सा चाहेंगे?",
        "hinglish": "Main symptom log kar sakta hoon, appointment book kar sakta hoon, ya aapki appointments dikha sakta hoon. Aap konsa chahenge?",
    },
}


def say(key: str, lang: str = "en") -> str:
    variants = RESPONSES[key]
    return variants.get(lang) or variants["en"]
