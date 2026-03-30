"""Shared test fixtures and configuration."""

from __future__ import annotations

import os
import pytest

# Force local mode for all tests
os.environ["USE_LOCAL_MODE"] = "true"
os.environ["ENABLE_WATCHER"] = "false"


@pytest.fixture
def sample_metadata():
    """Sample valid document metadata."""
    return {
        "document_id": "test-doc-001",
        "doc_name": "ICAO Doc 4444 PANS-ATM",
        "doc_type": "ICAO_DOC",
        "aerodrome_icao": "GLOBAL",
        "effective_date": "2024-11-07",
        "expiry_date": None,
    }


@pytest.fixture
def sample_markdown():
    """Sample aviation document markdown for chunking tests."""
    return """# Chapter 1 — General Provisions

## 1.1 Definitions

The following terms are used throughout this document:

**Aerodrome control tower.** A unit established to provide air traffic control
service to aerodrome traffic.

**Approach control unit.** A unit established to provide air traffic control
service to controlled flights arriving at, or departing from, one or more
aerodromes.

**Area control centre (ACC).** A unit established to provide air traffic control
service to controlled flights in control areas under its jurisdiction.

## 1.2 Applicability

These procedures are applicable to all air traffic services units providing
service in accordance with the Standards and Recommended Practices (SARPs)
contained in Annex 11 — Air Traffic Services.

The provisions contained herein shall be applied by ATS units in conjunction
with regional supplementary procedures published in ICAO Doc 7030.

# Chapter 2 — ATS Safety Management

## 2.1 Safety Management System (SMS)

An ATS provider shall implement a safety management system (SMS) that, as a
minimum, shall:

a) identify safety hazards;
b) ensure the implementation of remedial action necessary to maintain agreed
   safety performance;
c) provide for continuous monitoring and regular assessment of the safety
   performance; and
d) aim to make continuous improvement to the overall performance of the SMS.

## 2.2 Safety Assessment

A safety assessment shall be conducted for any changes to the ATS system,
including the introduction of new systems, procedures, or changes to airspace
organization.

The safety assessment shall include:
- Hazard identification
- Risk analysis and assessment
- Risk mitigation measures
- Documentation of the assessment

# Chapter 3 — Separation Methods

## 3.1 Vertical Separation

### 3.1.1 Application

Vertical separation shall be obtained by requiring aircraft using prescribed
altimeter setting procedures to operate at different levels expressed in terms
of flight levels or altitudes.

### 3.1.2 Vertical Separation Minimum (VSM)

The vertical separation minimum (VSM) shall be:
- **1000 ft** below FL 410 (or below the transition level where applicable)
- **2000 ft** at or above FL 410 (RVSM airspace: 1000 ft between FL 290 and FL 410)

## 3.2 Horizontal Separation

### 3.2.1 Lateral Separation

Lateral separation shall be applied so that the distance between those portions
of the intended routes for which lateral separation is to be provided is never
less than the applicable minimum.

### 3.2.2 Longitudinal Separation

Longitudinal separation shall be applied so that the spacing between aircraft
on the same, reciprocal, or crossing tracks is never less than a prescribed
minimum, expressed in terms of time or distance.
"""


@pytest.fixture
def sample_chunks(sample_metadata, sample_markdown):
    """Pre-chunked document for embedding/retrieval tests."""
    from app.ingest.chunker import chunk_markdown

    return chunk_markdown(sample_markdown, sample_metadata)
