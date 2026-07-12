"""
advisory_agent.py
------------------
System Feature 5: Citizen Health Advisory

Generates a personalized, multilingual health advisory for a citizen based on
their ward's forecast AQI and their individual vulnerability profile
(respiratory conditions, elderly, outdoor worker).

Design notes:
- Risk banding follows the standard Indian AQI categories (CPCB) so the
  advisory text stays consistent with what citizens already see elsewhere.
- Templates are separated from logic so adding a new language is a data
  change, not a code change (add a dict entry -- no agent logic touched).
  The problem statement calls out Kannada/Tamil for Bengaluru/Chennai --
  this structure makes that a 10-minute addition, not a rewrite.
"""

from dataclasses import dataclass
from typing import Optional

AQI_BANDS = [
    (0, 50, "good"),
    (51, 100, "satisfactory"),
    (101, 200, "moderate"),
    (201, 300, "poor"),
    (301, 400, "very_poor"),
    (401, 500, "severe"),
]

# Base advisory copy per AQI band, per language.
# Add a new language by adding a new top-level key -- no code changes needed.
TEMPLATES = {
    "en": {
        "good": "Air quality is good in your area. Enjoy outdoor activities.",
        "satisfactory": "Air quality is acceptable. Sensitive individuals should watch for symptoms.",
        "moderate": "Air quality is moderate. People with asthma or heart conditions should limit prolonged outdoor exertion.",
        "poor": "Air quality is poor. Avoid outdoor exercise. Sensitive groups should stay indoors where possible.",
        "very_poor": "Air quality is very poor. Everyone should reduce outdoor activity. Use a mask (N95) if you must go out.",
        "severe": "Air quality is severe -- a health emergency for sensitive groups. Stay indoors, keep windows closed, use an air purifier if available.",
    },
    "hi": {
        "good": "आपके क्षेत्र में वायु गुणवत्ता अच्छी है। बाहर की गतिविधियों का आनंद लें।",
        "satisfactory": "वायु गुणवत्ता संतोषजनक है। संवेदनशील व्यक्तियों को लक्षणों पर ध्यान देना चाहिए।",
        "moderate": "वायु गुणवत्ता मध्यम है। अस्थमा या हृदय रोगियों को लंबे समय तक बाहर शारीरिक गतिविधि से बचना चाहिए।",
        "poor": "वायु गुणवत्ता खराब है। बाहर व्यायाम से बचें। संवेदनशील वर्ग घर के अंदर रहें।",
        "very_poor": "वायु गुणवत्ता बहुत खराब है। सभी को बाहर की गतिविधि कम करनी चाहिए। बाहर जाने पर N95 मास्क का उपयोग करें।",
        "severe": "वायु गुणवत्ता गंभीर है — संवेदनशील वर्ग के लिए स्वास्थ्य आपातकाल। घर के अंदर रहें, खिड़कियां बंद रखें, एयर प्यूरीफायर का उपयोग करें।",
    },
}

VULNERABILITY_ADDENDA = {
    "en": {
        "asthma": "As someone with a respiratory condition, consider keeping rescue medication on hand today.",
        "elderly": "Elderly residents should avoid peak-pollution hours (typically early morning and evening).",
        "outdoor_worker": "If you work outdoors, take frequent breaks in ventilated indoor spaces where possible.",
    },
    "hi": {
        "asthma": "श्वास रोग होने की स्थिति में, आज अपनी दवा अपने पास रखें।",
        "elderly": "वृद्ध निवासियों को उच्च प्रदूषण घंटों (आमतौर पर सुबह और शाम) से बचना चाहिए।",
        "outdoor_worker": "यदि आप बाहर काम करते हैं, तो जहां तक संभव हो हवादार स्थानों में बार-बार विश्राम लें।",
    },
}


@dataclass
class CitizenProfile:
    user_id: str
    ward: str
    language: str = "en"
    conditions: Optional[list] = None
    elderly: bool = False
    outdoor_worker: bool = False


@dataclass
class Advisory:
    user_id: str
    ward: str
    language: str
    risk_level: str
    forecast_aqi: float
    message: str


class CitizenAdvisoryAgent:
    """
    Role: Generates personalized, multilingual health advisories.
    Inputs: ward-level forecast AQI (from Prediction Agent) + citizen
            vulnerability profile.
    Outputs: Advisory (ready to hand to the Notification Service for
             push/SMS/IVR dispatch).
    Talks to: Prediction Agent (consumes forecast), Notification Service
              (produces dispatch-ready message).
    """

    def band_for_aqi(self, aqi: float) -> str:
        for low, high, band in AQI_BANDS:
            if low <= aqi <= high:
                return band
        return "severe"  # anything above the top band

    def generate(self, profile: CitizenProfile, forecast_aqi: float) -> Advisory:
        lang = profile.language if profile.language in TEMPLATES else "en"
        band = self.band_for_aqi(forecast_aqi)

        message = TEMPLATES[lang][band]

        addenda = []
        for condition in (profile.conditions or []):
            addendum = VULNERABILITY_ADDENDA.get(lang, {}).get(condition)
            if addendum:
                addenda.append(addendum)
        if profile.elderly:
            addendum = VULNERABILITY_ADDENDA.get(lang, {}).get("elderly")
            if addendum:
                addenda.append(addendum)
        if profile.outdoor_worker:
            addendum = VULNERABILITY_ADDENDA.get(lang, {}).get("outdoor_worker")
            if addendum:
                addenda.append(addendum)

        full_message = " ".join([message] + addenda)

        return Advisory(
            user_id=profile.user_id,
            ward=profile.ward,
            language=lang,
            risk_level=band,
            forecast_aqi=forecast_aqi,
            message=full_message,
        )

    def generate_batch(self, profiles: list[CitizenProfile], ward_forecasts: dict) -> list[Advisory]:
        """ward_forecasts: {ward_name: forecast_aqi}"""
        results = []
        for profile in profiles:
            forecast_aqi = ward_forecasts.get(profile.ward, 0)
            results.append(self.generate(profile, forecast_aqi))
        return results


if __name__ == "__main__":
    agent = CitizenAdvisoryAgent()

    profiles = [
        CitizenProfile(user_id="u1", ward="Ward-1", language="en", conditions=["asthma"]),
        CitizenProfile(user_id="u2", ward="Ward-3", language="hi", outdoor_worker=True),
        CitizenProfile(user_id="u3", ward="Ward-6", language="hi", elderly=True),
    ]
    forecasts = {"Ward-1": 240, "Ward-3": 130, "Ward-6": 410}

    for advisory in agent.generate_batch(profiles, forecasts):
        print(advisory)
