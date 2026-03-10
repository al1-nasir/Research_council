"""
Research Council — shared configuration.

Loads .env once, exposes typed settings used by every sub-package.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(_PROJECT_ROOT / ".env")

# Paths
DATA_DIR = _PROJECT_ROOT / "data"
RAW_PAPERS_DIR = DATA_DIR / "raw_papers"
CHUNKS_DIR = DATA_DIR / "chunks"
CONCLUSIONS_DIR = DATA_DIR / "conclusions"
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(DATA_DIR / "chroma_db"))

# Ensure directories exist
for _d in (RAW_PAPERS_DIR, CHUNKS_DIR, CONCLUSIONS_DIR, Path(CHROMA_PERSIST_DIR)):
    _d.mkdir(parents=True, exist_ok=True)

# LLM Providers
GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")
OPENROUTER_API_KEY: str = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

# Neo4j
NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "password")

# Embeddings
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
EMBEDDING_DIM: int = 384  # MiniLM-L6-v2 output dimension

# PubMed / Entrez
ENTREZ_EMAIL: str = os.getenv("ENTREZ_EMAIL", "")

# Semantic Scholar
SEMANTIC_SCHOLAR_API_KEY: str = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")

# Langfuse Observability
LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST: str = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

# Chunking defaults
CHUNK_SIZE_TOKENS: int = 500
CHUNK_OVERLAP_TOKENS: int = 50
