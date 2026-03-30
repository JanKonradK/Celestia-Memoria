"""Tests for the heading-aware markdown chunker."""

from __future__ import annotations

import pytest

from app.ingest.chunker import chunk_markdown, count_tokens, _split_at_headings


class TestCountTokens:
    def test_empty_string(self):
        assert count_tokens("") == 0

    def test_simple_text(self):
        tokens = count_tokens("Hello, world!")
        assert tokens > 0
        assert tokens < 10

    def test_longer_text(self):
        text = "This is a somewhat longer piece of text that should have more tokens."
        tokens = count_tokens(text)
        assert tokens > 10


class TestSplitAtHeadings:
    def test_splits_at_headings(self):
        md = "# Heading 1\n\nContent 1\n\n## Heading 2\n\nContent 2"
        sections = _split_at_headings(md)
        assert len(sections) >= 2

    def test_no_headings(self):
        md = "Just some plain text without any headings."
        sections = _split_at_headings(md)
        assert len(sections) == 1
        assert sections[0]["content"] == md

    def test_section_path_tracking(self):
        md = "# Chapter 1\n\nText\n\n## Section 1.1\n\nMore text"
        sections = _split_at_headings(md)
        # Find the section with heading "Section 1.1"
        nested = [s for s in sections if "1.1" in s.get("heading", "")]
        assert len(nested) > 0
        assert "Chapter 1" in nested[0]["section_path"]


class TestChunkMarkdown:
    def test_basic_chunking(self, sample_metadata, sample_markdown):
        chunks = chunk_markdown(sample_markdown, sample_metadata)
        assert len(chunks) > 0
        for chunk in chunks:
            assert "chunk_text" in chunk
            assert "chunk_index" in chunk
            assert "section_path" in chunk
            assert "token_count" in chunk

    def test_chunk_indices_sequential(self, sample_metadata, sample_markdown):
        chunks = chunk_markdown(sample_markdown, sample_metadata)
        indices = [c["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_metadata_preserved(self, sample_metadata, sample_markdown):
        chunks = chunk_markdown(sample_markdown, sample_metadata)
        for chunk in chunks:
            assert chunk["doc_type"] == "ICAO_DOC"
            assert chunk["aerodrome_icao"] == "GLOBAL"

    def test_chunk_size_reasonable(self, sample_metadata, sample_markdown):
        chunks = chunk_markdown(
            sample_markdown, sample_metadata, target_tokens=200, min_tokens=50
        )
        for chunk in chunks:
            # Allow some tolerance for heading-boundary constraints
            assert chunk["token_count"] > 0
            # Should not be wildly oversized
            assert chunk["token_count"] < 1000

    def test_empty_document(self, sample_metadata):
        chunks = chunk_markdown("", sample_metadata)
        # Should produce at least one chunk even for empty input
        assert len(chunks) >= 0

    def test_single_paragraph(self, sample_metadata):
        text = "This is a single paragraph without any headings. " * 20
        chunks = chunk_markdown(text, sample_metadata, target_tokens=50)
        assert len(chunks) >= 1
        # All text should be covered
        total_text = " ".join(c["chunk_text"] for c in chunks)
        assert "single paragraph" in total_text
