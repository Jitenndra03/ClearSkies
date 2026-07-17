"""
knowledge_corpus.py
--------------------
Small curated corpus for System Feature 8 (AI Chat Assistant / RAG).

Per the plan's Section 5, the production version would index NCAP docs,
CPCB guidelines, and historical intervention logs via Sentence-Transformers.
For the hackathon build, this hand-written corpus covers the same topics
a citizen or official would actually ask about -- AQI categories, how
each agent works, and how the system's decisions should be interpreted --
so `ChatAssistantAgent` (agents/chat_agent.py) has real, citable ground
truth to retrieve from instead of hallucinating.

Each entry: {id, title, text}. Keep `text` factual and self-contained --
it gets stitched directly into chat answers, so avoid references that
only make sense with surrounding paragraphs.
"""

DOCS = [
    {
        "id": "aqi-categories",
        "title": "AQI categories (CPCB)",
        "text": (
            "India's CPCB AQI scale has six bands: Good (0-50), Satisfactory (51-100), "
            "Moderate (101-200), Poor (201-300), Very Poor (301-400), and Severe (401-500). "
            "Sensitive groups -- children, the elderly, and people with respiratory or heart "
            "conditions -- should start limiting outdoor exertion from the Moderate band onward."
        ),
    },
    {
        "id": "source-attribution-method",
        "title": "How source attribution works",
        "text": (
            "The Pollution Attribution Agent classifies each hotspot into traffic, construction, "
            "industrial, dust, or stubble-burning using a RandomForest model trained on traffic "
            "density, construction permit density, industrial stack counts, satellite thermal "
            "anomaly counts, and dust-prone land-use percentage near the hotspot. It always reports "
            "a confidence score rather than a certainty, and is designed as decision support for "
            "officials, not as standalone legal evidence."
        ),
    },
    {
        "id": "forecast-method",
        "title": "How the AQI forecast works",
        "text": (
            "The AQI Prediction Agent uses a LightGBM regression model trained on historical AQI, "
            "weather features (wind speed, humidity, temperature inversion likelihood), and a "
            "traffic emission index to forecast ward-level AQI 24, 48, and 72 hours ahead. "
            "Confidence intervals widen at longer horizons because weather and traffic uncertainty "
            "compounds over time."
        ),
    },
    {
        "id": "enforcement-priority",
        "title": "How the enforcement queue is ranked",
        "text": (
            "The Smart Enforcement Prioritization Agent ranks registered emission sources by a "
            "composite risk score combining proximity to an active hotspot, permit status "
            "(unpermitted sources score higher), days since last inspection, and the forecast "
            "severity of the ward they sit in. This lets inspectors go to the highest-impact site "
            "first instead of working a list in arrival order."
        ),
    },
    {
        "id": "recommendation-engine",
        "title": "How intervention recommendations are generated",
        "text": (
            "The Recommendation Agent uses a deterministic source-by-severity decision matrix -- "
            "not an LLM -- so every recommended action is auditable and repeatable. Given an "
            "attributed source (e.g. construction) and a severity band (e.g. Very Poor), it returns "
            "concrete, time-bound, role-specific actions such as deploying water sprinklers or "
            "restricting a construction site's working hours, tagged with which department is "
            "responsible and how urgently it should act."
        ),
    },
    {
        "id": "emergency-detection",
        "title": "How emergency spikes are detected",
        "text": (
            "The Emergency Pollution Detection Agent runs three independent checks on every "
            "station's recent readings: a rolling z-score on PM2.5 against that station's own "
            "baseline, a rate-of-change check on AQI over a short window, and an absolute "
            "severe-band threshold. Any single trigger raises an alert, which lets it catch both "
            "sudden events like a fire and gradual severe buildups."
        ),
    },
    {
        "id": "outcome-tracking",
        "title": "How the intervention outcome loop works",
        "text": (
            "After an enforcement action is logged, officials record the AQI before and after the "
            "intervention. The Analytics Dashboard aggregates these into an average AQI drop per "
            "action type, which is what lets the system say whether a given intervention -- like "
            "sprinkling or a construction stop-work order -- actually worked, rather than assuming "
            "it did."
        ),
    },
    {
        "id": "multi-city-comparison",
        "title": "How city comparison works",
        "text": (
            "The Multi-city Comparison Agent benchmarks cities on average AQI, how many "
            "interventions were logged, and the average AQI drop achieved per intervention over a "
            "configurable window (30 days by default). It highlights not just which city has worse "
            "air, but which city's interventions are actually more effective per action taken."
        ),
    },
    {
        "id": "citizen-advisory",
        "title": "How citizen advisories are personalized",
        "text": (
            "The Citizen Advisory Agent builds a health advisory from a citizen's forecast AQI band "
            "plus their vulnerability profile (asthma, elderly, outdoor worker), in their preferred "
            "language. Vulnerable citizens get an extra addendum with specific precautions on top of "
            "the base band advisory that everyone in that ward receives."
        ),
    },
    {
        "id": "data-sources",
        "title": "What data the system runs on",
        "text": (
            "AirPulse ingests CPCB CAAQMS ground-station readings, Open-Meteo weather forecasts, "
            "OpenStreetMap/Overpass land-use and traffic proxies, and NASA FIRMS thermal anomaly "
            "data for stubble-burning and fire detection -- all free-tier or open sources, refreshed "
            "every 15 to 60 minutes depending on each API's rate limit."
        ),
    },
    {
        "id": "alerts-channels",
        "title": "How real-time alerts are dispatched",
        "text": (
            "When a forecast crosses into a worse AQI band or the Emergency Detection Agent fires, "
            "the Real-Time Alerts Agent dispatches a notification through push, SMS, or the in-app "
            "feed depending on severity and the recipient's channel preference, and logs every "
            "dispatch so the Alerts page always reflects what was actually sent, to whom, and when."
        ),
    },
    {
        "id": "ncap-context",
        "title": "NCAP and non-attainment cities",
        "text": (
            "The National Clean Air Programme (NCAP) tracks 131 non-attainment cities in India that "
            "did not meet national ambient air quality standards. AirPulse is designed as a "
            "reusable template -- the same pipeline and agents can be pointed at a new city by "
            "swapping in that city's ward boundaries and station list, without rebuilding the "
            "system."
        ),
    },
]
