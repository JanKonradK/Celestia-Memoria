"""Tests for grounding: context formatting, prompt constraints, and relevance filtering."""

from __future__ import annotations

import pytest

from app.agents.nodes.synthesis_node import (
    SYNTHESIS_SYSTEM_PROMPT,
    _build_context,
)
from app.retrieval.reranker import _rerank_local

# ---------------------------------------------------------------------------
# Context formatting
# ---------------------------------------------------------------------------


class TestContextFormat:
    """Verify _build_context includes clause_id and required fields."""

    def test_context_includes_clause_id(self):
        chunks = [
            {
                "doc_name": "Doc 4444",
                "section_path": "4.6 > 4.6.1.2",
                "clause_id": "4.6.1.2",
                "page_number": 45,
                "chunk_text": "The VSM shall be 1000 ft.",
            }
        ]
        context = _build_context(chunks)
        assert "Clause 4.6.1.2" in context

    def test_context_without_clause_id(self):
        chunks = [
            {
                "doc_name": "Some Doc",
                "section_path": "General",
                "clause_id": "",
                "page_number": 10,
                "chunk_text": "General text.",
            }
        ]
        context = _build_context(chunks)
        assert "Clause" not in context
        assert "[Source 1]" in context

    def test_context_includes_all_fields(self):
        chunks = [
            {
                "doc_name": "ICAO Doc 4444",
                "section_path": "Chapter 4 > 4.6",
                "clause_id": "4.6",
                "page_number": 42,
                "chunk_text": "Content here.",
            }
        ]
        context = _build_context(chunks)
        assert "ICAO Doc 4444" in context
        assert "Chapter 4 > 4.6" in context
        assert "p. 42" in context
        assert "Content here." in context

    def test_empty_chunks_context(self):
        context = _build_context([])
        assert "No relevant document sources" in context

    def test_multiple_chunks_separated(self):
        base = {"section_path": "", "clause_id": "", "page_number": None}
        chunks = [
            {"doc_name": "A", "chunk_text": "Text A", **base},
            {"doc_name": "B", "chunk_text": "Text B", **base},
        ]
        context = _build_context(chunks)
        assert "[Source 1]" in context
        assert "[Source 2]" in context
        assert "---" in context


# ---------------------------------------------------------------------------
# Grounding prompt constraints
# ---------------------------------------------------------------------------


class TestGroundingPrompt:
    """Verify the synthesis system prompt enforces strict grounding."""

    def test_prompt_contains_strict_grounding(self):
        assert "ONLY use information from" in SYNTHESIS_SYSTEM_PROMPT

    def test_prompt_forbids_general_knowledge(self):
        assert "Do NOT use your general aviation knowledge" in SYNTHESIS_SYSTEM_PROMPT

    def test_prompt_requires_quote_for_values(self):
        assert "quote the exact source text" in SYNTHESIS_SYSTEM_PROMPT.lower() or \
               "quote the\nexact source text" in SYNTHESIS_SYSTEM_PROMPT.lower() or \
               "exact source text" in SYNTHESIS_SYSTEM_PROMPT

    def test_prompt_no_general_knowledge_fallback(self):
        # The old prompt had "answer based on your general knowledge" — must be gone
        assert "answer based on your general knowledge" not in SYNTHESIS_SYSTEM_PROMPT

    def test_prompt_has_citation_format(self):
        assert "[Source N, <clause>]" in SYNTHESIS_SYSTEM_PROMPT

    def test_prompt_has_out_of_scope(self):
        assert "outside the scope" in SYNTHESIS_SYSTEM_PROMPT

    def test_prompt_has_partial_answer(self):
        assert "partially" in SYNTHESIS_SYSTEM_PROMPT.lower() or \
               "PARTIAL" in SYNTHESIS_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Relevance filtering
# ---------------------------------------------------------------------------


@pytest.mark.evaluation
class TestRelevanceFiltering:
    """Test that the reranker filters low-score results."""

    def test_low_score_chunks_filtered(self, mock_reranked_chunks):
        # Local rerank sorts by score and filters below threshold
        results = _rerank_local(mock_reranked_chunks, top_n=10)
        # The chunk with score 0.20 should be filtered (0.20 < 0.15 * 2 = 0.30)
        scores = [r["rerank_score"] for r in results]
        assert all(s >= 0.30 for s in scores), f"Expected all scores >= 0.30, got {scores}"

    def test_good_results_preserved(self, mock_reranked_chunks):
        results = _rerank_local(mock_reranked_chunks, top_n=10)
        # The top two chunks (0.92, 0.65) should pass
        assert len(results) >= 1

    def test_empty_input(self):
        from app.retrieval.reranker import rerank

        results = rerank("test query", [], top_n=5)
        assert results == []
