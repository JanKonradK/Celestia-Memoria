"""Auto-ingestion pipeline for files detected by the directory watcher."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from pathlib import Path

from app.ingest.metadata import infer_metadata_from_path
from app.ingest.pipeline import run_pipeline, generate_document_id

logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).resolve().parent.parent.parent.parent / "data" / ".state.json"


def _load_state() -> dict:
    """Load the ingestion state file tracking already-processed files."""
    if not STATE_FILE.exists():
        return {"ingested_files": {}}
    try:
        return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return {"ingested_files": {}}


def _save_state(state: dict) -> None:
    """Persist the ingestion state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _file_hash(path: str) -> str:
    """Compute SHA-256 hash of a file for change detection."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_already_ingested(file_path: str) -> bool:
    """Check if a file has already been ingested (by path + hash)."""
    state = _load_state()
    stored = state["ingested_files"].get(file_path)
    if stored is None:
        return False
    current_hash = _file_hash(file_path)
    return stored.get("hash") == current_hash


def _mark_ingested(file_path: str, document_id: str) -> None:
    """Record a file as successfully ingested."""
    state = _load_state()
    state["ingested_files"][file_path] = {
        "hash": _file_hash(file_path),
        "document_id": document_id,
    }
    _save_state(state)


def ingest_local_file(file_path: str) -> None:
    """Ingest a local PDF file detected by the watcher.

    This is called from the watcher's thread, so we run the async pipeline
    in a new event loop.
    """
    if _is_already_ingested(file_path):
        logger.info("Skipping already-ingested file: %s", file_path)
        return

    metadata = infer_metadata_from_path(file_path)
    document_id = generate_document_id()
    metadata["document_id"] = document_id

    logger.info(
        "Auto-ingesting: %s (type=%s, aerodrome=%s)",
        Path(file_path).name,
        metadata["doc_type"],
        metadata["aerodrome_icao"],
    )

    try:
        # Insert metadata record
        from app.config import get_settings

        settings = get_settings()
        if settings.USE_LOCAL_MODE:
            from app.db.local_client import insert_document_metadata
        else:
            from app.db.supabase_client import insert_document_metadata

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(insert_document_metadata(metadata))
            loop.run_until_complete(
                run_pipeline(
                    source=file_path,
                    document_id=document_id,
                    metadata=metadata,
                    is_local_file=True,
                )
            )
        finally:
            loop.close()

        _mark_ingested(file_path, document_id)
        logger.info("Auto-ingestion complete: %s -> %s", Path(file_path).name, document_id)

    except Exception as e:
        logger.exception("Auto-ingestion failed for %s: %s", file_path, e)


def scan_data_directory() -> list[str]:
    """Scan the data/ directory for new or modified PDFs not yet ingested.

    Returns a list of file paths that need ingestion.
    """
    data_dir = Path(__file__).resolve().parent.parent.parent.parent / "data"
    if not data_dir.exists():
        return []

    pending = []
    for pdf_path in data_dir.rglob("*.pdf"):
        file_path = str(pdf_path)
        if not _is_already_ingested(file_path):
            pending.append(file_path)

    if pending:
        logger.info("Found %d new/modified PDFs in data/", len(pending))

    return pending
