"""Tests for clause extraction, citation parsing, and chunk metadata accuracy."""

from __future__ import annotations

import pytest

from app.agents.nodes.synthesis_node import SOURCE_PATTERN, _parse_sources
from app.ingest.clause_extractor import (
    build_enriched_section_path,
    extract_clause_id,
    extract_clause_references,
)

# ---------------------------------------------------------------------------
# Clause extraction from headings
# ---------------------------------------------------------------------------


class TestClauseExtraction:
    """Test extract_clause_id against aviation heading patterns."""

    def test_numbered_section(self):
        assert extract_clause_id("4.6.1.2 Application of Vertical Separation") == "4.6.1.2"

    def test_two_level_number(self):
        assert extract_clause_id("3.1 Vertical Separation") == "3.1"

    def test_enr_section(self):
        assert extract_clause_id("ENR 1.1 General Rules") == "ENR 1.1"

    def test_enr_deep_section(self):
        assert extract_clause_id("ENR 1.1.2 VFR Flight Requirements") == "ENR 1.1.2"

    def test_ad_section(self):
        assert extract_clause_id("AD 2.EGLL Aerodrome Data") == "AD 2.EGLL"

    def test_gen_section(self):
        assert extract_clause_id("GEN 3.1.2 Meteorological Services") == "GEN 3.1.2"

    def test_annex_reference(self):
        assert extract_clause_id("Annex 11 Air Traffic Services") == "Annex 11"

    def test_annex_14(self):
        assert extract_clause_id("Annex 14 Aerodromes") == "Annex 14"

    def test_doc_reference(self):
        assert extract_clause_id("Doc 4444 Procedures") == "Doc 4444"

    def test_easa_part(self):
        assert extract_clause_id("Part-OPS Requirements") == "Part-OPS"

    def test_easa_amc(self):
        assert extract_clause_id("AMC FCL.010 Definitions") == "AMC FCL.010"

    def test_no_clause_in_generic_heading(self):
        assert extract_clause_id("General Provisions") is None

    def test_no_clause_in_prose_heading(self):
        assert extract_clause_id("Introduction and Background") is None

    def test_empty_heading(self):
        assert extract_clause_id("") is None

    def test_none_heading(self):
        assert extract_clause_id(None) is None


class TestClauseReferences:
    """Test extract_clause_references for body text scanning."""

    def test_multiple_references(self):
        text = "as per 3.1.2 and Annex 14, see also Doc 4444"
        refs = extract_clause_references(text)
        assert "3.1.2" in refs
        assert "Annex 14" in refs
        assert "Doc 4444" in refs

    def test_enr_reference_in_body(self):
        refs = extract_clause_references("Refer to ENR 1.1 for general rules")
        assert "ENR 1.1" in refs

    def test_no_references(self):
        assert extract_clause_references("No clause numbers here.") == []

    def test_empty_text(self):
        assert extract_clause_references("") == []

    def test_deduplicated(self):
        text = "See 4.6.1 and then again 4.6.1 for details"
        refs = extract_clause_references(text)
        assert refs.count("4.6.1") == 1


class TestEnrichedSectionPath:
    """Test build_enriched_section_path prefers clause IDs."""

    def test_with_clause_ids(self):
        stack = [
            ("Chapter 4 — Separation", None),
            ("4.6 Vertical Separation", "4.6"),
            ("4.6.1.2 Application", "4.6.1.2"),
        ]
        path = build_enriched_section_path(stack)
        assert path == "Chapter 4 — Separation > 4.6 > 4.6.1.2"

    def test_without_clause_ids(self):
        stack = [("General", None), ("Background", None)]
        path = build_enriched_section_path(stack)
        assert path == "General > Background"

    def test_mixed(self):
        stack = [("Overview", None), ("3.1 Methods", "3.1")]
        path = build_enriched_section_path(stack)
        assert path == "Overview > 3.1"


# ---------------------------------------------------------------------------
# Source citation parsing from synthesis responses
# ---------------------------------------------------------------------------


