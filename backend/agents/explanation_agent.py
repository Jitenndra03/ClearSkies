from groq import Groq
import os

class ExplanationAgent:
    def __init__(self):
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
        self.model = "llama3-8b-8192"

    def answer(self, query: str, context: dict, language: str = "en") -> dict:
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
