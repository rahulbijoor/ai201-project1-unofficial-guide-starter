"""
Milestone 3 — Document ingestion + chunking for The Unofficial Guide.

Two jobs:
  1. load_documents() — read the .md Q&A threads in documents/, pull out their
     source metadata (title + URL), and return clean body text ready for chunking.
  2. chunk_text()    — split each document with a recursive character splitter
     (~900 chars, ~120 overlap) that prefers answer/paragraph boundaries so a
     chunk holds one coherent piece of advice instead of blending two answers.

Run directly to load, chunk, and INSPECT the output:
    python ingest.py
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

DOCS_DIR = Path(__file__).parent / "documents"

# Chunking parameters (see planning.md -> Chunking Strategy).
CHUNK_SIZE = 900
CHUNK_OVERLAP = 120
# Tried in priority order: answer headers first, then paragraphs, lines,
# sentences, words, and finally a hard character cut as a last resort.
SEPARATORS = ["\n## ", "\n\n", "\n", ". ", " ", ""]


@dataclass
class Document:
    """One loaded source document plus the metadata every chunk inherits."""
    doc_id: str          # filename stem, e.g. "how-to-...-imposter-syndrome"
    title: str
    url: str
    text: str            # cleaned body, ready for chunking


@dataclass
class Chunk:
    """A single retrievable piece of text with its source attribution."""
    text: str
    doc_id: str
    title: str
    url: str
    index: int = 0       # position of this chunk within its document
    metadata: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# 1. LOAD
# --------------------------------------------------------------------------- #
def _parse_header(raw: str) -> tuple[str, str]:
    """Extract title (from '# ...') and 'URL: ...' line written by the collector."""
    title_match = re.search(r"^#\s+(.*)", raw, flags=re.M)
    url_match = re.search(r"^URL:\s*(\S+)", raw, flags=re.M)
    title = title_match.group(1).strip() if title_match else "(untitled)"
    url = url_match.group(1).strip() if url_match else ""
    return title, url


def _clean_body(raw: str) -> str:
    """
    Light preprocessing: drop the leading metadata block (title/Source/URL/Tags/
    score lines) since that isn't advice content, and normalize whitespace.
    The HTML was already stripped when the documents were collected.
    """
    # Normalize Unicode "smart" punctuation to plain ASCII (avoids display
    # glitches and helps keyword matching). Not HTML entities -- real chars.
    for fancy, plain in {
        "’": "'", "‘": "'", "“": '"', "”": '"',
        "–": "-", "—": "-", "…": "...", " ": " ",
    }.items():
        raw = raw.replace(fancy, plain)
    # Remove the metadata lines the collector wrote at the top of each file.
    body = re.sub(r"^Source:.*$", "", raw, flags=re.M)
    body = re.sub(r"^URL:.*$", "", body, flags=re.M)
    body = re.sub(r"^Tags:.*$", "", body, flags=re.M)
    body = re.sub(r"^Question score:.*$", "", body, flags=re.M)
    # Drop the top-level '# Title' line (kept as metadata instead).
    body = re.sub(r"^#\s+.*$", "", body, count=1, flags=re.M)
    body = re.sub(r"[ \t]+\n", "\n", body)       # trailing spaces
    body = re.sub(r"\n{3,}", "\n\n", body)       # collapse blank runs
    return body.strip()


def load_documents(docs_dir: Path = DOCS_DIR) -> list[Document]:
    """Load every .md file in docs_dir into a Document with metadata + clean text."""
    docs: list[Document] = []
    for path in sorted(docs_dir.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        title, url = _parse_header(raw)
        text = _clean_body(raw)
        if not text:
            continue
        docs.append(Document(doc_id=path.stem, title=title, url=url, text=text))
    return docs


# --------------------------------------------------------------------------- #
# 2. CHUNK  (recursive character splitter)
# --------------------------------------------------------------------------- #
def _split_recursive(text: str, separators: list[str]) -> list[str]:
    """
    Split text into pieces no larger than CHUNK_SIZE by trying separators in
    priority order. If a piece is still too big with the current separator,
    recurse into it using the next (finer) separator.
    """
    if len(text) <= CHUNK_SIZE:
        return [text]

    sep, *rest = separators
    # Last-resort separator "" -> hard-cut into CHUNK_SIZE slices.
    if sep == "":
        return [text[i:i + CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]

    pieces: list[str] = []
    for part in text.split(sep):
        if not part.strip():
            continue
        if len(part) > CHUNK_SIZE:
            pieces.extend(_split_recursive(part, rest))
        else:
            pieces.append(part)
    return pieces


def _merge_with_overlap(pieces: list[str]) -> list[str]:
    """
    Greedily merge small adjacent pieces up to ~CHUNK_SIZE, then carry the last
    ~CHUNK_OVERLAP characters into the next chunk to preserve continuity.
    """
    chunks: list[str] = []
    current = ""
    for piece in pieces:
        if not current:
            current = piece
        elif len(current) + len(piece) + 2 <= CHUNK_SIZE:
            current = f"{current}\n\n{piece}"
        else:
            chunks.append(current.strip())
            overlap = current[-CHUNK_OVERLAP:] if CHUNK_OVERLAP else ""
            current = (overlap + "\n\n" + piece).strip() if overlap else piece
    if current.strip():
        chunks.append(current.strip())
    return chunks


def chunk_text(text: str) -> list[str]:
    """Public chunker: recursive split, then merge with overlap."""
    pieces = _split_recursive(text, SEPARATORS)
    return _merge_with_overlap(pieces)


def chunk_documents(docs: list[Document]) -> list[Chunk]:
    """Turn loaded documents into Chunk objects carrying source metadata."""
    chunks: list[Chunk] = []
    for doc in docs:
        for i, piece in enumerate(chunk_text(doc.text)):
            chunks.append(
                Chunk(
                    text=piece,
                    doc_id=doc.doc_id,
                    title=doc.title,
                    url=doc.url,
                    index=i,
                    metadata={"title": doc.title, "url": doc.url,
                              "doc_id": doc.doc_id, "chunk_index": i},
                )
            )
    return chunks


# --------------------------------------------------------------------------- #
# 3. INSPECT  (don't skip this step)
# --------------------------------------------------------------------------- #
def _inspect(docs: list[Document], chunks: list[Chunk]) -> None:
    sizes = [len(c.text) for c in chunks]
    print(f"Loaded {len(docs)} documents -> {len(chunks)} chunks")
    if sizes:
        print(f"Chunk size  : min={min(sizes)}  max={max(sizes)}  "
              f"avg={sum(sizes)//len(sizes)}  (target ~{CHUNK_SIZE})")
    over = [s for s in sizes if s > CHUNK_SIZE]
    print(f"Chunks over target: {len(over)}")
    # 5 representative chunks spread across the corpus (not all from one doc),
    # so we can judge whether each makes sense on its own.
    step = max(1, len(chunks) // 5)
    sample = [chunks[i] for i in range(0, len(chunks), step)][:5]
    print("\n--- 5 representative chunks (read each: does it stand alone?) ---")
    for c in sample:
        print(f"\n[{c.doc_id} #{c.index}]  ({len(c.text)} chars)  src: {c.url}")
        print(c.text)
        print("-" * 70)


if __name__ == "__main__":
    documents = load_documents()
    all_chunks = chunk_documents(documents)
    _inspect(documents, all_chunks)
