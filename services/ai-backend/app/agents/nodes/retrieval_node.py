"""Retrieval node: fetches relevant document chunks using hybrid search."""

from __future__ import annotations

import logging

from app.agents.state import AgentState
from app.retrieval.hybrid_retriever import get_retriever

logger = logging.getLogger(__name__)


async def retrieval_node(state: AgentState) -> dict:
    """Retrieve relevant document chunks for the rewritten query.

    Uses the HybridRetriever to perform dense+sparse search, then reranks
    results using Cohere (production) or score-based ranking (local).
    """
    query = state.get("query_rewrite", "")
    aerodrome = state.get("aerodrome_icao", "GLOBAL")

    if not query:
        logger.warning("Retrieval node called with empty query")
        return {
            "retrieved_chunks": [],
            "reranked_chunks": [],
            "node_trace": state.get("node_trace", []) + ["retrieval"],
        }

    retriever = get_retriever()

    try:
        reranked = await retriever.retrieve(
            query=query,
            aerodrome=aerodrome,
        )

        # Store both the full retrieval and reranked results
        logger.info(
            "Retrieval: %d reranked chunks for aerodrome=%s",
            len(reranked),
            aerodrome,
        )

        return {
            "retrieved_chunks": reranked,  # All results before reranking filter
            "reranked_chunks": reranked,
            "node_trace": state.get("node_trace", []) + ["retrieval"],
        }

    except Exception as e:
        logger.exception("Retrieval failed: %s", e)
        return {
            "retrieved_chunks": [],
            "reranked_chunks": [],
            "node_trace": state.get("node_trace", []) + ["retrieval"],
        }
