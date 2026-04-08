"""Supabase client factory for production mode."""

from __future__ import annotations

import logging
from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_supabase() -> Client:
    """Create and cache a Supabase client using the service role key."""
    settings = get_settings()
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY,
    )


async def update_document_status(
    document_id: str,
    status: str,
    chunk_count: int | None = None,
    error_message: str | None = None,
) -> None:
    """Update a document's processing status in the document_metadata table."""
    try:
        client = get_supabase()
        update_data: dict = {"status": status, "updated_at": "now()"}
        if chunk_count is not None:
            update_data["chunk_count"] = chunk_count
        if error_message is not None:
            update_data["error_message"] = error_message
        client.table("document_metadata").update(update_data).eq(
            "document_id", document_id
        ).execute()
    except Exception as e:
        logger.error("Failed to update document status for %s: %s", document_id, e)
        raise


async def insert_document_metadata(metadata: dict) -> None:
    """Insert a new document metadata record."""
    try:
        client = get_supabase()
        client.table("document_metadata").insert(metadata).execute()
    except Exception as e:
        logger.error("Failed to insert document metadata: %s", e)
        raise


async def get_document_by_id(document_id: str) -> dict | None:
    """Fetch a document metadata record by ID."""
    try:
        client = get_supabase()
        result = (
            client.table("document_metadata")
            .select("*")
            .eq("document_id", document_id)
            .maybe_single()
            .execute()
        )
        return result.data
    except Exception as e:
        logger.error("Failed to fetch document %s: %s", document_id, e)
        raise


async def create_signed_url(storage_path: str, expires_in: int = 3600) -> str:
    """Create a signed URL for downloading a file from Supabase Storage."""
    try:
        client = get_supabase()
        result = client.storage.from_("documents").create_signed_url(
            storage_path, expires_in
        )
        return result["signedURL"]
    except Exception as e:
        logger.error("Failed to create signed URL for %s: %s", storage_path, e)
        raise
