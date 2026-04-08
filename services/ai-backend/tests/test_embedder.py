"""Tests for text embedding and prefix construction."""

from __future__ import annotations

import pytest

from app.ingest.embedder import _build_prefix, embed_chunks, embed_query, embed_texts


class TestBuildPrefix:
    """Tests for structured metadata prefix construction."""

    def test_basic_prefix(self):
        meta = {
            "doc_type": "ICAO_DOC",
            "aerodrome_icao": "GLOBAL",
        }
        prefix = _build_prefix(meta)
        assert "[DOC:ICAO_DOC|ICAO:GLOBAL]" in prefix

    def test_prefix_with_clause(self):
        meta = {
            "doc_type": "EASA_REG",
            "aerodrome_icao": "EGLL",
            "clause_id": "5.2.1",
        }
        prefix = _build_prefix(meta)
        assert "CLAUSE:5.2.1" in prefix

    def test_prefix_with_section(self):
        meta = {
            "doc_type": "AIP",
            "aerodrome_icao": "GLOBAL",
            "section_path": "Chapter 3 > Separation",
        }
        prefix = _build_prefix(meta)
        assert "SECTION:Chapter 3 > Separation" in prefix

    def test_prefix_with_effective_date(self):
        meta = {
            "doc_type": "ICAO_DOC",
            "aerodrome_icao": "GLOBAL",
            "effective_date": "2024-01-01",
        }
        prefix = _build_prefix(meta)
        assert "EFFECTIVE:2024-01-01" in prefix

    def test_prefix_missing_fields(self):
        prefix = _build_prefix({})
        assert "[DOC:UNKNOWN|ICAO:GLOBAL]" in prefix

    def test_prefix_ends_with_space(self):
        prefix = _build_prefix({"doc_type": "AIP", "aerodrome_icao": "GLOBAL"})
        assert prefix.endswith("] ")


class TestEmbedTexts:
    """Tests for batch text embedding (local mode)."""

    def test_returns_list_of_vectors(self):
        texts = ["hello world", "aviation safety"]
        embeddings = embed_texts(texts)
        assert len(embeddings) == 2
        assert isinstance(embeddings[0], list)
        assert all(isinstance(v, float) for v in embeddings[0])

    def test_consistent_dimension(self):
        embeddings = embed_texts(["text one", "text two", "text three"])
        dims = [len(e) for e in embeddings]
        assert len(set(dims)) == 1  # all same dimension

    def test_single_text(self):
        embeddings = embed_texts(["single"])
        assert len(embeddings) == 1


class TestEmbedQuery:
    """Tests for single query embedding."""

    def test_returns_single_vector(self):
        embedding = embed_query("What is the minimum radar separation?")
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(v, float) for v in embedding)


class TestEmbedChunks:
    """Tests for embedding chunks with prefix."""

    def test_adds_embedding_to_chunks(self, sample_chunks):
        if not sample_chunks:
            pytest.skip("No chunks generated")

        # Only embed first 2 to keep test fast
        chunks = sample_chunks[:2]
        result = embed_chunks(chunks)
        assert len(result) == len(chunks)
        for chunk in result:
            assert "embedding" in chunk
            assert isinstance(chunk["embedding"], list)

    def test_preserves_chunk_metadata(self, sample_chunks):
        if not sample_chunks:
            pytest.skip("No chunks generated")

        chunks = sample_chunks[:1]
        original_text = chunks[0]["chunk_text"]
        result = embed_chunks(chunks)
        assert result[0]["chunk_text"] == original_text
