"""
Milestone 4 — Embedding + retrieval for The Unofficial Guide.

Pipeline (see planning.md -> Retrieval Approach / Architecture):
    chunks (ingest.py)
      -> embed with all-MiniLM-L6-v2 (sentence-transformers)
      -> store in ChromaDB (local, persistent) with source metadata
      -> search(query, k=4) returns top-k chunks + source + distance

Usage:
    python retriever.py            # build the index (if needed) and run test queries
    python retriever.py --rebuild  # force re-embed from scratch
"""
from __future__ import annotations

import argparse
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

import ingest

EMBED_MODEL = "all-MiniLM-L6-v2"
DB_DIR = str(Path(__file__).parent / "chroma_db")   # persistent on disk
COLLECTION = "unofficial_guide"
DEFAULT_K = 4

# Lazy singletons so importing this module is cheap.
_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)
    return _model


def embed(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts into 384-dim vectors."""
    return get_model().encode(texts, show_progress_bar=False).tolist()


# --------------------------------------------------------------------------- #
# Build the index
# --------------------------------------------------------------------------- #
def build_index(rebuild: bool = False) -> chromadb.Collection:
    """
    Load chunks from the ingestion pipeline, embed them, and store them in a
    persistent ChromaDB collection with source metadata for attribution.
    Skips re-embedding if the collection already holds all chunks.
    """
    client = chromadb.PersistentClient(path=DB_DIR)

    if rebuild:
        try:
            client.delete_collection(COLLECTION)
        except Exception:
            pass

    # cosine distance matches how sentence-transformers embeddings are compared.
    collection = client.get_or_create_collection(
        name=COLLECTION, metadata={"hnsw:space": "cosine"}
    )

    chunks = ingest.chunk_documents(ingest.load_documents())

    if collection.count() == len(chunks) and not rebuild:
        print(f"Index already built ({collection.count()} chunks). "
              f"Use --rebuild to force.")
        return collection

    # Fresh build: clear and re-add so we never end up with stale/dup vectors.
    if collection.count() and not rebuild:
        client.delete_collection(COLLECTION)
        collection = client.get_or_create_collection(
            name=COLLECTION, metadata={"hnsw:space": "cosine"}
        )

    ids = [f"{c.doc_id}::{c.index}" for c in chunks]
    documents = [c.text for c in chunks]
    metadatas = [
        {"title": c.title, "url": c.url,
         "doc_id": c.doc_id, "chunk_index": c.index}
        for c in chunks
    ]

    print(f"Embedding {len(chunks)} chunks with {EMBED_MODEL} ...")
    embeddings = embed(documents)
    collection.add(
        ids=ids, documents=documents,
        metadatas=metadatas, embeddings=embeddings,
    )
    print(f"Stored {collection.count()} chunks in ChromaDB at {DB_DIR}")
    return collection


_collection: chromadb.Collection | None = None


def _get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        _collection = build_index(rebuild=False)
    return _collection


# --------------------------------------------------------------------------- #
# Retrieve
# --------------------------------------------------------------------------- #
def search(query: str, k: int = DEFAULT_K) -> list[dict]:
    """
    Return the top-k chunks most relevant to `query`, each as a dict with:
        text, title, url, doc_id, chunk_index, distance
    Lower distance = closer match (cosine distance, 0 = identical).
    """
    collection = _get_collection()
    q_emb = embed([query])
    res = collection.query(
        query_embeddings=q_emb,
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    results = []
    for text, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        results.append({
            "text": text,
            "title": meta.get("title", ""),
            "url": meta.get("url", ""),
            "doc_id": meta.get("doc_id", ""),
            "chunk_index": meta.get("chunk_index"),
            "distance": round(float(dist), 3),
        })
    return results


# --------------------------------------------------------------------------- #
# Manual retrieval test (Milestone 4 checkpoint)
# --------------------------------------------------------------------------- #
TEST_QUERIES = [
    "What tactics help with imposter syndrome in grad school?",
    'In a single-author paper, should I write "I" or "we"?',
    "What free software is recommended for drawing figures in papers?",
    "Does a PhD from a top-ranked university matter for an academic career?",
    "How do I negotiate a higher PhD stipend with my department?",  # out-of-corpus
]


def run_tests(k: int = DEFAULT_K) -> None:
    for q in TEST_QUERIES:
        print("\n" + "=" * 78)
        print(f"QUERY: {q}")
        print("=" * 78)
        for i, r in enumerate(search(q, k=k), 1):
            flag = "  <-- weak match (>0.5)" if r["distance"] > 0.5 else ""
            print(f"\n[{i}] distance={r['distance']}{flag}")
            print(f"    source: {r['title'][:70]}")
            print(f"    {r['doc_id']} #{r['chunk_index']}")
            preview = r["text"][:300].replace("\n", " ")
            print(f"    {preview}{'...' if len(r['text']) > 300 else ''}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true",
                        help="force re-embed from scratch")
    parser.add_argument("-k", type=int, default=DEFAULT_K,
                        help="number of chunks to retrieve")
    args = parser.parse_args()

    build_index(rebuild=args.rebuild)
    run_tests(k=args.k)
