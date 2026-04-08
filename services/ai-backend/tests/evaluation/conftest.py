"""Fixtures for evaluation tests: citation accuracy, grounding, and refusal."""

from __future__ import annotations

import pytest


@pytest.fixture
def aviation_markdown_with_clauses():
    """Aviation document markdown with explicit clause-numbered headings."""
    return """\
# Doc 4444 — Procedures for Air Navigation Services

## Chapter 4 — Separation Methods and Minima

### 4.6 Vertical Separation

#### 4.6.1 Application

Vertical separation shall be obtained by requiring aircraft using prescribed
altimeter setting procedures to operate at different levels expressed in terms
of flight levels or altitudes as specified in Annex 2.

#### 4.6.1.2 Vertical Separation Minimum

The vertical separation minimum (VSM) shall be:
- A nominal 300 m (1000 ft) below FL 410;
- A nominal 600 m (2000 ft) at or above FL 410.

In designated RVSM airspace, a VSM of 300 m (1000 ft) shall be applied
between FL 290 and FL 410 inclusive.

### 4.7 Horizontal Separation

#### 4.7.1 Lateral Separation

Lateral separation shall be applied so that the distance between those
portions of the intended routes for which lateral separation is provided
is never less than an applicable minimum as specified in 4.7.1.1.

## ENR 1.1 General Rules

### ENR 1.1.1 Applicability

These rules apply to all aircraft operating within the FIR.
See also Part-SERA and AMC SERA.3101 for additional requirements.

### ENR 1.1.2 VFR Flight Requirements

VFR flights shall comply with visual flight rules as per Annex 2
and regional supplementary procedures in Doc 7030.

## AD 2.EGLL Aerodrome Data

### AD 2.EGLL.1 Aerodrome Reference Point

The aerodrome reference point is located at coordinates
51°28'39"N 000°27'41"W, elevation 83 ft AMSL.

### AD 2.EGLL.2 Runway Information

Runway 27L: length 3902 m, width 50 m, surface asphalt.
Runway 27R: length 3660 m, width 50 m, surface asphalt.
"""


@pytest.fixture
def sample_eval_metadata():
    """Metadata for evaluation test document."""
    return {
        "doc_name": "ICAO Doc 4444 PANS-ATM",
        "doc_type": "ICAO_DOC",
        "aerodrome_icao": "GLOBAL",
        "effective_date": "2024-11-07",
    }


@pytest.fixture
def chunked_aviation_doc(aviation_markdown_with_clauses, sample_eval_metadata):
    """Pre-chunked aviation document with clause identifiers."""
    from app.ingest.chunker import chunk_markdown

    return chunk_markdown(
        aviation_markdown_with_clauses,
        sample_eval_metadata,
        target_tokens=150,
        min_tokens=30,
    )


@pytest.fixture
def mock_reranked_chunks():
    """Mock reranked results with varying scores for threshold testing."""
    return [
        {
            "chunk_id": "doc1_0",
            "chunk_text": "The vertical separation minimum shall be 1000 ft below FL 410.",
            "score": 0.92,
            "rerank_score": 0.85,
            "doc_name": "ICAO Doc 4444",
            "doc_type": "ICAO_DOC",
            "section_path": "4.6 > 4.6.1.2",
            "clause_id": "4.6.1.2",
            "page_number": 45,
            "aerodrome_icao": "GLOBAL",
            "clause_references": ["FL 410", "Annex 2"],
        },
        {
            "chunk_id": "doc1_1",
            "chunk_text": "Lateral separation shall be applied.",
            "score": 0.65,
            "rerank_score": 0.45,
            "doc_name": "ICAO Doc 4444",
            "doc_type": "ICAO_DOC",
            "section_path": "4.7 > 4.7.1",
            "clause_id": "4.7.1",
            "page_number": 50,
            "aerodrome_icao": "GLOBAL",
            "clause_references": [],
        },
        {
            "chunk_id": "doc2_0",
            "chunk_text": "Something vaguely related.",
            "score": 0.20,
            "rerank_score": 0.05,
            "doc_name": "Other doc",
            "doc_type": "AIP",
            "section_path": "",
            "clause_id": "",
            "page_number": None,
            "aerodrome_icao": "GLOBAL",
            "clause_references": [],
        },
    ]


@pytest.fixture
def out_of_scope_queries():
    """Queries that should trigger refusal."""
    return [
        "What is the weather in Paris?",
        "Tell me a joke about pilots",
        "How do I bake a cake?",
        "What is the capital of France?",
        "Help me write an email to my boss",
    ]


@pytest.fixture
def in_scope_queries():
    """Queries that should trigger document retrieval."""
    return [
        "What is the vertical separation minimum below FL410?",
        "What are the EGLL ILS minima?",
        "Explain the SMS requirements from Doc 4444",
        "What does ENR 1.1 say about VFR flights?",
        "What is the runway length for 27L at Heathrow?",
    ]
