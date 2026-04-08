"""Document ingestion pipeline: parse -> chunk -> embed -> store."""

from __future__ import annotations

import json
import logging
import uuid

from app.config import get_settings
from app.ingest.chunker import chunk_markdown
from app.ingest.embedder import embed_chunks, embedding_to_bytes
from app.ingest.metadata import normalize_metadata
from app.ingest.pdf_parser import parse_pdf_from_url, parse_pdf_to_markdown

logger = logging.getLogger(__name__)


async def _store_vectors_production(chunks: list[dict], document_id: str) -> None:
    """Upsert chunk vectors into Pinecone (production mode)."""
    from app.retrieval.bm25_encoder import get_encoder
    from app.retrieval.pinecone_client import get_index

    index = get_index()
    bm25 = get_encoder()

    vectors_to_upsert = []
    for chunk in chunks:
        chunk_id = f"{document_id}_{chunk['chunk_index']}"
        sparse = bm25.encode_documents([chunk["chunk_text"]])[0]

        chunk_text = chunk["chunk_text"]
        if len(chunk_text) > 40000:
            logger.warning(
                "Chunk %s text truncated from %d to 40000 chars for Pinecone metadata",
                chunk_id, len(chunk_text),
            )

        metadata = {
            "document_id": document_id,
            "doc_type": chunk.get("doc_type", ""),
            "doc_name": chunk.get("doc_name", ""),
            "section_path": chunk.get("section_path", ""),
            "page_number": chunk.get("page_number"),
            "chunk_index": chunk["chunk_index"],
            "effective_date": chunk.get("effective_date", ""),
            "expiry_date": chunk.get("expiry_date", ""),
            "is_current": chunk.get("is_current", True),
            "chunk_text": chunk["chunk_text"][:40000],
            "aerodrome_icao": chunk.get("aerodrome_icao", "GLOBAL"),
            "clause_id": chunk.get("clause_id", ""),
            "clause_references": json.dumps(chunk.get("clause_references", [])),
        }

        vectors_to_upsert.append({
            "id": chunk_id,
            "values": chunk["embedding"],
            "sparse_values": sparse,
            "metadata": metadata,
        })

    # Upsert in batches of 100
    import re
    namespace = chunks[0].get("aerodrome_icao", "GLOBAL") if chunks else "GLOBAL"
    if namespace != "GLOBAL" and not re.match(r"^[A-Z]{4}$", namespace):
        raise ValueError(f"Invalid aerodrome namespace for Pinecone: {namespace!r}")
    batch_size = 100
    for i in range(0, len(vectors_to_upsert), batch_size):
        batch = vectors_to_upsert[i : i + batch_size]
        index.upsert(vectors=batch, namespace=namespace)

    logger.info("Upserted %d vectors to Pinecone namespace '%s'", len(vectors_to_upsert), namespace)


async def _store_vectors_local(chunks: list[dict], document_id: str) -> None:
    """Store chunk vectors in local SQLite (local dev mode)."""
    from app.db.local_client import upsert_vectors

    vectors = []
    for chunk in chunks:
        vectors.append({
            "chunk_id": f"{document_id}_{chunk['chunk_index']}",
            "document_id": document_id,
            "chunk_index": chunk["chunk_index"],
            "chunk_text": chunk["chunk_text"],
            "section_path": chunk.get("section_path", ""),
            "page_number": chunk.get("page_number"),
            "token_count": chunk.get("token_count", 0),
            "embedding": embedding_to_bytes(chunk["embedding"]),
            "doc_name": chunk.get("doc_name", ""),
            "doc_type": chunk.get("doc_type", ""),
            "aerodrome_icao": chunk.get("aerodrome_icao", "GLOBAL"),
            "is_current": 1 if chunk.get("is_current", True) else 0,
            "effective_date": chunk.get("effective_date"),
            "expiry_date": chunk.get("expiry_date"),
            "clause_id": chunk.get("clause_id", ""),
            "clause_references": chunk.get("clause_references", []),
        })

    await upsert_vectors(vectors)
    logger.info("Stored %d vectors in local SQLite", len(vectors))


async def _update_status(document_id: str, status: str, **kwargs) -> None:
    """Update document status using the appropriate backend."""
    settings = get_settings()
    if settings.USE_LOCAL_MODE:
        from app.db.local_client import update_document_status
    else:
        from app.db.supabase_client import update_document_status
    await update_document_status(document_id, status, **kwargs)


async def run_pipeline(
    source: str,
    document_id: str,
    metadata: dict,
    is_local_file: bool = False,
) -> None:
    """Run the full ingestion pipeline for a document.

    Args:
        source: Either a Supabase storage_path or a local file path.
        document_id: Unique document identifier.
        metadata: Raw metadata dict (will be normalized).
        is_local_file: If True, source is a local file path instead of storage path.
    """
    settings = get_settings()

    try:
        await _update_status(document_id, "processing")

        # Normalize metadata
        normalized = normalize_metadata(metadata)
        logger.info(
            "Processing document '%s' (type=%s, aerodrome=%s)",
            normalized["doc_name"],
            normalized["doc_type"],
            normalized["aerodrome_icao"],
        )

        # Parse PDF
        if is_local_file:
            markdown = parse_pdf_to_markdown(source)
        else:
            from app.db.supabase_client import create_signed_url
            url = await create_signed_url(source)
            markdown = await parse_pdf_from_url(url, normalized["doc_name"])

        if not markdown.strip():
            raise ValueError("PDF parsing produced empty output")

        # Chunk
        chunks = chunk_markdown(markdown, normalized)

        if not chunks:
            raise ValueError("Chunking produced no chunks")

        # Embed
        chunks = embed_chunks(chunks)

        # Store vectors
        if settings.USE_LOCAL_MODE:
            await _store_vectors_local(chunks, document_id)
        else:
            await _store_vectors_production(chunks, document_id)

        # Update status
        await _update_status(document_id, "indexed", chunk_count=len(chunks))

        logger.info(
            "Pipeline complete for '%s': %d chunks indexed",
            normalized["doc_name"],
            len(chunks),
        )

    except Exception as e:
        logger.exception("Pipeline failed for document %s: %s", document_id, e)
        await _update_status(
            document_id, "failed", error_message=str(e)[:500]
        )
        raise


def generate_document_id() -> str:
    """Generate a unique document ID."""
    return str(uuid.uuid4())
