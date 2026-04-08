# API Reference

Complete API reference for the Celestia Memoria backend.

## Base URL

| Environment | URL |
|------------|-----|
| Local | `http://localhost:8000` |
| Production | Your Railway deployment URL |

## Authentication

All endpoints except `/health`, `/docs`, `/redoc`, and `/openapi.json` require a Bearer token.

```
Authorization: Bearer <supabase_jwt>
```

In local mode (`USE_LOCAL_MODE=true`), authentication is bypassed with a dev user (admin role).

---

## Endpoints

### GET /health

Health check and mode information. No authentication required.

**Response 200:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "mode": "local"
}
```

**Example:**
```bash
curl http://localhost:8000/health
```

---

### POST /chat/stream

LangServe streaming chat endpoint. Returns Server-Sent Events with JSONPatch operations. This is the primary endpoint used by the frontend.

**Request:**
```json
{
  "input": {
    "messages": [
      { "type": "human", "content": "What is the minimum radar separation?" }
    ],
    "intent": "",
    "requires_rag": false,
    "query_rewrite": "",
    "retrieved_chunks": [],
    "reranked_chunks": [],
    "final_response": "",
    "sources": [],
    "node_trace": [],
    "model_slug": "default",
    "aerodrome_icao": "GLOBAL"
  }
}
```

**Response:** SSE stream of JSONPatch events:
```
data: {"ops":[{"op":"replace","path":"/intent","value":"regulatory_query"}]}

data: {"ops":[{"op":"replace","path":"/final_response","value":"According to ICAO Doc 4444..."}]}

data: {"ops":[{"op":"replace","path":"/sources","value":[{"source_index":1,"doc_name":"ICAO Doc 4444","doc_type":"ICAO_DOC","section_path":"Chapter 8 > Radar Separation","page_number":85,"aerodrome_icao":"GLOBAL","clause_id":"8.7.3.1","cited_clause":"8.7.3.1"}]}]}

data: [DONE]
```

**Example:**
```bash
curl -N -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "input": {
      "messages": [{"type": "human", "content": "What is the minimum radar separation?"}],
      "intent": "", "requires_rag": false, "query_rewrite": "",
      "retrieved_chunks": [], "reranked_chunks": [],
      "final_response": "", "sources": [], "node_trace": [],
      "model_slug": "default", "aerodrome_icao": "GLOBAL"
    }
  }'
```

---

### POST /chat/invoke

LangServe synchronous chat endpoint. Same request schema as `/chat/stream` but returns the complete response as a single JSON object.

**Request:** Same as `/chat/stream`.

**Response 200:** Complete AgentState object:
```json
{
  "output": {
    "messages": [...],
    "intent": "regulatory_query",
    "requires_rag": true,
    "query_rewrite": "minimum radar separation distance ICAO",
    "retrieved_chunks": [...],
    "reranked_chunks": [...],
    "final_response": "According to ICAO Doc 4444, Section 8.7.3...",
    "sources": [...],
    "node_trace": ["router", "retrieval", "synthesis"],
    "model_slug": "default",
    "aerodrome_icao": "GLOBAL"
  }
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/chat/invoke \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "input": {
      "messages": [{"type": "human", "content": "What are ICAO runway marking standards?"}],
      "intent": "", "requires_rag": false, "query_rewrite": "",
      "retrieved_chunks": [], "reranked_chunks": [],
      "final_response": "", "sources": [], "node_trace": [],
      "model_slug": "default", "aerodrome_icao": "GLOBAL"
    }
  }'
```

---

### POST /query

Direct query with a simple JSON response. Does not stream. Useful for programmatic access and integrations.

**Request:**
```json
{
  "message": "What are the ICAO standards for runway markings?",
  "aerodrome_icao": "GLOBAL",
  "model_slug": "default"
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `message` | string | *required* | The user's question |
| `aerodrome_icao` | string | `"GLOBAL"` | Target aerodrome ICAO code |
| `model_slug` | string | `"default"` | LLM model identifier |

**Response 200:**
```json
{
  "answer": "According to ICAO Annex 14, Chapter 5, runway markings shall include...",
  "sources": [
    {
      "source_index": 1,
      "doc_name": "ICAO Annex 14",
      "doc_type": "ICAO_DOC",
      "section_path": "Chapter 5 > Visual Aids",
      "page_number": 42,
      "aerodrome_icao": "GLOBAL",
      "clause_id": "5.2.1.1",
      "cited_clause": "5.2.1.1"
    }
  ],
  "intent": "regulatory_query",
  "node_trace": ["router", "retrieval", "synthesis"]
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message": "What are the ICAO standards for runway markings?"}'
```

---

### POST /ingest

Trigger document ingestion pipeline. **Admin role required.** The pipeline runs in the background and returns immediately with a processing status.

**Request:**
```json
{
  "storage_path": "icao/doc4444.pdf",
  "doc_name": "ICAO Doc 4444 - PANS-ATM",
  "doc_type": "ICAO_DOC",
  "aerodrome_icao": "GLOBAL",
  "effective_date": "2024-01-01",
  "expiry_date": null,
  "document_id": null
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `storage_path` | string | *required* | Path in Supabase Storage or local filesystem |
| `doc_name` | string | *required* | Human-readable document name |
| `doc_type` | string | *required* | Document type (see below) |
| `aerodrome_icao` | string | `"GLOBAL"` | ICAO aerodrome code or `GLOBAL` |
| `effective_date` | string? | `null` | Effective date (`YYYY-MM-DD`) |
| `expiry_date` | string? | `null` | Expiry date (`YYYY-MM-DD`) |
| `document_id` | string? | `null` | Custom ID (auto-generated if omitted) |

**Response 200:**
```json
{
  "status": "processing",
  "document_id": "doc_a1b2c3d4",
  "message": "Document 'ICAO Doc 4444 - PANS-ATM' queued for ingestion"
}
```

**Response 403:**
```json
{
  "detail": "Only admins can trigger document ingestion"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "storage_path": "icao/doc4444.pdf",
    "doc_name": "ICAO Doc 4444 - PANS-ATM",
    "doc_type": "ICAO_DOC",
    "aerodrome_icao": "GLOBAL"
  }'
```

---

### GET /docs

Interactive Swagger UI API documentation. No authentication required.

### GET /redoc

ReDoc API documentation. No authentication required.

---

## Document Types

Valid values for `doc_type`:

| Type | Description |
|------|-------------|
| `AIP` | Aeronautical Information Publication |
| `AIP_SUP` | AIP Supplement |
| `UNIT_MANUAL` | Unit/Tower Manual |
| `ICAO_DOC` | ICAO Document (Annex, PANS, etc.) |
| `EASA_REG` | EASA Regulation |
| `PROCEDURE_CHANGE` | Procedure Change Notice |
| `LOA` | Letter of Agreement |

## ICAO Codes

- Must be exactly 4 uppercase letters: `^[A-Z]{4}$`
- Or the string `GLOBAL` for documents not specific to an aerodrome
- Examples: `EGLL` (Heathrow), `KJFK` (JFK), `LFPG` (Paris CDG), `EDDF` (Frankfurt)

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error description"
}
```

| Status | Meaning |
|--------|---------|
| 400 | Bad request (missing or invalid fields) |
| 401 | Missing or invalid authentication token |
| 403 | Insufficient permissions (e.g., non-admin calling `/ingest`) |
| 422 | Validation error (invalid request body — Pydantic) |
| 500 | Internal server error |
| 502 | Backend unreachable (from Next.js proxy) |
