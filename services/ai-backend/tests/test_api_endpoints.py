"""Tests for API endpoints using FastAPI TestClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    """Create a test client with local mode enabled."""
    app = create_app()
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["mode"] == "local"
        assert "version" in data

    def test_health_no_auth_required(self, client):
        """Health endpoint should not require authentication."""
        response = client.get("/health")
        assert response.status_code == 200


class TestIngestEndpoint:
    """Tests for POST /ingest."""

    @patch("app.db.local_client.insert_document_metadata", new_callable=AsyncMock)
    @patch("app.api.routes.ingest.run_pipeline")
    def test_ingest_returns_processing(self, mock_pipeline, mock_insert, client):
        """Admin should be able to trigger ingestion."""
        # run_pipeline is added as a background task; mock it to prevent actual execution
        mock_pipeline.return_value = None

        response = client.post(
            "/ingest",
            json={
                "storage_path": "test/doc.pdf",
                "doc_name": "Test Document",
                "doc_type": "ICAO_DOC",
                "aerodrome_icao": "GLOBAL",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert "document_id" in data

    def test_ingest_rejects_invalid_doc_type(self, client):
        """Should reject invalid document types."""
        response = client.post(
            "/ingest",
            json={
                "storage_path": "test/doc.pdf",
                "doc_name": "Test Document",
                "doc_type": "INVALID_TYPE",
                "aerodrome_icao": "GLOBAL",
            },
        )
        assert response.status_code == 422

    def test_ingest_rejects_invalid_icao(self, client):
        """Should reject invalid ICAO codes."""
        response = client.post(
            "/ingest",
            json={
                "storage_path": "test/doc.pdf",
                "doc_name": "Test Document",
                "doc_type": "ICAO_DOC",
                "aerodrome_icao": "invalid",
            },
        )
        assert response.status_code == 422

    def test_ingest_rejects_path_traversal(self, client):
        """Should reject paths with directory traversal."""
        response = client.post(
            "/ingest",
            json={
                "storage_path": "../../../etc/passwd",
                "doc_name": "Test Document",
                "doc_type": "ICAO_DOC",
            },
        )
        assert response.status_code == 422

    def test_ingest_rejects_empty_doc_name(self, client):
        """Should reject empty document names."""
        response = client.post(
            "/ingest",
            json={
                "storage_path": "test/doc.pdf",
                "doc_name": "",
                "doc_type": "ICAO_DOC",
            },
        )
        assert response.status_code == 422


class TestQueryEndpoint:
    """Tests for POST /query."""

    @patch("app.api.routes.query.get_graph")
    def test_query_returns_answer(self, mock_graph, client):
        """Should return an answer from the agent graph."""
        graph = AsyncMock()
        graph.ainvoke.return_value = {
            "final_response": "The minimum separation is 5 NM.",
            "sources": [
                {
                    "source_index": 1,
                    "doc_name": "ICAO Doc 4444",
                    "doc_type": "ICAO_DOC",
                    "section_path": "Chapter 8",
                    "page_number": 85,
                    "aerodrome_icao": "GLOBAL",
                    "clause_id": "8.7.3.1",
                    "cited_clause": "8.7.3.1",
                }
            ],
            "intent": "regulatory_query",
            "node_trace": ["router", "retrieval", "synthesis"],
        }
        mock_graph.return_value = graph

        response = client.post(
            "/query",
            json={"message": "What is the minimum radar separation?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["sources"]) == 1
        assert data["intent"] == "regulatory_query"

    def test_query_rejects_empty_message(self, client):
        """Should reject empty messages."""
        response = client.post(
            "/query",
            json={"message": ""},
        )
        assert response.status_code == 422

    def test_query_rejects_invalid_icao(self, client):
        """Should reject invalid ICAO codes."""
        response = client.post(
            "/query",
            json={"message": "test", "aerodrome_icao": "invalid"},
        )
        assert response.status_code == 422
