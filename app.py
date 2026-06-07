"""
Milestone 5 — Gradio query interface for The Unofficial Guide.

Run:
    python app.py
Then open http://localhost:7860

The UI shows the grounded answer, the source document(s) it drew from, and the
retrieved chunks with their distance scores (so a viewer can see the system is
actually retrieving, not making things up).
"""
from __future__ import annotations

import gradio as gr

import config
from generator import ask

EXAMPLES = [
    "What tactics help with imposter syndrome in grad school?",
    'In a single-author paper, should I write "I" or "we"?',
    "What free software is recommended for drawing figures in papers?",
    "Does a PhD from a top-ranked university matter for an academic career?",
    "How do I negotiate a higher PhD stipend with my department?",
]


def handle_query(question: str):
    question = (question or "").strip()
    if not question:
        return "Please enter a question.", "", ""

    result = ask(question)

    answer = result["answer"]
    if result["sources"]:
        sources = "\n".join(f"• {s}" for s in result["sources"])
    else:
        sources = "(no sources — the guide could not answer from its documents)"

    # Show the retrieved evidence + distance scores for transparency.
    retrieved = "\n\n".join(
        f"[{i}] distance={c['distance']} — {c['title']}\n{c['text'][:300]}"
        f"{'...' if len(c['text']) > 300 else ''}"
        for i, c in enumerate(result["chunks"], 1)
    )
    return answer, sources, retrieved


with gr.Blocks(title=config.APP_TITLE) as demo:
    gr.Markdown(f"# {config.APP_TITLE}")
    gr.Markdown(
        "Ask a plain-language question. Answers come **only** from real "
        "Academia Stack Exchange threads — if the guide doesn't have the "
        "information, it will say so instead of guessing."
    )

    inp = gr.Textbox(label="Your question", placeholder="e.g. How do I deal with a difficult advisor?")
    btn = gr.Button("Ask", variant="primary")
    answer = gr.Textbox(label="Answer", lines=8)
    sources = gr.Textbox(label="Sources (drawn from)", lines=4)
    retrieved = gr.Textbox(label="Retrieved chunks (with distance scores)", lines=10)

    gr.Examples(examples=EXAMPLES, inputs=inp)

    btn.click(handle_query, inputs=inp, outputs=[answer, sources, retrieved])
    inp.submit(handle_query, inputs=inp, outputs=[answer, sources, retrieved])


if __name__ == "__main__":
    demo.launch(server_port=config.APP_PORT)
