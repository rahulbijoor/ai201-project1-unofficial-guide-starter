"""
Central configuration for The Unofficial Guide.

Every tunable setting lives here so the model, retrieval depth, and grounding
behaviour can be changed in one place (or overridden via environment variables /
.env without editing code).
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # read .env into the environment

BASE_DIR = Path(__file__).parent


def _get(name: str, default: str) -> str:
    return os.getenv(name, default)


# --- Embedding + vector store (Milestone 4) ------------------------------- #
EMBED_MODEL = _get("EMBED_MODEL", "all-MiniLM-L6-v2")
DB_DIR = _get("DB_DIR", str(BASE_DIR / "chroma_db"))
COLLECTION = _get("COLLECTION", "unofficial_guide")

# --- Retrieval ------------------------------------------------------------- #
TOP_K = int(_get("TOP_K", "4"))
# Cosine distance above this = no chunk is relevant enough to ground an answer.
# Tuned from Milestone 4: in-corpus top hits were <=0.45, the out-of-corpus
# question's best hit was 0.66, so 0.55 cleanly separates them.
DISTANCE_THRESHOLD = float(_get("DISTANCE_THRESHOLD", "0.55"))

# --- Generation (Milestone 5) --------------------------------------------- #
GROQ_API_KEY = _get("GROQ_API_KEY", "")
LLM_MODEL = _get("LLM_MODEL", "llama-3.3-70b-versatile")
TEMPERATURE = float(_get("TEMPERATURE", "0.2"))   # low = stick to the context
MAX_TOKENS = int(_get("MAX_TOKENS", "700"))

# Shown to the user when no retrieved chunk clears DISTANCE_THRESHOLD.
NO_INFO_MESSAGE = (
    "I don't have enough information on that in my sources."
)

# --- UI -------------------------------------------------------------------- #
APP_TITLE = _get("APP_TITLE", "The Unofficial Guide — Grad School Survival")
APP_PORT = int(_get("APP_PORT", "7860"))
