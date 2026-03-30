"""SQLite-based local storage for development mode (no Supabase required)."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from functools import lru_cache

DB_PATH = Path(__file__).resolve().parent.parent.parent / "celestia_local.db"


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@lru_cache
def init_local_db() -> None:
    """Create tables if they don't exist."""
    conn = _get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS document_metadata (
            document_id TEXT PRIMARY KEY,
            doc_name TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            aerodrome_icao TEXT NOT NULL DEFAULT 'GLOBAL',
            effective_date TEXT,
            expiry_date TEXT,
            is_current INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'pending',
            chunk_count INTEGER,
            storage_path TEXT,
            error_message TEXT,
            uploaded_by TEXT NOT NULL DEFAULT 'local',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS vector_store (
            chunk_id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            section_path TEXT NOT NULL DEFAULT '',
            page_number INTEGER,
            token_count INTEGER NOT NULL DEFAULT 0,
            embedding BLOB NOT NULL,
            doc_name TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            aerodrome_icao TEXT NOT NULL DEFAULT 'GLOBAL',
            is_current INTEGER NOT NULL DEFAULT 1,
            effective_date TEXT,
            expiry_date TEXT,
            FOREIGN KEY (document_id) REFERENCES document_metadata(document_id)
        );

        CREATE INDEX IF NOT EXISTS idx_vector_store_document
            ON vector_store(document_id);
        CREATE INDEX IF NOT EXISTS idx_vector_store_aerodrome
            ON vector_store(aerodrome_icao);
        CREATE INDEX IF NOT EXISTS idx_vector_store_current
            ON vector_store(is_current);
    """)
    conn.commit()
    conn.close()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def update_document_status(
    document_id: str,
    status: str,
    chunk_count: int | None = None,
    error_message: str | None = None,
) -> None:
    init_local_db()
    conn = _get_connection()
    updates = ["status = ?", "updated_at = ?"]
    params: list = [status, _now_iso()]
    if chunk_count is not None:
        updates.append("chunk_count = ?")
        params.append(chunk_count)
    if error_message is not None:
        updates.append("error_message = ?")
        params.append(error_message)
    params.append(document_id)
    conn.execute(
        f"UPDATE document_metadata SET {', '.join(updates)} WHERE document_id = ?",
        params,
    )
    conn.commit()
    conn.close()


async def insert_document_metadata(metadata: dict) -> None:
    init_local_db()
    conn = _get_connection()
    now = _now_iso()
    metadata.setdefault("created_at", now)
    metadata.setdefault("updated_at", now)
    metadata.setdefault("is_current", True)
    metadata.setdefault("status", "pending")
    metadata.setdefault("uploaded_by", "local")
    columns = ", ".join(metadata.keys())
    placeholders = ", ".join("?" for _ in metadata)
    conn.execute(
        f"INSERT OR REPLACE INTO document_metadata ({columns}) VALUES ({placeholders})",
        list(metadata.values()),
    )
    conn.commit()
    conn.close()


async def get_document_by_id(document_id: str) -> dict | None:
    init_local_db()
    conn = _get_connection()
    row = conn.execute(
        "SELECT * FROM document_metadata WHERE document_id = ?",
        (document_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


async def upsert_vectors(
    vectors: list[dict],
) -> None:
    """Store embedding vectors locally.

    Each dict in vectors must have: chunk_id, document_id, chunk_index,
    chunk_text, section_path, page_number, token_count, embedding (as bytes),
    doc_name, doc_type, aerodrome_icao, is_current, effective_date, expiry_date.
    """
    init_local_db()
    conn = _get_connection()
    for v in vectors:
        conn.execute(
            """INSERT OR REPLACE INTO vector_store
               (chunk_id, document_id, chunk_index, chunk_text, section_path,
                page_number, token_count, embedding, doc_name, doc_type,
                aerodrome_icao, is_current, effective_date, expiry_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                v["chunk_id"],
                v["document_id"],
                v["chunk_index"],
                v["chunk_text"],
                v.get("section_path", ""),
                v.get("page_number"),
                v.get("token_count", 0),
                v["embedding"],
                v["doc_name"],
                v["doc_type"],
                v.get("aerodrome_icao", "GLOBAL"),
                v.get("is_current", 1),
                v.get("effective_date"),
                v.get("expiry_date"),
            ),
        )
    conn.commit()
    conn.close()


async def search_vectors(
    query_embedding: bytes,
    aerodrome: str = "GLOBAL",
    top_k: int = 20,
) -> list[dict]:
    """Brute-force cosine similarity search over stored embeddings."""
    import numpy as np

    init_local_db()
    conn = _get_connection()

    query_vec = np.frombuffer(query_embedding, dtype=np.float32)
    query_norm = np.linalg.norm(query_vec)
    if query_norm == 0:
        return []

    rows = conn.execute(
        """SELECT * FROM vector_store
           WHERE is_current = 1
           AND (aerodrome_icao = ? OR aerodrome_icao = 'GLOBAL')""",
        (aerodrome,),
    ).fetchall()
    conn.close()

    results = []
    for row in rows:
        row_dict = dict(row)
        stored_vec = np.frombuffer(row_dict["embedding"], dtype=np.float32)
        stored_norm = np.linalg.norm(stored_vec)
        if stored_norm == 0:
            continue
        score = float(np.dot(query_vec, stored_vec) / (query_norm * stored_norm))
        row_dict["score"] = score
        del row_dict["embedding"]
        results.append(row_dict)

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


async def delete_document_vectors(document_id: str) -> None:
    init_local_db()
    conn = _get_connection()
    conn.execute("DELETE FROM vector_store WHERE document_id = ?", (document_id,))
    conn.commit()
    conn.close()
