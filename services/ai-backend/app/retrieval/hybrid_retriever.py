"""Hybrid dense+sparse retrieval with filtering and deduplication."""

from __future__ import annotations

import logging

from app.config import get_settings
from app.ingest.embedder import embed_query, embedding_to_bytes
from app.retrieval.reranker import rerank

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Retrieves relevant document chunks using hybrid dense+sparse search."""

    def __init__(self):
        self._settings = get_settings()

    async def retrieve(
        self,
        query: str,
        aerodrome: str = "GLOBAL",
        doc_type_filter: str | None = None,
        alpha: float = 0.6,
        top_k: int = 20,
        rerank_top_n: int | None = None,
    ) -> list[dict]:
        """Execute hybrid retrieval with reranking.

        Args:
            query: The search query text.
            aerodrome: ICAO code to filter by (also includes GLOBAL results).
            doc_type_filter: Optional document type filter.
            alpha: Dense vs sparse weighting (0.6 = 60% dense).
            top_k: Initial retrieval count before reranking.
            rerank_top_n: Final count after reranking.

        Returns:
            List of reranked result dicts with chunk text and metadata.
        """
        if self._settings.USE_LOCAL_MODE:
            results = await self._retrieve_local(
                query, aerodrome, doc_type_filter, top_k
            )
        else:
            results = await self._retrieve_pinecone(
                query, aerodrome, doc_type_filter, alpha, top_k
            )

        # Deduplicate by chunk_id
        seen = set()
        deduped = []
        for r in results:
            chunk_id = r.get("chunk_id") or r.get("id", "")
            if chunk_id not in seen:
                seen.add(chunk_id)
                deduped.append(r)

        # Rerank
        reranked = rerank(query, deduped, top_n=rerank_top_n)

        logger.info(
            "Hybrid retrieval: %d initial -> %d deduped -> %d reranked (aerodrome=%s)",
            len(results),
            len(deduped),
            len(reranked),
            aerodrome,
        )
        return reranked

    async def _retrieve_pinecone(
        self,
        query: str,
        aerodrome: str,
        doc_type_filter: str | None,
        alpha: float,
        top_k: int,
    ) -> list[dict]:
        """Retrieve from Pinecone using hybrid search."""
        from app.retrieval.pinecone_client import query_hybrid
        from app.retrieval.bm25_encoder import get_encoder

        # Embed query
        dense_vector = embed_query(query)

        # BM25 encode query
        bm25 = get_encoder()
        sparse_vectors = bm25.encode_queries([query])
        sparse_vector = sparse_vectors[0]

        # Build filter
        filter_dict: dict = {"is_current": {"$eq": True}}
        if doc_type_filter:
            filter_dict["doc_type"] = {"$eq": doc_type_filter}

        # Query both aerodrome-specific and GLOBAL namespaces
        namespaces = [aerodrome]
        if aerodrome != "GLOBAL":
            namespaces.append("GLOBAL")

        all_results = []
        for ns in namespaces:
            results = query_hybrid(
                dense_vector=dense_vector,
                sparse_vector=sparse_vector,
                namespace=ns,
                filter_dict=filter_dict,
                top_k=top_k,
                alpha=alpha,
            )
            for r in results:
                meta = r.get("metadata", {})
                all_results.append({
                    "chunk_id": r["id"],
                    "chunk_text": meta.get("chunk_text", ""),
                    "score": r["score"],
                    "document_id": meta.get("document_id", ""),
                    "doc_name": meta.get("doc_name", ""),
                    "doc_type": meta.get("doc_type", ""),
                    "section_path": meta.get("section_path", ""),
                    "page_number": meta.get("page_number"),
                    "aerodrome_icao": meta.get("aerodrome_icao", "GLOBAL"),
                })

        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:top_k]

    async def _retrieve_local(
        self,
        query: str,
        aerodrome: str,
        doc_type_filter: str | None,
        top_k: int,
    ) -> list[dict]:
        """Retrieve from local SQLite vector store."""
        from app.db.local_client import search_vectors

        query_embedding = embed_query(query)
        query_bytes = embedding_to_bytes(query_embedding)

        results = await search_vectors(
            query_embedding=query_bytes,
            aerodrome=aerodrome,
            top_k=top_k,
        )

        # Apply doc_type filter if specified
        if doc_type_filter:
            results = [r for r in results if r.get("doc_type") == doc_type_filter]

        return [
            {
                "chunk_id": r.get("chunk_id", ""),
                "chunk_text": r.get("chunk_text", ""),
                "score": r.get("score", 0),
                "document_id": r.get("document_id", ""),
                "doc_name": r.get("doc_name", ""),
                "doc_type": r.get("doc_type", ""),
                "section_path": r.get("section_path", ""),
                "page_number": r.get("page_number"),
                "aerodrome_icao": r.get("aerodrome_icao", "GLOBAL"),
            }
            for r in results
        ]


_retriever: HybridRetriever | None = None


def get_retriever() -> HybridRetriever:
    """Get the singleton HybridRetriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever
