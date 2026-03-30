"""Document ingestion API endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, Field

from app.ingest.pipeline import run_pipeline, generate_document_id
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])


class IngestRequest(BaseModel):
    """Request body for document ingestion."""

    storage_path: str = Field(description="Path in Supabase Storage (or local path in local mode)")
    doc_name: str = Field(description="Human-readable document name")
    doc_type: str = Field(description="Document type (AIP, ICAO_DOC, EASA_REG, etc.)")
    aerodrome_icao: str = Field(default="GLOBAL", description="ICAO aerodrome code or GLOBAL")
    effective_date: str | None = Field(default=None, description="Effective date (YYYY-MM-DD)")
    expiry_date: str | None = Field(default=None, description="Expiry date (YYYY-MM-DD)")
    document_id: str | None = Field(default=None, description="Optional document ID (auto-generated if omitted)")


class IngestResponse(BaseModel):
    """Response from document ingestion."""

    status: str
    document_id: str
    message: str | None = None


@router.post("", response_model=IngestResponse)
async def ingest_document(
    body: IngestRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> IngestResponse:
    """Trigger document ingestion pipeline.

    Requires admin role. The pipeline runs in the background — returns
    immediately with a processing status.
    """
    # Check authorization
    user_role = getattr(request.state, "user_role", "controller")
    if user_role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can trigger document ingestion",
        )

    settings = get_settings()
    document_id = body.document_id or generate_document_id()
    is_local = settings.USE_LOCAL_MODE

    metadata = {
        "document_id": document_id,
        "doc_name": body.doc_name,
        "doc_type": body.doc_type,
        "aerodrome_icao": body.aerodrome_icao,
        "effective_date": body.effective_date,
        "expiry_date": body.expiry_date,
    }

    # Insert initial metadata record
    if is_local:
        from app.db.local_client import insert_document_metadata
    else:
        from app.db.supabase_client import insert_document_metadata

    await insert_document_metadata(metadata)

    # Run pipeline in background
    background_tasks.add_task(
        run_pipeline,
        source=body.storage_path,
        document_id=document_id,
        metadata=metadata,
        is_local_file=is_local,
    )

    logger.info("Ingestion queued for document '%s' (id=%s)", body.doc_name, document_id)

    return IngestResponse(
        status="processing",
        document_id=document_id,
        message=f"Document '{body.doc_name}' queued for ingestion",
    )
