"""
Sanity checks for the ingestion + chunking pipeline (Milestone 3).

These verify the pipeline isn't BROKEN (every doc loads, chunks carry their
source, no HTML leftovers, sizes within bounds). They do NOT judge whether the
chunks are semantically useful -- that's what retrieval testing in Milestone 4
is for.

Run anytime, e.g. after changing CHUNK_SIZE / CHUNK_OVERLAP:
    python test_ingest.py
"""
import re

import ingest

EXPECTED_DOCS = 14


def main() -> None:
    docs = ingest.load_documents()
    chunks = ingest.chunk_documents(docs)

    checks = [
        (len(docs) == EXPECTED_DOCS,
         f"expected {EXPECTED_DOCS} docs, got {len(docs)}"),
        (50 <= len(chunks) <= 2000,
         f"chunk count {len(chunks)} outside healthy 50-2000 range"),
        (all(c.url.startswith("http") for c in chunks),
         "a chunk lost its source URL (breaks citations)"),
        (all(c.text.strip() for c in chunks),
         "empty chunk found"),
        (all(len(c.text) <= ingest.CHUNK_SIZE + ingest.CHUNK_OVERLAP
             for c in chunks),
         "a chunk exceeds CHUNK_SIZE + CHUNK_OVERLAP"),
        (not any(re.search(r"<[a-z/][^>]*>|&[a-z]+;", c.text) for c in chunks),
         "HTML tag or entity left in a chunk (cleaning unfinished)"),
        (not any(re.search(r"[‘’“”–—…]", c.text) for c in chunks),
         "smart/Unicode punctuation not normalized"),
        (len({c.doc_id for c in chunks}) == len(docs),
         "a document produced zero chunks"),
        (all(c.metadata.get("url") and c.metadata.get("title") for c in chunks),
         "a chunk is missing title/url metadata"),
    ]

    failed = [msg for ok, msg in checks if not ok]
    if failed:
        for msg in failed:
            print("FAIL:", msg)
        raise SystemExit(1)

    sizes = [len(c.text) for c in chunks]
    print("ALL CHECKS PASSED")
    print(f"{len(docs)} docs -> {len(chunks)} chunks | "
          f"size min={min(sizes)} max={max(sizes)} avg={sum(sizes)//len(sizes)}")


if __name__ == "__main__":
    main()
