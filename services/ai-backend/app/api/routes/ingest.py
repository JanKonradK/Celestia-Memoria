"""Document ingestion API endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, Field, model_validator

from app.config import get_settings
from app.ingest.pipeline import generate_document_id, run_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])


VALID_DOC_TYPES = {
    "AIP", "AIP_SUP", "UNIT_MANUAL", "ICAO_DOC", "EASA_REG", "PROCEDURE_CHANGE", "LOA",
}


class IngestRequest(BaseModel):
    """Request body for document ingestion."""

    storage_path: str = Field(
        description="Path in Supabase Storage (or local path in local mode)",
        min_length=1,
        max_length=500,
    )
    doc_name: str = Field(
        description="Human-readable document name",
        min_length=1,
        max_length=300,
    )
    doc_type: str = Field(description="Document type (AIP, ICAO_DOC, EASA_REG, etc.)")
    aerodrome_icao: str = Field(
        default="GLOBAL",
        description="ICAO aerodrome code or GLOBAL",
        pattern=r"^([A-Z]{4}|GLOBAL)$",
    )
    effective_date: str | None = Field(
        default=None,
        description="Effective date (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    expiry_date: str | None = Field(
        default=None,
        description="Expiry date (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    document_id: str | None = Field(
        default=None,
        description="Optional document ID (auto-generated if omitted)",
        max_length=100,
    )

    @model_validator(mode="after")
    def validate_doc_type(self) -> IngestRequest:
        if self.doc_type not in VALID_DOC_TYPES:
            raise ValueError(
                f"Invalid doc_type '{self.doc_type}'. "
                f"Must be one of: {', '.join(sorted(VALID_DOC_TYPES))}"
            )
        return self

    @model_validator(mode="after")
    def sanitize_storage_path(self) -> IngestRequest:
        # Prevent path traversal
        if ".." in self.storage_path or self.storage_path.startswith("/"):
            raise ValueError("storage_path must not contain '..' or start with '/'")
        return self


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
