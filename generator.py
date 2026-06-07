"""
Milestone 5 — Grounded answer generation for The Unofficial Guide.

Flow:
    ask(question)
      -> retriever.search()            (top-k chunks + distances)
      -> if nothing clears the relevance threshold: decline (no hallucination)
      -> else build a context block and call Groq with a STRICT grounding prompt
      -> return {answer, sources, chunks, grounded}

Grounding is enforced two ways:
  1. The system prompt forbids using outside knowledge and requires a fixed
     refusal phrase when the context is insufficient.
  2. Source attribution is added PROGRAMMATICALLY from the retrieved chunks --
     it never depends on the LLM choosing to cite.

Usage:
    python generator.py        # run a few end-to-end test queries
"""
from __future__ import annotations

from groq import Groq

import config
import retriever

SYSTEM_PROMPT = """You are The Unofficial Guide, answering questions about \
surviving grad school using ONLY the numbered source excerpts provided by the \
user.

Rules you must follow:
- Use ONLY information contained in the provided sources. Do NOT use any outside \
or general knowledge, even if you are confident it is correct.
- If the sources do not contain enough information to answer, reply with EXACTLY \
this sentence and nothing else: "{no_info}"
- When you do answer, cite the sources you used inline using their numbers, like \
[1] or [2].
- Do not invent sources, facts, names, or numbers that are not in the excerpts.
- Be concise and practical. If sources disagree, present the differing views \
rather than picking one as definitive.""".format(no_info=config.NO_INFO_MESSAGE)

USER_TEMPLATE = """Question: {question}

Sources:
{context}

Answer the question using only the sources above, following all the rules."""


def _client() -> Groq:
    if not config.GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to your .env file."
        )
    return Groq(api_key=config.GROQ_API_KEY)


def _format_context(chunks: list[dict]) -> str:
    blocks = []
    for i, c in enumerate(chunks, 1):
        blocks.append(f"[{i}] (from \"{c['title']}\")\n{c['text']}")
    return "\n\n".join(blocks)


def _source_list(chunks: list[dict]) -> list[str]:
    """De-duplicated, ordered list of source documents used as context."""
    seen, sources = set(), []
    for c in chunks:
        key = c["url"] or c["title"]
        if key in seen:
            continue
        seen.add(key)
        label = c["title"]
        if c["url"]:
            label = f"{label} ({c['url']})"
        sources.append(label)
    return sources


def ask(question: str, k: int | None = None) -> dict:
    """
    Answer `question` grounded in retrieved chunks.

    Returns dict: {answer, sources, chunks, grounded}
      grounded=False means we declined because nothing was relevant enough.
    """
    k = k or config.TOP_K
    chunks = retriever.search(question, k=k)

    # Relevance gate: if even the best chunk is too far, refuse rather than
    # let the LLM improvise from training knowledge.
    best = chunks[0]["distance"] if chunks else 1.0
    if not chunks or best > config.DISTANCE_THRESHOLD:
        return {
            "answer": config.NO_INFO_MESSAGE,
            "sources": [],
            "chunks": chunks,
            "grounded": False,
        }

    context = _format_context(chunks)
    resp = _client().chat.completions.create(
        model=config.LLM_MODEL,
        temperature=config.TEMPERATURE,
        max_tokens=config.MAX_TOKENS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",
             "content": USER_TEMPLATE.format(question=question, context=context)},
        ],
    )
    answer = resp.choices[0].message.content.strip()

    # If the model itself decided the context was insufficient, surface no
    # sources (the answer isn't actually drawn from them).
    declined = answer.strip().rstrip(".") == config.NO_INFO_MESSAGE.rstrip(".")
    return {
        "answer": answer,
        "sources": [] if declined else _source_list(chunks),
        "chunks": chunks,
        "grounded": not declined,
    }


if __name__ == "__main__":
    tests = [
        "What tactics help with imposter syndrome in grad school?",
        'In a single-author paper, should I write "I" or "we"?',
        "How do I negotiate a higher PhD stipend with my department?",  # out-of-corpus
    ]
    for q in tests:
        print("\n" + "=" * 78)
        print("Q:", q)
        print("=" * 78)
        r = ask(q)
        print("\nANSWER:\n", r["answer"])
        print("\nGROUNDED:", r["grounded"])
        print("SOURCES:")
        for s in r["sources"]:
            print("  -", s)
