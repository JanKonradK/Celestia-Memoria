"""Text embedding with structured metadata prefixes for aviation documents."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING

import numpy as np

from app.config import get_settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def _build_prefix(metadata: dict) -> str:
    """Build a structured prefix to prepend to chunk text before embedding.

    Format: [DOC:<doc_type>|ICAO:<aerodrome>|SECTION:<section>|EFFECTIVE:<date>]

    This improves embedding quality for domain-specific retrieval by encoding
    structural metadata directly into the embedding input.
    """
    doc_type = metadata.get("doc_type", "UNKNOWN")
    aerodrome = metadata.get("aerodrome_icao", "GLOBAL")
    section = metadata.get("section_path", "")
    effective = metadata.get("effective_date", "")

    parts = [f"DOC:{doc_type}", f"ICAO:{aerodrome}"]
    if section:
        parts.append(f"SECTION:{section}")
    if effective:
        parts.append(f"EFFECTIVE:{effective}")

    return f"[{'|'.join(parts)}] "


@lru_cache
def _get_openai_embeddings():
    """Get OpenAI embeddings model routed through OpenRouter."""
    from langchain_openai import OpenAIEmbeddings

    settings = get_settings()
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=settings.OPENROUTER_API_KEY,
        openai_api_base=settings.OPENROUTER_BASE_URL,
    )


@lru_cache
def _get_local_embeddings():
    """Get local sentence-transformers model for development mode."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2")
    return model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts using the configured embedding model.

    In production mode: uses text-embedding-3-small via OpenRouter.
    In local mode: uses sentence-transformers all-MiniLM-L6-v2.
    """
    settings = get_settings()

    if settings.USE_LOCAL_MODE:
        model = _get_local_embeddings()
        embeddings = model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()
    else:
        embeddings_model = _get_openai_embeddings()
        return embeddings_model.embed_documents(texts)


def embed_query(text: str) -> list[float]:
    """Embed a single query text."""
    settings = get_settings()

    if settings.USE_LOCAL_MODE:
        model = _get_local_embeddings()
        embedding = model.encode([text], show_progress_bar=False)
        return embedding[0].tolist()
    else:
        embeddings_model = _get_openai_embeddings()
        return embeddings_model.embed_query(text)


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Embed a list of chunks, prepending structured metadata prefixes.

    Modifies each chunk dict in-place by adding an 'embedding' key
    containing the float vector, and returns the list.
    """
    prefixed_texts = []
    for chunk in chunks:
        prefix = _build_prefix(chunk)
        prefixed_texts.append(prefix + chunk["chunk_text"])

    logger.info("Embedding %d chunks...", len(prefixed_texts))

    # Batch in groups of 100 to avoid API limits
    batch_size = 100
    all_embeddings: list[list[float]] = []

    for i in range(0, len(prefixed_texts), batch_size):
        batch = prefixed_texts[i : i + batch_size]
        batch_embeddings = embed_texts(batch)
        all_embeddings.extend(batch_embeddings)

    for chunk, embedding in zip(chunks, all_embeddings):
        chunk["embedding"] = embedding

    logger.info("Embedded %d chunks successfully", len(chunks))
    return chunks


def embedding_to_bytes(embedding: list[float]) -> bytes:
    """Convert a float embedding to bytes for local storage."""
    return np.array(embedding, dtype=np.float32).tobytes()


def bytes_to_embedding(data: bytes) -> list[float]:
    """Convert bytes back to a float embedding."""
    return np.frombuffer(data, dtype=np.float32).tolist()
