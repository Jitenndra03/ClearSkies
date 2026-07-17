"""
chat_agent.py
--------------
System Feature 8: AI Chat Assistant

RAG-lite implementation: TF-IDF + cosine similarity retrieval over
data/knowledge_corpus.py, then a templated answer built from the
top-matching chunks with citations -- so "why is AQI high near me today?"
gets an evidence-backed answer instead of a raw LLM guess.

This is a deliberately lighter-weight stand-in for the plan's
"Sentence-Transformers + RAG" design (Section 5/8): TF-IDF needs no model
download and runs instantly, which matters for a 48h build, at some cost
to semantic matching quality vs. real embeddings. Swap
`_vectorize()`/`_similarity()` for a sentence-transformers encoder later
without changing the retrieval/answer-assembly logic below.

To go from "retrieval + template" to genuine free-text generation, plug a
real LLM call into `_synthesize_answer()` -- the retrieved chunks are
already assembled as context, ready to hand to a prompt.

Role: Answers free-text questions using retrieved, cited context instead
      of an unconstrained LLM response.
Inputs: user query (str) + optional live context (current AQI, ward,
        attribution result) to ground the answer in real-time data.
Outputs: ChatAnswer (answer text + list of cited source titles).
Talks to: Chat UI. Can also pull from AttributionAgent / EmergencyDetectionAgent
          outputs when the caller supplies them as live_context.
"""

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class ChatAnswer:
    query: str
    answer: str
    citations: list = field(default_factory=list)  # list of {title, id}
    confidence: float = 0.0  # top retrieval similarity score, not answer correctness


class ChatAssistantAgent:
    """
    Role: Retrieves the most relevant knowledge-corpus chunks for a query
          and assembles a cited answer, optionally grounded in live
          per-ward data supplied by the caller.
    Inputs: query string, corpus (list of {id, title, text} dicts),
            optional live_context dict (e.g. {"ward": ..., "aqi": ...,
            "attributed_source": ...}).
    Outputs: ChatAnswer.
    Talks to: Chat UI.
    """

    def __init__(self, corpus: list[dict], top_k: int = 2, min_similarity: float = 0.05):
        self.corpus = corpus
        self.top_k = top_k
        self.min_similarity = min_similarity
        self._vectorizer = TfidfVectorizer(stop_words="english")
        # Index title + text together -- a query using a document's title
        # wording (e.g. "enforcement queue") should match even if that
        # exact phrase never appears in the body text itself.
        combined_docs = [f"{d['title']} {d['text']}" for d in corpus]
        self._doc_matrix = self._vectorizer.fit_transform(combined_docs)

    def retrieve(self, query: str) -> list[dict]:
        """Returns the top_k corpus entries most similar to the query,
        each with a `similarity` score attached, filtered by min_similarity."""
        query_vec = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._doc_matrix)[0]
        ranked_idx = np.argsort(scores)[::-1][: self.top_k]

        results = []
        for i in ranked_idx:
            if scores[i] < self.min_similarity:
                continue
            entry = dict(self.corpus[i])
            entry["similarity"] = round(float(scores[i]), 3)
            results.append(entry)
        return results

    def answer(self, query: str, live_context: Optional[dict] = None) -> ChatAnswer:
        retrieved = self.retrieve(query)

        if not retrieved:
            return ChatAnswer(
                query=query,
                answer=(
                    "I don't have enough grounded information to answer that confidently. "
                    "Try asking about AQI categories, source attribution methodology, "
                    "enforcement prioritization, emergency detection, or multi-city comparison."
                ),
                citations=[],
                confidence=0.0,
            )

        answer_text = self._synthesize_answer(query, retrieved, live_context)
        citations = [{"id": r["id"], "title": r["title"]} for r in retrieved]
        top_confidence = retrieved[0]["similarity"]

        return ChatAnswer(query=query, answer=answer_text, citations=citations, confidence=top_confidence)

    @staticmethod
    def _synthesize_answer(query: str, retrieved: list[dict], live_context: Optional[dict]) -> str:
        """
        Template-based synthesis: stitches retrieved chunks together with a
        short lead-in, and prepends live per-ward data if the caller
        supplied it (e.g. from AttributionAgent's output for "why is my
        ward's AQI high right now").

        Replace this method's body with a real LLM call
        (e.g. "Answer the question using ONLY this context: ...") once an
        LLM API key is available -- `retrieved` and `live_context` are
        already the exact inputs such a prompt would need.
        """
        parts = []

        if live_context:
            ward = live_context.get("ward")
            aqi = live_context.get("aqi")
            source = live_context.get("attributed_source")
            if ward and aqi is not None:
                line = f"Right now, {ward} has an AQI of {aqi:.0f}."
                if source:
                    line += f" The current hotspot is attributed to {source.replace('_', ' ')}."
                parts.append(line)

        for r in retrieved:
            parts.append(r["text"])

        return " ".join(parts)


if __name__ == "__main__":
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from data.knowledge_corpus import DOCS

    agent = ChatAssistantAgent(DOCS)

    print("--- Q: why is AQI high near me today? (with live context) ---")
    result = agent.answer(
        "why is my air quality bad today",
        live_context={"ward": "Ward-3", "aqi": 312, "attributed_source": "industrial"},
    )
    print(result.answer)
    print("Citations:", result.citations)

    print("\n--- Q: how does the enforcement queue decide priority? ---")
    result = agent.answer("how does the enforcement queue decide what to inspect first")
    print(result.answer)
    print("Citations:", result.citations)

    print("\n--- Q: unrelated question, should fall back gracefully ---")
    result = agent.answer("what's the best pizza topping")
    print(result.answer)