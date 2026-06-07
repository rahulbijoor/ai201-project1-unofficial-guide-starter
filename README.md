# The Unofficial Guide — Project 1

A RAG system that answers plain-language questions about **surviving grad school**
using real, student-generated Q&A threads — grounded in retrieved documents and
cited, with an explicit refusal when the answer isn't in the corpus.

**Run it:**
```bash
pip install -r requirements.txt          # deps (sentence-transformers, chromadb, groq, gradio)
# put GROQ_API_KEY=... in a .env file
python ingest.py        # inspect cleaning + chunking
python retriever.py     # build the vector index + retrieval test
python app.py           # launch the web UI at http://localhost:7860
```

---

## Domain

**Surviving grad school & academic life** — the unofficial, student-to-student advice
that helps people actually *get through* a graduate program: handling a difficult
advisor, coping with imposter syndrome and discouragement, beating research
procrastination, navigating academic-integrity situations, making writing/publishing
decisions, and recovering from setbacks.

This knowledge is valuable because it's the *real* curriculum of grad school — the part
that determines whether someone finishes — yet none of it appears in official channels.
Course catalogs and program handbooks cover requirements and deadlines, but never tell
you what to do when your advisor goes silent for months or how others talked themselves
out of quitting. That experience lives in tacit, scattered form on forums, where
community voting surfaces the most-trusted advice.

---

## Document Sources

All documents collected from **Academia Stack Exchange** (CC BY-SA) via the public Stack
Exchange API. Each document is one Q&A thread (question + top-voted answers), saved as a
cleaned `.md` file. The collector script is [documents/_fetch_documents.py](documents/_fetch_documents.py).

| # | Source (thread) | Subtopic | URL |
|---|-----------------|----------|-----|
| 1 | How should I deal with becoming discouraged as a graduate student? | Mental health — discouragement | https://academia.stackexchange.com/questions/2219 |
| 2 | How to effectively deal with Imposter Syndrome and feelings of inadequacy | Mental health — imposter syndrome | https://academia.stackexchange.com/questions/11765 |
| 3 | How to avoid procrastination during the research phase of my PhD? | Productivity / time management | https://academia.stackexchange.com/questions/5786 |
| 4 | First year Math PhD student; my problem-solving skill has atrophied | Coursework struggles / confidence | https://academia.stackexchange.com/questions/162431 |
| 5 | I don't want to kill any more mice, but my advisor insists | Advisor conflict / research ethics | https://academia.stackexchange.com/questions/67897 |
| 6 | Have I embarrassed my supervisors by solving a problem a PhD student couldn't? | Advisor / lab group dynamics | https://academia.stackexchange.com/questions/66820 |
| 7 | What to do when your student is convinced he'll be the next Einstein? | Supervision (advisor's perspective) | https://academia.stackexchange.com/questions/56220 |
| 8 | I was caught cheating on an exam — how can I minimize the damage? | Academic integrity / consequences | https://academia.stackexchange.com/questions/30539 |
| 9 | A student does well on exams but doesn't do the homework | Grading / exams (instructor view) | https://academia.stackexchange.com/questions/58721 |
| 10 | Professor creates assignment making students advocate for a bill | Coursework / ethics / legal | https://academia.stackexchange.com/questions/102950 |
| 11 | Choice of personal pronoun in single-author papers | Academic writing style | https://academia.stackexchange.com/questions/2945 |
| 12 | Software to draw illustrative figures in papers | Writing tools / workflow | https://academia.stackexchange.com/questions/1095 |
| 13 | University rank/stature — how much does it affect a post-PhD career? | Career path / prestige | https://academia.stackexchange.com/questions/90 |
| 14 | Is it possible to recover after a career setback? | Career recovery / resilience | https://academia.stackexchange.com/questions/10381 |

**Ingestion pipeline** ([ingest.py](ingest.py)): load each `.md` → extract title + URL as
metadata → strip the metadata header block, normalize Unicode "smart" punctuation to ASCII,
collapse whitespace (HTML was already removed at collection time) → produce clean body text
ready for chunking.

