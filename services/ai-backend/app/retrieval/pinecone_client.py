"""Pinecone vector database client for production mode."""

from __future__ import annotations

import logging
from functools import lru_cache

from pinecone import Pinecone

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def _get_client() -> Pinecone:
    settings = get_settings()
    return Pinecone(api_key=settings.PINECONE_API_KEY)


@lru_cache
def get_index():
    """Get the Pinecone index for vector operations."""
    settings = get_settings()
    client = _get_client()
    index = client.Index(settings.PINECONE_INDEX_NAME)
    logger.info("Connected to Pinecone index '%s'", settings.PINECONE_INDEX_NAME)
    return index


def query_hybrid(
    dense_vector: list[float],
    sparse_vector: dict,
    namespace: str = "GLOBAL",
    filter_dict: dict | None = None,
    top_k: int = 20,
    alpha: float = 0.6,
) -> list[dict]:
    """Execute a hybrid dense+sparse query against Pinecone.

    Args:
        dense_vector: Dense embedding vector.
        sparse_vector: Sparse BM25 vector dict with 'indices' and 'values'.
        namespace: Pinecone namespace (typically aerodrome ICAO code).
        filter_dict: Optional metadata filter.
        top_k: Number of results to return.
        alpha: Weight for dense vs sparse (1.0 = all dense, 0.0 = all sparse).

    Returns:
        List of result dicts with 'id', 'score', and 'metadata'.
    """
    index = get_index()

    # Scale vectors by alpha
    scaled_dense = [v * alpha for v in dense_vector]
    scaled_sparse = {
        "indices": sparse_vector["indices"],
        "values": [v * (1 - alpha) for v in sparse_vector["values"]],
    }

    query_params = {
        "vector": scaled_dense,
        "sparse_vector": scaled_sparse,
        "top_k": top_k,
        "include_metadata": True,
        "namespace": namespace,
    }
    if filter_dict:
        query_params["filter"] = filter_dict

    results = index.query(**query_params)

    return [
        {
            "id": match.id,
            "score": match.score,
            "metadata": match.metadata or {},
        }
        for match in results.matches
    ]


def delete_by_document(document_id: str, namespace: str = "GLOBAL") -> None:
    """Delete all vectors for a given document from Pinecone."""
    index = get_index()
    index.delete(
        filter={"document_id": {"$eq": document_id}},
        namespace=namespace,
    )
    logger.info(
        "Deleted vectors for document %s from namespace %s",
        document_id,
        namespace,
    )
