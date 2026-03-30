"""Search result reranking using Cohere (production) or score-based (local)."""

from __future__ import annotations

import logging
from functools import lru_cache

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def _get_cohere_client():
    """Get a Cohere client for reranking."""
    import cohere

    settings = get_settings()
    return cohere.Client(api_key=settings.COHERE_API_KEY)


def rerank(
    query: str,
    results: list[dict],
    top_n: int | None = None,
) -> list[dict]:
    """Rerank search results for relevance to the query.

    In production: uses Cohere rerank-english-v3.0.
    In local mode: simple score-based pass-through (already sorted by score).

    Args:
        query: The user's search query.
        results: List of result dicts, each must have 'chunk_text' and 'score'.
        top_n: Number of results to return after reranking.

    Returns:
        Reranked list of result dicts with updated scores.
    """
    settings = get_settings()

    if top_n is None:
        top_n = settings.COHERE_RERANK_TOP_N

    if not results:
        return []

    if settings.USE_LOCAL_MODE:
        return _rerank_local(results, top_n)

    return _rerank_cohere(query, results, top_n)


def _rerank_cohere(query: str, results: list[dict], top_n: int) -> list[dict]:
    """Rerank using Cohere's reranking model."""
    settings = get_settings()
    client = _get_cohere_client()

    documents = [r.get("chunk_text", "") for r in results]

    response = client.rerank(
        query=query,
        documents=documents,
        model=settings.COHERE_RERANK_MODEL,
        top_n=min(top_n, len(results)),
    )

    reranked = []
    for item in response.results:
        result = dict(results[item.index])
        result["rerank_score"] = item.relevance_score
        reranked.append(result)

    logger.info(
        "Cohere reranked %d -> %d results (top score: %.3f)",
        len(results),
        len(reranked),
        reranked[0]["rerank_score"] if reranked else 0,
    )
    return reranked


def _rerank_local(results: list[dict], top_n: int) -> list[dict]:
    """Simple score-based reranking for local dev mode."""
    sorted_results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
    truncated = sorted_results[:top_n]

    for r in truncated:
        r["rerank_score"] = r.get("score", 0)

    logger.info("Local reranked %d -> %d results", len(results), len(truncated))
    return truncated