---

## Chunking Strategy

Recursive character splitting (custom implementation, no extra dependency) with separators
tried in priority order: `["\n## ", "\n\n", "\n", ". ", " ", ""]`. It breaks first at
answer headers, then paragraphs, lines, and sentences — only cutting mid-word as a last
resort. After splitting, small adjacent pieces are merged up to the size cap and the tail
of each chunk is carried into the next as overlap.

**Chunk size:** ~900 characters (cap).

**Overlap:** ~120 characters (~13%).

**Why these choices fit your documents:** The value lives in self-contained pieces of
advice — each answer, often each paragraph. ~900 chars is large enough to hold a full short
answer or a substantive paragraph (so a retrieved chunk is self-contained) but small enough
that a specific query matches precisely. The merge step won't cross a `## Answer` boundary
if doing so would exceed the cap, so one answer ≈ one chunk — which keeps **source
attribution clean**. Overlap preserves continuity when a long answer spans chunks. I
rejected **fixed-size** (would slice mid-sentence and blend two different people's answers)
and **semantic** chunking (extra embedding cost/complexity at ingest for marginal gain,
since the documents are already cleanly segmented by structure).

**Final chunk count:** **208 chunks** across 14 documents (avg 720 chars, min 239, max 985).

---

## Sample Chunks

Five representative chunks, each labeled with its source document:

**1.** `a-student-in-my-course-does-well-on-exams-but-does.md` (chunk #0, 421 chars)
> ## Question — I have a student in my course that does well on the exams, and his answers
> show a deep understanding of the material. However, this student has not been handing in
> the assigned homeworks and has missed a few lab assignments... *(complete question setup —
> stands alone)*

**2.** `first-year-math-phd-student-my-problem-solving-ski.md` (chunk #10, 670 chars)
> ...problems you are encountering might be actually more difficult than problems you
> encountered in your undergrad studies. Your brain is tired. Stress of starting a PhD
> program; from a global pandemic; from knowing you are in a top program and feeling you're
> not up to snuff... Let go of these. *(a complete, standalone piece of advice)*

**3.** `how-to-avoid-procrastination-during-the-research-p.md` (chunk #6, 619 chars)
> ...Answer 3 (score 72): IMHO to keep the pace, the most important thing is not to work
> alone. When I talk about my project on a daily basis it naturally makes me work (as I don't
> want to make others wait)... *(one answer's core point, self-contained)*

**4.** `i-was-caught-cheating-on-an-exam-how-can-i-minimiz.md` (chunk #18, 755 chars)
> ...what I hope for from students in cases like this is genuine introspection. By this I mean
> going beyond a superficial account of rules and motivations... *(coherent advice, readable
> without surrounding context)*

**5.** `software-to-draw-illustrative-figures-in-papers.md` (chunk #4, 495 chars)
> ...TikZ provides an amazing live community which can help you with everything related to it.
> A perfect starting point would be the TeX.se. PS: You can also have a look at pstricks...
> *(a complete tool recommendation)*

Each chunk reads as a complete thought and carries `{title, url, doc_id, chunk_index}`
metadata for citation.

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers` — runs locally (no API key,
no rate limits), fast on CPU, and produces compact 384-dim vectors. A good match for a
14-document English corpus where I want quick iteration. Vectors are stored in a persistent
**ChromaDB** collection using cosine distance.

**Production tradeoff reflection:** For real users I'd weigh:
- **Domain accuracy (highest priority)** — MiniLM is small/general. A larger hosted model
  (Voyage, Cohere Embed, OpenAI `text-embedding-3-large`) would better capture nuance in
  advice-style prose and match paraphrased queries. RAG quality is bottlenecked by
  retrieval, so this matters most.
- **Context length** — MiniLM truncates at 256 tokens, so my ~900-char chunks sit near its
  limit; longer chunks would be silently clipped. A model with an 8k-token window would let
  me embed whole answers/threads.
- **Local vs. API / latency / privacy** — local MiniLM has zero network latency and keeps
  data private; an API model offloads compute and scales but adds latency and a vendor
  dependency.
- **Multilingual** — corpus is English-only now; a multilingual model would be needed if
  international students posted in other languages.
- **Dimensionality / index cost** — bigger models output 1536–3072-dim vectors, raising
  storage and search latency at scale (negligible at 14 docs).

---

## Retrieval Test Results

Retrieval = embed query → cosine similarity in ChromaDB → top-k (k=4). Lower distance =
closer match. ([retriever.py](retriever.py))

**Query 1: "What tactics help with imposter syndrome in grad school?"**
| Rank | Distance | Source chunk |
|---|---|---|
| 1 | **0.178** | imposter-syndrome #1 |
| 2 | 0.270 | imposter-syndrome #0 |
| 3 | 0.290 | imposter-syndrome #4 |
| 4 | 0.335 | imposter-syndrome #5 |

*Why these are relevant:* All four come from the imposter-syndrome thread, the only document
in the corpus on this topic. The top chunk (0.178 — a very close match) contains the question
asker explicitly requesting "actual tactics," and chunks #4/#5 contain the answers listing
concrete tactics (recognize it's documented, look at empirical data, remember even superstars
doubt themselves). Retrieval pulled exactly the chunks needed to answer.

**Query 2: "What free software is recommended for drawing figures in papers?"**
| Rank | Distance | Source chunk |
|---|---|---|
| 1 | **0.309** | figures #0 |
| 2 | 0.426 | figures #2 |
| 3 | 0.530 | figures #3 |
| 4 | 0.531 | figures #1 |

*Why these are relevant:* The top chunk is the question itself ("suggestions of good software
for drawing illustrations"), and #1/#2 are the answer chunks naming the actual tools — Inkscape,
Dia, Graphviz, TikZ. The tool names sit in the strongly-matching chunk #1 (0.309), so even
though chunks 3–4 creep above 0.5, the answer content is well within reach.

**Query 3: "Does a PhD from a top-ranked university matter for an academic career?"**
| Rank | Distance | Source chunk |
|---|---|---|
| 1 | **0.447** | university-rank #0 |
| 2 | 0.458 | university-rank #8 |
| 3 | 0.527 | university-rank #5 |
| 4 | 0.530 | university-rank #1 |

All four come from the correct (university-rank) document, including chunk #8 which holds the
key "tl;dr: top dept helps, but by making you a better researcher" conclusion.

---

## Grounded Generation

Grounding is enforced **two ways** ([generator.py](generator.py)):

**1. A pipeline relevance gate (structural).** Before the LLM is ever called, retrieval runs
and the best chunk's cosine distance is checked against a threshold (`DISTANCE_THRESHOLD =
0.55`, in [config.py](config.py)). This value was tuned from the Milestone 4 results: in-corpus
top hits were ≤0.45, while the out-of-corpus question's best hit was 0.66 — so 0.55 cleanly
separates them. If nothing clears the gate, the system returns a fixed refusal and **never
calls the LLM**, so it cannot improvise from training knowledge.

**2. A strict system prompt (instruction).** The actual instruction given to the model:

> *"You are The Unofficial Guide... Use ONLY information contained in the provided sources. Do
> NOT use any outside or general knowledge, even if you are confident it is correct. If the
> sources do not contain enough information to answer, reply with EXACTLY this sentence: 'I
> don't have enough information on that in my sources.' ... Do not invent sources, facts,
> names, or numbers. If sources disagree, present the differing views rather than picking one
> as definitive."*

The retrieved chunks are passed as numbered, titled excerpts, and temperature is low (0.2).

**How source attribution is surfaced:** Source documents are attached **programmatically**
from the retrieved chunks (de-duplicated title + URL) — it does **not** depend on the LLM
choosing to cite. The model is *also* instructed to use inline `[n]` markers, but the
authoritative source list is built in code, so attribution is guaranteed.

---

## Example Responses

**Example 1 — Imposter syndrome** *(grounded, cited)*
> **Query:** "What tactics help with imposter syndrome in grad school?"
>
> **Answer:** To combat imposter syndrome in grad school, several tactics can be employed...
> knowing that imposter syndrome is a real and documented phenomenon, and that many people,
> including accomplished academics, experience it, can be helpful [4]. Forcing oneself to look
> at empirical data and comparing oneself to others with similar achievements can also be
> beneficial [4]... realizing that one is not alone... [1], [3].
>
> **Sources:** How to effectively deal with Imposter Syndrome and feelings of inadequacy —
> https://academia.stackexchange.com/questions/11765

**Example 2 — "I" vs "we" in single-author papers** *(grounded, cited, presents disagreement)*
> **Query:** "In a single-author paper, should I write \"I\" or \"we\"?"
>
> **Answer:** In a single-author paper, the choice between "I" and "we" varies. According to
> [1] and [3], "we" is a common choice... However, [2] suggests that "I" should be used,
> citing the APA style guide... [4] emphasizes the importance of consistency.
>
> **Sources:** Choice of personal pronoun in single-author papers —
> https://academia.stackexchange.com/questions/2945

**Example 3 — Out-of-scope query** *(refusal)*
> **Query:** "How do I negotiate a higher PhD stipend with my department?"
> **Answer:** I don't have enough information on that in my sources.
> **Sources:** *(none)*

No document covers stipend negotiation; the best retrieved chunk was 0.661 (above the 0.55
gate), so the system declined instead of fabricating advice.

---

## Query Interface

A **Gradio web UI** ([app.py](app.py)) at `http://localhost:7860`.

**Input field:**
- *Your question* — a free-text box (also submits on Enter); clickable example questions
  provided.

**Output fields:**
- *Answer* — the grounded response with inline `[n]` citations.
- *Sources (drawn from)* — bulleted list of the source document(s) + URLs, added programmatically.
- *Retrieved chunks (with distance scores)* — the actual evidence retrieved, so a viewer can
  see the system is grounding rather than guessing.

**Sample interaction transcript:**
```
Your question:  What free software is recommended for drawing figures in papers?

Answer:         For drawing figures in papers, a free software recommended is Inkscape [1],
                which uses SVG as its native file format. Another option is Dia [4], suitable
                for block diagrams and flow charts (a free Visio alternative). Additionally,
                TikZ/PGF [2] and Graphviz [4] can be used, but TikZ/PGF requires specifying
                the diagram in LaTeX and has a steep learning curve.

Sources:        • Software to draw illustrative figures in papers
                  (https://academia.stackexchange.com/questions/1095)

Retrieved:      [1] distance=0.309 — Software to draw illustrative figures in papers ...
                [2] distance=0.426 — ... Answer 2: OmniGraffle / TikZ ...
                [3] distance=0.53  — ... TikZ externalize ...
                [4] distance=0.531 — ... Inkscape / Dia / Graphviz ...
```

---

## Evaluation Report

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | Tactics for imposter syndrome in grad school? | Reinforce what you know; engage non-academics; recognize it's common/documented; look at empirical evidence | Listed: recognize it's documented & common, look at empirical data, remember even superstars doubt themselves | Relevant (top 0.178) | Accurate |
| 2 | Single-author paper: "I" or "we"? | "we" is common in math/sci (author+reader); "I" rare; exceptions exist; be consistent | Presented both views: "we" common [1][3], some prefer "I" per APA [2], consistency matters [4] | Relevant (top 0.228) | Accurate |
| 3 | Free software for drawing figures? | Inkscape, Dia, Graphviz, TikZ/PGF (OmniGraffle paid/Mac) | Named Inkscape, Dia, Graphviz, TikZ/PGF with descriptions | Relevant (top 0.309) | Accurate |
| 4 | Does PhD program rank matter for an academic career? | Helps, but mainly by making you a better researcher; record matters most; pedigree is secondary signal | Said rank helps; cited "makes you a better researcher" and pedigree as secondary signal; noted lower-rank disadvantage | Relevant (top 0.447) | Accurate (see failure note) |
| 5 | How to negotiate a higher PhD stipend? | **Out of corpus — system should refuse** | "I don't have enough information on that in my sources." | Off-target (top 0.661, gated) | Accurate (correct refusal) |

**Retrieval quality:** Relevant / Partially relevant / Off-target
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

**Question that failed:** *"Does a PhD from a top-ranked university matter for an academic
career?"* (Question 4) — a *partial* generation failure, despite correct retrieval.

**What the system returned:** A reasonable answer, but it **under-weighted the source's single
most important point.** The top-voted accepted answer's explicit `tl;dr` is: *"Yes, getting a
PhD from a top department definitely helps, but more by helping you become a better researcher
than by making you look better on paper."* The system mentioned "makes you a better researcher"
in passing but led with and emphasized the *pedigree/secondary-signal* framing, partially
inverting the source's emphasis.

**Root cause (tied to a specific pipeline stage):** Chunking + retrieval ranking. The nuanced
"better researcher, not better on paper" conclusion lives in chunk #8, which retrieved at
**rank 2 (distance 0.458)** — just behind the generic question-restatement chunk #0 (0.447).
Because the strongest-ranked chunk was the *question* rather than the *key conclusion*, the LLM
weighted the supporting/secondary material more heavily. This is exactly the "key information
split across chunk boundaries / not top-ranked" risk flagged in planning.md.

**What you would change to fix it:** (a) Bump `TOP_K` to 5–6 so more of the answer's reasoning
is in context; (b) experiment with slightly larger chunks so the `tl;dr` and its supporting
argument stay together; (c) add a light re-ranking step that down-weights chunks that are just
restatements of the question.

---

## Spec Reflection

**One way the spec helped you during implementation:** Writing the Retrieval Approach and
Anticipated Challenges sections of planning.md *before* coding forced me to define the
distance-threshold refusal mechanism up front. When I later saw in Milestone 4 that the
out-of-corpus query's best distance (0.66) sat well above the in-corpus hits (≤0.45), I already
knew exactly what to do with that gap — set a 0.55 gate — instead of discovering the need for a
refusal mechanism only after the LLM started hallucinating. The spec turned a potential bug into
a planned feature.

**One way your implementation diverged from the spec, and why:** planning.md named LangChain's
`RecursiveCharacterTextSplitter` for chunking, but LangChain isn't in the project's
`requirements.txt`. Rather than add a heavy dependency for one function, I implemented an
equivalent recursive splitter by hand (~40 lines) using the same separators and parameters.
The behavior matches the spec; only the implementation vehicle changed. I updated planning.md to
reflect this.

---

## AI Usage

**Instance 1 — Ingestion + chunking**
- *What I gave the AI:* My planning.md Documents and Chunking Strategy sections, plus the
  Milestone 3 requirements (clean docs, recursive split ~900/120, inspect output).
- *What it produced:* `ingest.py` with `load_documents()`, a recursive `chunk_text()`, and an
  inspection step.
- *What I changed or overrode:* The first draft of the recursive splitter contained dead/buggy
  code (unused `candidate`/`piece` variables and a confused separator re-attachment). I directed
  it to simplify the split function, and I added Unicode "smart punctuation" normalization after
  the chunk inspection surfaced a `'`/`—` artifact that the original cleaning step had missed.

**Instance 2 — Grounded generation**
- *What I gave the AI:* The Architecture diagram, the grounding requirement (answer only from
  retrieved context, programmatic source attribution), and the Groq/`config.py` structure I
  wanted.
- *What it produced:* `generator.py` with `ask()`, a strict system prompt, and Groq wiring.
- *What I changed or overrode:* I insisted that source attribution be built **in code** from the
  retrieved chunks rather than trusting the LLM's inline citations, and that grounding be enforced
  by a **pre-LLM distance gate** (not just a prompt instruction) — so out-of-corpus questions are
  refused before the model is even called. I also pinned temperature to 0.2 to reduce drift from
  the context.
