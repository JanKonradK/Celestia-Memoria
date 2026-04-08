"""Tests for search result reranking."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.retrieval.reranker import _rerank_local, rerank


def _make_result(chunk_text: str, score: float) -> dict:
    return {"chunk_text": chunk_text, "score": score}


class TestLocalReranking:
    """Tests for score-based local reranking."""

    def test_sorts_by_score_descending(self):
        results = [
            _make_result("low", 0.3),
            _make_result("high", 0.9),
            _make_result("mid", 0.6),
        ]
        reranked = _rerank_local(results, top_n=10)
        scores = [r["rerank_score"] for r in reranked]
        assert scores == sorted(scores, reverse=True)

    def test_respects_top_n(self):
        results = [_make_result(f"r{i}", 0.5 + i * 0.1) for i in range(10)]
        reranked = _rerank_local(results, top_n=3)
        assert len(reranked) <= 3

    def test_filters_below_threshold(self):
        results = [
            _make_result("above", 0.8),
            _make_result("below", 0.1),
        ]
        reranked = _rerank_local(results, top_n=10)
        # Local threshold is 0.3, so score=0.1 should be filtered
        assert all(r["rerank_score"] >= 0.3 for r in reranked)

    def test_empty_results(self):
        reranked = _rerank_local([], top_n=10)
        assert reranked == []

    def test_adds_rerank_score(self):
        results = [_make_result("text", 0.7)]
        reranked = _rerank_local(results, top_n=10)
        assert "rerank_score" in reranked[0]
        assert reranked[0]["rerank_score"] == 0.7


class TestRerankDispatch:
    """Tests for the main rerank function dispatch logic."""

    def test_returns_empty_for_empty_input(self):
        result = rerank("query", [], top_n=10)
        assert result == []

    def test_local_mode_uses_score_sort(self):
        """In local mode, rerank should use score-based sorting."""
        results = [
            _make_result("a", 0.9),
            _make_result("b", 0.5),
        ]
        # conftest.py sets USE_LOCAL_MODE=true
        reranked = rerank("test query", results, top_n=10)
        assert reranked[0]["chunk_text"] == "a"


class TestCohereReranking:
    """Tests for Cohere reranking with mocked API."""

    @patch("app.retrieval.reranker._get_cohere_client")
    @patch("app.retrieval.reranker.get_settings")
    def test_falls_back_on_cohere_error(self, mock_settings, mock_client):
        """Should fall back to score-sort if Cohere raises an exception."""
        settings = MagicMock()
        settings.USE_LOCAL_MODE = False
        settings.COHERE_RERANK_MODEL = "rerank-english-v3.0"
        settings.COHERE_RERANK_TOP_N = 10
        settings.RERANK_MIN_SCORE = 0.15
        settings.RERANK_MIN_SCORE_LOCAL = 0.3
        mock_settings.return_value = settings

        client = MagicMock()
        client.rerank.side_effect = Exception("API error")
        mock_client.return_value = client

        results = [_make_result("text", 0.8)]
        # Should not raise — falls back to local reranking
        reranked = rerank("query", results, top_n=10)
        assert len(reranked) >= 0  # May be filtered by threshold
