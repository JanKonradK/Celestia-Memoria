"""Document metadata validation and normalization for aviation documents."""

from __future__ import annotations

import re
from datetime import date

VALID_DOC_TYPES = frozenset({
    "AIP",
    "AIP_SUP",
    "UNIT_MANUAL",
    "ICAO_DOC",
    "EASA_REG",
    "PROCEDURE_CHANGE",
    "LOA",
})

ICAO_CODE_PATTERN = re.compile(r"^[A-Z]{4}$")


class MetadataValidationError(ValueError):
    """Raised when document metadata fails validation."""


def validate_icao_code(code: str) -> str:
    """Validate and return an ICAO aerodrome code (4 uppercase letters) or 'GLOBAL'."""
    code = code.strip().upper()
    if code == "GLOBAL":
        return code
    if not ICAO_CODE_PATTERN.match(code):
        raise MetadataValidationError(
            f"Invalid ICAO code '{code}': must be exactly 4 uppercase letters or 'GLOBAL'"
        )
    return code


def validate_doc_type(doc_type: str) -> str:
    """Validate and return a document type."""
    doc_type = doc_type.strip().upper()
    if doc_type not in VALID_DOC_TYPES:
        raise MetadataValidationError(
            f"Invalid doc_type '{doc_type}': must be one of {sorted(VALID_DOC_TYPES)}"
        )
    return doc_type


def validate_date(date_str: str | None) -> str | None:
    """Validate an ISO-format date string. Returns None if input is None/empty."""
    if not date_str:
        return None
    date_str = date_str.strip()
    try:
        parsed = date.fromisoformat(date_str)
        return parsed.isoformat()
    except ValueError as e:
        raise MetadataValidationError(
            f"Invalid date '{date_str}': must be ISO format (YYYY-MM-DD)"
        ) from e


def normalize_metadata(raw: dict) -> dict:
    """Validate and normalize raw document metadata.

    Returns a new dict with validated and normalized fields.
    Raises MetadataValidationError for invalid values.
    """
    normalized = dict(raw)

    if "aerodrome_icao" in normalized:
        normalized["aerodrome_icao"] = validate_icao_code(normalized["aerodrome_icao"])
    else:
        normalized["aerodrome_icao"] = "GLOBAL"

    if "doc_type" in normalized:
        normalized["doc_type"] = validate_doc_type(normalized["doc_type"])
    else:
        raise MetadataValidationError("doc_type is required")

    normalized["effective_date"] = validate_date(normalized.get("effective_date"))
    normalized["expiry_date"] = validate_date(normalized.get("expiry_date"))

    if not normalized.get("doc_name"):
        raise MetadataValidationError("doc_name is required")

    normalized.setdefault("is_current", True)

    return normalized


def infer_metadata_from_path(file_path: str) -> dict:
    """Infer document metadata from the file's location within the data/ directory.

    Directory structure convention:
        data/icao/<file>.pdf     -> ICAO_DOC, GLOBAL
        data/easa/<file>.pdf     -> EASA_REG, GLOBAL
        data/local/<ICAO>/<file> -> AIP, aerodrome from folder name
        data/local/<file>.pdf    -> AIP, GLOBAL
        data/other/<file>.pdf    -> ICAO_DOC, GLOBAL
    """
    from pathlib import Path

    path = Path(file_path)
    parts = path.parts

    # Find the 'data' directory in the path to determine relative position
    try:
        data_idx = list(parts).index("data")
    except ValueError:
        return {
            "doc_name": path.stem,
            "doc_type": "ICAO_DOC",
            "aerodrome_icao": "GLOBAL",
        }

    relative_parts = parts[data_idx + 1 :]

    if not relative_parts:
        return {
            "doc_name": path.stem,
            "doc_type": "ICAO_DOC",
            "aerodrome_icao": "GLOBAL",
        }

    category = relative_parts[0].lower()
    doc_name = path.stem

    if category == "icao":
        return {
            "doc_name": doc_name,
            "doc_type": "ICAO_DOC",
            "aerodrome_icao": "GLOBAL",
        }
    elif category == "easa":
        return {
            "doc_name": doc_name,
            "doc_type": "EASA_REG",
            "aerodrome_icao": "GLOBAL",
        }
    elif category == "local":
        # Check if there's a subfolder that looks like an ICAO code
        if len(relative_parts) >= 3:
            potential_icao = relative_parts[1].upper()
            if ICAO_CODE_PATTERN.match(potential_icao):
                return {
                    "doc_name": doc_name,
                    "doc_type": "AIP",
                    "aerodrome_icao": potential_icao,
                }
        return {
            "doc_name": doc_name,
            "doc_type": "AIP",
            "aerodrome_icao": "GLOBAL",
        }
    else:
        return {
            "doc_name": doc_name,
            "doc_type": "ICAO_DOC",
            "aerodrome_icao": "GLOBAL",
        }
