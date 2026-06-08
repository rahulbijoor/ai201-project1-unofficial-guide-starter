"""
Gradio chat interface for The Unofficial Guide.

Run:
    python app.py
Then open http://localhost:7860
"""
from __future__ import annotations

import os

# Ensure Gradio's localhost self-check isn't routed through a proxy (which
# breaks it and raises "localhost is not accessible" on launch).
os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1,0.0.0.0")
os.environ.setdefault("no_proxy", "localhost,127.0.0.1,0.0.0.0")

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


def handle_chat(message: str, chat_history: list[list]):
    """
    chat_history is a list of [user_msg, assistant_msg] tuples (Gradio default).
    We convert it to OpenAI-style dicts for the LLM.
    """
    message = (message or "").strip()
    if not message:
        yield chat_history, "", ""
        return

    history = []
    for user_msg, assistant_msg in chat_history:
        if user_msg:
            history.append({"role": "user", "content": user_msg})
        if assistant_msg:
            history.append({"role": "assistant", "content": assistant_msg})

    result = ask(message, history=history)

    sources = (
        "\n".join(f"• {s}" for s in result["sources"])
        if result["sources"]
        else "(no sources — the guide could not answer from its documents)"
    )
    retrieved = "\n\n".join(
        f"[{i}] distance={c['distance']} — {c['title']}\n{c['text'][:300]}"
        f"{'...' if len(c['text']) > 300 else ''}"
        for i, c in enumerate(result["chunks"], 1)
    )

    chat_history = chat_history + [[message, result["answer"]]]
    yield chat_history, sources, retrieved


with gr.Blocks(title=config.APP_TITLE) as demo:
    gr.Markdown(f"# {config.APP_TITLE}")
    gr.Markdown(
        "Ask a plain-language question about surviving grad school. Answers come "
        "**only** from real Academia Stack Exchange threads — if the guide doesn't "
        "have the information, it says so. You can ask follow-up questions."
    )

    with gr.Row():
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(label="Conversation", height=450)
            with gr.Row():
                inp = gr.Textbox(
                    label="Your question",
                    placeholder="e.g. How do I deal with a difficult advisor?",
                    scale=4,
                )
                send_btn = gr.Button("Ask", variant="primary", scale=1)
            clear_btn = gr.Button("Clear conversation", variant="secondary")
            gr.Examples(examples=EXAMPLES, inputs=inp)

        with gr.Column(scale=2):
            sources_box = gr.Textbox(label="Sources (drawn from)", lines=4)
            retrieved_box = gr.Textbox(
                label="Retrieved chunks (with distance scores)", lines=14
            )

    send_btn.click(
        handle_chat,
        inputs=[inp, chatbot],
        outputs=[chatbot, sources_box, retrieved_box],
    ).then(lambda: "", outputs=inp)

    inp.submit(
        handle_chat,
        inputs=[inp, chatbot],
        outputs=[chatbot, sources_box, retrieved_box],
    ).then(lambda: "", outputs=inp)

    clear_btn.click(
        lambda: ([], "", ""),
        outputs=[chatbot, sources_box, retrieved_box],
    )


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=config.APP_PORT)
