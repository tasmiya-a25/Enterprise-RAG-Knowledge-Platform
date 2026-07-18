"""
Answer generation.

Pluggable by design:
- If an OPENAI_API_KEY is configured, uses GPT for real generative answers.
- Otherwise falls back to a deterministic *extractive* synthesizer that
  returns the most relevant sentences from the retrieved chunks. This keeps
  the whole platform runnable and demoable with zero external API keys,
  while making it obvious exactly where to plug in a real LLM.
"""
import re

from app.config.settings import get_settings
from app.rag.prompts.templates import build_qa_prompt

settings = get_settings()


def _extractive_answer(question: str, chunks: list[dict]) -> str:
    """No-LLM fallback: pick the sentences from the top chunks most relevant
    to the question via simple lexical overlap, and stitch them into an
    answer with inline [source:N] tags. Deterministic and fully local."""
    if not chunks:
        return ("I don't have enough information in the uploaded documents to answer that. "
                "Try uploading a document that covers this topic.")

    question_terms = set(re.findall(r"[a-z0-9]+", question.lower()))
    scored_sentences = []
    for i, chunk in enumerate(chunks, start=1):
        for sentence in re.split(r"(?<=[.!?])\s+", chunk["content"]):
            terms = set(re.findall(r"[a-z0-9]+", sentence.lower()))
            overlap = len(terms & question_terms)
            if overlap > 0 and len(sentence.strip()) > 20:
                scored_sentences.append((overlap, i, sentence.strip()))

    if not scored_sentences:
        top = chunks[0]
        return f"Based on the most relevant excerpt found: {top['content'][:400].strip()} [source:1]"

    scored_sentences.sort(key=lambda x: x[0], reverse=True)
    best = scored_sentences[:4]
    best.sort(key=lambda x: x[1])  # restore document order for readability

    parts = [f"{sentence} [source:{idx}]" for _, idx, sentence in best]
    return (
        "Here's what the uploaded documents say (extractive summary -- connect an "
        "OPENAI_API_KEY for a fully generative answer): " + " ".join(parts)
    )


def _openai_answer(question: str, chunks: list[dict], history: list[dict]) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    prompt = build_qa_prompt(question, chunks, history)
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return response.choices[0].message.content


def generate_answer(question: str, chunks: list[dict], history: list[dict]) -> str:
    use_openai = settings.LLM_PROVIDER == "openai" or (
        settings.LLM_PROVIDER == "auto" and bool(settings.OPENAI_API_KEY)
    )
    if use_openai:
        return _openai_answer(question, chunks, history)
    return _extractive_answer(question, chunks)
