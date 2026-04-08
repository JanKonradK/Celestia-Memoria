"""Tests for document metadata validation and normalization."""

from __future__ import annotations

import pytest

from app.ingest.metadata import (
    MetadataValidationError,
    infer_metadata_from_path,
    normalize_metadata,
    validate_date,
    validate_doc_type,
    validate_icao_code,
)


class TestValidateIcaoCode:
    def test_valid_codes(self):
        assert validate_icao_code("EGLL") == "EGLL"
        assert validate_icao_code("KJFK") == "KJFK"
        assert validate_icao_code("LFPG") == "LFPG"

    def test_global(self):
        assert validate_icao_code("GLOBAL") == "GLOBAL"
        assert validate_icao_code("global") == "GLOBAL"

    def test_lowercase_normalized(self):
        assert validate_icao_code("egll") == "EGLL"

    def test_invalid_length(self):
        with pytest.raises(MetadataValidationError, match="must be exactly 4"):
            validate_icao_code("EG")

    def test_invalid_characters(self):
        with pytest.raises(MetadataValidationError):
            validate_icao_code("EG1L")

    def test_empty(self):
        with pytest.raises(MetadataValidationError):
            validate_icao_code("")

    def test_strips_whitespace(self):
        assert validate_icao_code("  EGLL  ") == "EGLL"


class TestValidateDocType:
    def test_valid_types(self):
        assert validate_doc_type("AIP") == "AIP"
        assert validate_doc_type("ICAO_DOC") == "ICAO_DOC"
        assert validate_doc_type("EASA_REG") == "EASA_REG"
        assert validate_doc_type("LOA") == "LOA"

    def test_case_insensitive(self):
        assert validate_doc_type("aip") == "AIP"
        assert validate_doc_type("icao_doc") == "ICAO_DOC"

    def test_invalid_type(self):
        with pytest.raises(MetadataValidationError, match="must be one of"):
            validate_doc_type("INVALID")


class TestValidateDate:
    def test_valid_date(self):
        assert validate_date("2024-01-15") == "2024-01-15"
        assert validate_date("2025-12-31") == "2025-12-31"

    def test_none(self):
        assert validate_date(None) is None

    def test_empty(self):
        assert validate_date("") is None

    def test_invalid_format(self):
        with pytest.raises(MetadataValidationError, match="ISO format"):
            validate_date("15/01/2024")


class TestNormalizeMetadata:
    def test_valid_metadata(self, sample_metadata):
        result = normalize_metadata(sample_metadata)
        assert result["aerodrome_icao"] == "GLOBAL"
        assert result["doc_type"] == "ICAO_DOC"
        assert result["effective_date"] == "2024-11-07"
        assert result["is_current"] is True

    def test_missing_doc_name(self):
        with pytest.raises(MetadataValidationError, match="doc_name is required"):
            normalize_metadata({"doc_type": "AIP"})

    def test_missing_doc_type(self):
        with pytest.raises(MetadataValidationError, match="doc_type is required"):
            normalize_metadata({"doc_name": "Test"})

    def test_defaults_aerodrome_to_global(self):
        result = normalize_metadata({"doc_name": "Test", "doc_type": "AIP"})
        assert result["aerodrome_icao"] == "GLOBAL"


class TestInferMetadataFromPath:
    def test_icao_directory(self):
        result = infer_metadata_from_path("/some/path/data/icao/doc4444.pdf")
        assert result["doc_type"] == "ICAO_DOC"
        assert result["aerodrome_icao"] == "GLOBAL"
        assert result["doc_name"] == "doc4444"

    def test_easa_directory(self):
        result = infer_metadata_from_path("/data/easa/regulation-2017-373.pdf")
        assert result["doc_type"] == "EASA_REG"
        assert result["aerodrome_icao"] == "GLOBAL"

    def test_local_with_icao_code(self):
        result = infer_metadata_from_path("/data/local/EGLL/unit-manual.pdf")
        assert result["doc_type"] == "AIP"
        assert result["aerodrome_icao"] == "EGLL"

    def test_local_without_icao_code(self):
        result = infer_metadata_from_path("/data/local/national-aip.pdf")
        assert result["doc_type"] == "AIP"
        assert result["aerodrome_icao"] == "GLOBAL"

    def test_other_directory(self):
        result = infer_metadata_from_path("/data/other/misc-doc.pdf")
        assert result["doc_type"] == "ICAO_DOC"
        assert result["aerodrome_icao"] == "GLOBAL"

    def test_no_data_directory(self):
        result = infer_metadata_from_path("/random/path/file.pdf")
        assert result["doc_type"] == "ICAO_DOC"
        assert result["aerodrome_icao"] == "GLOBAL"
