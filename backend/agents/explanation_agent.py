from groq import Groq
import os
import logging

class ExplanationAgent:
    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        logging.info(f"ExplanationAgent init — GROQ_API_KEY present: {bool(api_key)}, starts with: {api_key[:8] if api_key else 'MISSING'}")
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"

    def answer(self, query: str, context: dict, language: str = "en") -> dict:
        try:
            lang_instruction = "Respond in Hindi (Devanagari script)." if language == "hi" else "Respond in English."
            system_prompt = f"""You are ClearSkies, an air quality assistant for city residents in India.
Answer ONLY using the data provided in the context below. Do not invent statistics or sources.
{lang_instruction}
Keep your answer under 80 words. End with exactly one short actionable recommendation for the citizen.
Always cite your data source as "ClearSkies AQI Monitor" at the end in italics.

Context:
- Ward: {context.get('ward', 'Unknown')}
- Current AQI: {context.get('aqi', 'N/A')}
- Primary pollution source: {context.get('source', 'Unknown')} ({context.get('confidence', 'N/A')}% confidence)
- Health risk level: {context.get('risk_level', 'Unknown')}
- Peak pollution month: {context.get('peak_month', 'Unknown')}
- Weekday vs weekend AQI delta: {context.get('weekday_delta', 'N/A')}"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                max_tokens=200,
                temperature=0.4
            )
            return {
                "answer": response.choices[0].message.content,
                "citation": "ClearSkies AQI Monitor",
                "language": language
            }
        except Exception as e:
            logging.error(f"Groq API call failed: {type(e).__name__}: {e}")
            raise