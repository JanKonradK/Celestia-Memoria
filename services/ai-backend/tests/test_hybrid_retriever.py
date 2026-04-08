"""Tests for hybrid retriever deduplication and filtering logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from app.retrieval.hybrid_retriever import HybridRetriever


def _make_result(chunk_id: str, score: float, aerodrome: str = "GLOBAL", **kwargs) -> dict:
    """Helper to create a mock retrieval result."""
    return {
        "chunk_id": chunk_id,
        "chunk_text": f"Content for {chunk_id}",
        "score": score,
        "document_id": "doc-001",
        "doc_name": "Test Doc",
        "doc_type": "ICAO_DOC",
        "section_path": "Chapter 1",
        "page_number": 1,
        "aerodrome_icao": aerodrome,
        "clause_id": "",
        "clause_references": [],
        **kwargs,
    }


class TestDeduplication:
    """Tests for chunk deduplication logic."""

    @patch("app.retrieval.hybrid_retriever.rerank")
    @patch.object(HybridRetriever, "_retrieve_local", new_callable=AsyncMock)
    async def test_deduplicates_by_chunk_id(self, mock_retrieve, mock_rerank):
        """Duplicate chunk_ids should be removed before reranking."""
        mock_retrieve.return_value = [
            _make_result("chunk-1", 0.9),
            _make_result("chunk-1", 0.85),  # duplicate
            _make_result("chunk-2", 0.8),
        ]
        mock_rerank.side_effect = lambda q, results, top_n: results

        retriever = HybridRetriever()
        await retriever.retrieve("test query")

        # Rerank should receive only 2 unique results
        call_args = mock_rerank.call_args
        deduped = call_args[0][1]  # second positional arg
        assert len(deduped) == 2

    @patch("app.retrieval.hybrid_retriever.rerank")
    @patch.object(HybridRetriever, "_retrieve_local", new_callable=AsyncMock)
    async def test_keeps_first_occurrence(self, mock_retrieve, mock_rerank):
        """Dedup should keep the first (higher-scored) occurrence."""
        mock_retrieve.return_value = [
            _make_result("chunk-1", 0.9),
            _make_result("chunk-1", 0.5),
        ]
        mock_rerank.side_effect = lambda q, results, top_n: results

        retriever = HybridRetriever()
        await retriever.retrieve("test query")

        call_args = mock_rerank.call_args
        deduped = call_args[0][1]
        assert len(deduped) == 1
        assert deduped[0]["score"] == 0.9


class TestEmptyResults:
    """Tests for edge cases with empty results."""

    @patch("app.retrieval.hybrid_retriever.rerank")
    @patch.object(HybridRetriever, "_retrieve_local", new_callable=AsyncMock)
    async def test_empty_results(self, mock_retrieve, mock_rerank):
        """Should handle empty retrieval results gracefully."""
        mock_retrieve.return_value = []
        mock_rerank.return_value = []

        retriever = HybridRetriever()
        results = await retriever.retrieve("test query")

        assert results == []


class TestDocTypeFilter:
    """Tests for document type filtering in local retrieval."""

    @patch("app.retrieval.hybrid_retriever.rerank")
    @patch("app.retrieval.hybrid_retriever.embed_query")
    @patch("app.retrieval.hybrid_retriever.embedding_to_bytes")
    @patch("app.db.local_client.search_vectors", new_callable=AsyncMock)
    async def test_filters_by_doc_type(self, mock_search, mock_bytes, mock_embed, mock_rerank):
        """Local retrieval should filter by doc_type when specified."""
        mock_embed.return_value = [0.1] * 384
        mock_bytes.return_value = b"\x00" * 1536
        mock_search.return_value = [
            {"chunk_id": "c1", "chunk_text": "text", "score": 0.9, "doc_type": "ICAO_DOC",
             "document_id": "d1", "doc_name": "n", "section_path": "s", "page_number": 1,
             "aerodrome_icao": "GLOBAL", "clause_id": "", "clause_references": "[]"},
            {"chunk_id": "c2", "chunk_text": "text", "score": 0.8, "doc_type": "EASA_REG",
             "document_id": "d2", "doc_name": "n", "section_path": "s", "page_number": 1,
             "aerodrome_icao": "GLOBAL", "clause_id": "", "clause_references": "[]"},
        ]
        mock_rerank.side_effect = lambda q, results, top_n: results

        retriever = HybridRetriever()
        await retriever.retrieve("test", doc_type_filter="ICAO_DOC")

        # After dedup+rerank, the EASA_REG result should be filtered out
        call_args = mock_rerank.call_args
        passed_results = call_args[0][1]
        assert all(r["doc_type"] == "ICAO_DOC" for r in passed_results)