class TestSourceParsing:
    """Test _parse_sources with new [Source N, clause] format."""

    def _make_chunks(self, n: int) -> list[dict]:
        return [
            {
                "doc_name": f"Doc {i}",
                "doc_type": "ICAO_DOC",
                "section_path": f"Section {i}",
                "page_number": i * 10,
                "chunk_text": f"Chunk text {i}" * 20,
                "aerodrome_icao": "GLOBAL",
                "clause_id": f"{i}.1.{i}",
            }
            for i in range(1, n + 1)
        ]

    def test_new_format_with_clause(self):
        chunks = self._make_chunks(3)
        text = "The VSM is 1000 ft [Source 1, 4.6.1.2] and lateral [Source 2, 4.7.1]."
        sources = _parse_sources(text, chunks)
        assert len(sources) == 2
        assert sources[0]["cited_clause"] == "4.6.1.2"
        assert sources[1]["cited_clause"] == "4.7.1"

    def test_old_format_still_works(self):
        chunks = self._make_chunks(2)
        text = "The VSM is 1000 ft [Source 1] and lateral [Source 2]."
        sources = _parse_sources(text, chunks)
        assert len(sources) == 2
        assert sources[0]["cited_clause"] == ""
        assert sources[1]["cited_clause"] == ""

    def test_mixed_format(self):
        chunks = self._make_chunks(3)
        text = "VSM [Source 1, 4.6.1.2] and general info [Source 3]."
        sources = _parse_sources(text, chunks)
        assert len(sources) == 2
        assert sources[0]["cited_clause"] == "4.6.1.2"
        assert sources[1]["cited_clause"] == ""

    def test_no_phantom_sources(self):
        chunks = self._make_chunks(2)
        text = "VSM [Source 1] and [Source 5] does not exist."
        sources = _parse_sources(text, chunks)
        assert len(sources) == 1
        assert sources[0]["source_index"] == 1

    def test_deduplication(self):
        chunks = self._make_chunks(2)
        text = "Ref [Source 1, 4.6] and again [Source 1, 4.6]."
        sources = _parse_sources(text, chunks)
        assert len(sources) == 1

    def test_clause_id_included(self):
        chunks = self._make_chunks(1)
        text = "Info [Source 1, ENR 1.1]."
        sources = _parse_sources(text, chunks)
        assert sources[0]["clause_id"] == "1.1.1"  # from chunk metadata

    def test_regex_captures_both_groups(self):
        match = SOURCE_PATTERN.search("[Source 2, ENR 1.1]")
        assert match is not None
        assert match.group(1) == "2"
        assert match.group(2) == "ENR 1.1"

    def test_regex_captures_without_clause(self):
        match = SOURCE_PATTERN.search("[Source 3]")
        assert match is not None
        assert match.group(1) == "3"
        assert match.group(2) is None


# ---------------------------------------------------------------------------
# Chunk clause metadata from the chunker
# ---------------------------------------------------------------------------


@pytest.mark.evaluation
class TestChunkClauseMetadata:
    """Verify chunks produced from aviation markdown carry clause metadata."""

    def test_chunks_have_clause_id(self, chunked_aviation_doc):
        clause_chunks = [c for c in chunked_aviation_doc if c.get("clause_id")]
        assert len(clause_chunks) > 0, "No chunks have clause_id set"

    def test_specific_clause_found(self, chunked_aviation_doc):
        clause_ids = [c.get("clause_id", "") for c in chunked_aviation_doc]
        # The fixture has "4.6.1.2 Vertical Separation Minimum" heading
        assert any("4.6" in cid for cid in clause_ids if cid), (
            f"Expected clause containing '4.6' in {clause_ids}"
        )

    def test_section_path_includes_clause(self, chunked_aviation_doc):
        paths = [c.get("section_path", "") for c in chunked_aviation_doc]
        assert any("4.6" in p for p in paths), (
            f"Expected '4.6' in section paths: {paths}"
        )

    def test_clause_references_populated(self, chunked_aviation_doc):
        all_refs = []
        for c in chunked_aviation_doc:
            all_refs.extend(c.get("clause_references", []))
        assert len(all_refs) > 0, "No clause_references found in any chunk"

    def test_enr_clause_extracted(self, chunked_aviation_doc):
        clause_ids = [c.get("clause_id", "") for c in chunked_aviation_doc]
        assert any("ENR" in cid for cid in clause_ids if cid), (
            f"Expected ENR clause in {clause_ids}"
        )

    def test_ad_clause_extracted(self, chunked_aviation_doc):
        clause_ids = [c.get("clause_id", "") for c in chunked_aviation_doc]
        assert any("AD" in cid for cid in clause_ids if cid), (
            f"Expected AD clause in {clause_ids}"
        )
