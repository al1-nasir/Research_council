"""
Embedding pipeline — embed text chunks with MiniLM and store in ChromaDB.

All embedding runs on **CPU only** to preserve VRAM.
Batched encoding for performance (never one-at-a-time).
"""

from __future__ import annotations

import logging
from typing import Optional

import chromadb
from sentence_transformers import SentenceTransformer

from config import CHROMA_PERSIST_DIR, EMBEDDING_MODEL
from ingestion.chunker import TextChunk

logger = logging.getLogger(__name__)

# ── Singleton embedder (lazy init) ───────────────────────────────────────────
_embedder: Optional[SentenceTransformer] = None


def get_embedder() -> SentenceTransformer:
    """Return the shared SentenceTransformer instance (CPU only)."""
    global _embedder
    if _embedder is None:
        logger.info("Loading embedding model '%s' on CPU …", EMBEDDING_MODEL)
        _embedder = SentenceTransformer(EMBEDDING_MODEL, device="cpu")  # Force CPU — GPU too old
    return _embedder


# ── ChromaDB client (lazy init) ──────────────────────────────────────────────
_chroma_client: Optional[chromadb.PersistentClient] = None


def get_chroma_client() -> chromadb.PersistentClient:
    """Return the persistent ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        logger.info("Initializing ChromaDB at %s", CHROMA_PERSIST_DIR)
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))
    return _chroma_client


def get_or_create_collection(name: str = "papers_embeddings") -> chromadb.Collection:
    """Get or create a ChromaDB collection."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


# ── Public API ────────────────────────────────────────────────────────────────


def embed_texts(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """
    Embed a list of texts using MiniLM on CPU.

    Always batched — never call in a per-item loop.
    Returns list of 384-dim float vectors.
    """
    embedder = get_embedder()
    embeddings = embedder.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=len(texts) > 100,
        convert_to_numpy=True,
    )
    return embeddings.tolist()


def store_chunks(
    chunks: list[TextChunk],
    collection_name: str = "papers_embeddings",
    batch_size: int = 32,
) -> int:
    """
    Embed and store a list of TextChunks into ChromaDB.

    Returns the number of chunks stored.
    """
    if not chunks:
        return 0

    collection = get_or_create_collection(collection_name)

    texts = [c.text for c in chunks]
    ids = [f"{c.source_id}__chunk_{c.chunk_index}" for c in chunks]
    metadatas = [
        {
            "source_id": c.source_id,
            "chunk_index": c.chunk_index,
            "start_token": c.start_token,
            "end_token": c.end_token,
        }
        for c in chunks
    ]

    # Batch embed
    embeddings = embed_texts(texts, batch_size=batch_size)

    # Upsert into ChromaDB
    collection.upsert(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    logger.info("Stored %d chunks in collection '%s'", len(chunks), collection_name)
    return len(chunks)


def query_similar(
    query_text: str,
    collection_name: str = "papers_embeddings",
    n_results: int = 10,
) -> dict:
    """
    Embed *query_text* and return the top-k most similar chunks from ChromaDB.

    Returns ChromaDB query result dict with keys: ids, documents, metadatas, distances.
    """
    collection = get_or_create_collection(collection_name)
    query_embedding = embed_texts([query_text])[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, 10),  # cap at 10 per performance rule
    )
    return results
