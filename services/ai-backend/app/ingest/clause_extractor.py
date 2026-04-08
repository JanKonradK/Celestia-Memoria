"""Extract structured clause identifiers from aviation document headings and body text.

Aviation regulatory documents use several distinct numbering patterns:
- Numbered sections: "4.6.1.2", "3.1.1"
- AIP section codes: "ENR 1.1", "AD 2.EGLL", "GEN 3.1.2"
- ICAO Doc references: "Doc 4444", "Doc 7030"
- Annex references: "Annex 11", "Annex 14"
- EASA references: "Part-OPS", "AMC FCL.010", "GM CAT.OP.MPA"
- Chapter/Section composites: "Chapter 4, Section 6"
"""

from __future__ import annotations

import re

# --- Clause ID patterns (applied to headings) ---
# Order matters: more specific patterns first

# AIP section codes: ENR 1.1, AD 2.EGLL, GEN 3.1.2
_AIP_PATTERN = re.compile(
    r"((?:ENR|AD|GEN)\s+\d+(?:\.\d+)*(?:\.[A-Z]{4})?)"
)

# EASA references: Part-OPS, AMC FCL.010, GM CAT.OP.MPA
_EASA_PATTERN = re.compile(
    r"((?:Part-|AMC\s+|GM\s+)\S+)"
)

# ICAO Doc references: Doc 4444, Doc 7030
_DOC_PATTERN = re.compile(r"(Doc\s+\d{4})")

# Annex references: Annex 11, Annex 14
_ANNEX_PATTERN = re.compile(r"(Annex\s+\d+)")

# Numbered sections: 4.6.1.2, 3.1.1 (must have at least one dot)
_NUMBERED_PATTERN = re.compile(r"(?<!\w)((\d+\.)+\d+)(?!\w)")

# Chapter/Section composite: Chapter 4, Section 6
_CHAPTER_PATTERN = re.compile(
    r"(Chapter\s+\d+(?:[.,]\s*Section\s+\d+)?)", re.IGNORECASE
)

# Ordered list of (pattern, group_index) for heading extraction
_HEADING_PATTERNS = [
    (_AIP_PATTERN, 1),
    (_EASA_PATTERN, 1),
    (_DOC_PATTERN, 1),
    (_ANNEX_PATTERN, 1),
    (_NUMBERED_PATTERN, 1),
    (_CHAPTER_PATTERN, 1),
]

# --- Body text reference patterns (broader, captures all mentions) ---
_BODY_PATTERNS = [
    _AIP_PATTERN,
    _EASA_PATTERN,
    _DOC_PATTERN,
    _ANNEX_PATTERN,
    _NUMBERED_PATTERN,
    _CHAPTER_PATTERN,
]


def extract_clause_id(heading: str) -> str | None:
    """Extract the primary clause identifier from a heading string.

    Examples:
        "4.6.1.2 Application of Vertical Separation" → "4.6.1.2"
        "ENR 1.1 General Rules" → "ENR 1.1"
        "AD 2.EGLL Aerodrome Data" → "AD 2.EGLL"
        "Annex 14 Aerodromes" → "Annex 14"
        "General Provisions" → None

    Returns:
        The clause identifier string, or None if no structured identifier found.
    """
    if not heading or not heading.strip():
        return None

    for pattern, group in _HEADING_PATTERNS:
        match = pattern.search(heading)
        if match:
            return match.group(group).strip()

    return None


def extract_clause_references(text: str) -> list[str]:
    """Extract all clause references mentioned in body text.

    Scans for all aviation clause/section patterns and returns a
    deduplicated list of references found.

    Examples:
        "as per 3.1.2 and Annex 14" → ["3.1.2", "Annex 14"]
        "see ENR 1.1 and Doc 4444 Section 4.6" → ["ENR 1.1", "Doc 4444", "4.6"]
    """
    if not text:
        return []

    refs: list[str] = []
    seen: set[str] = set()

    for pattern in _BODY_PATTERNS:
        for match in pattern.finditer(text):
            ref = match.group(1).strip()
            if ref not in seen:
                seen.add(ref)
                refs.append(ref)

    return refs


def build_enriched_section_path(
    heading_stack: list[tuple[str, str | None]],
) -> str:
    """Build a section path preferring clause IDs over raw heading text.

    Args:
        heading_stack: List of (heading_text, clause_id_or_none) tuples
            representing the current heading hierarchy.

    Returns:
        A " > " joined path, e.g. "Doc 4444 > Chapter 4 > 4.6 > 4.6.1.2"
    """
    parts = [clause_id if clause_id else text for text, clause_id in heading_stack]
    return " > ".join(parts)
