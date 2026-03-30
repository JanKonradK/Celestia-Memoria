# Celestia Memoria — Developer Guide

## Project Overview

Aviation regulatory document intelligence platform using RAG. Air traffic controllers query ICAO, EASA, and local aerodrome documents through a chat interface.

**Monorepo structure:**
- `apps/web/` — Next.js 15 frontend (TypeScript, React 19, Tailwind CSS)
- `packages/shared-types/` — Shared TypeScript type definitions
- `services/ai-backend/` — FastAPI backend (Python 3.12+, LangGraph)
- `data/` — User-supplied aviation regulatory PDFs

## Commands

```bash
# Frontend dev server
pnpm dev

# Backend dev server
uv --directory services/ai-backend run uvicorn app.main:app --reload --port 8000

# Both together
pnpm dev:all

# Backend tests
cd services/ai-backend && uv run pytest

# Type checking
pnpm typecheck
```

## Architecture

### Agent Graph (LangGraph)

`services/ai-backend/app/agents/graph.py` defines the flow:
```
router → [requires_rag?] → retrieval → synthesis → END
                         ↘ synthesis → END
```

- **Router** (`agents/nodes/router_node.py`): Classifies intent using a fast model (Gemini Flash). Outputs: intent, requires_rag, query_rewrite.
- **Retrieval** (`agents/nodes/retrieval_node.py`): Hybrid dense+sparse search via `retrieval/hybrid_retriever.py`. Filters by aerodrome ICAO code.
- **Synthesis** (`agents/nodes/synthesis_node.py`): Generates answer with `[Source N]` citations using the default model (Claude Sonnet).

### Ingestion Pipeline

`services/ai-backend/app/ingest/pipeline.py` orchestrates:
1. `pdf_parser.py` — pymupdf4llm to Markdown
2. `metadata.py` — Validate ICAO codes, doc types
3. `chunker.py` — Heading-aware split (~800 tokens, tiktoken cl100k_base)
4. `embedder.py` — text-embedding-3-small with structured prefix
5. Pinecone upsert (or SQLite in local mode)

### Retrieval

`services/ai-backend/app/retrieval/hybrid_retriever.py`:
- Alpha=0.6 (60% dense, 40% sparse BM25)
- Queries both aerodrome-specific and GLOBAL namespaces
- Deduplicates, then reranks via Cohere (or score-sort in local mode)

### Frontend Chat

`apps/web/components/chat/ChatInterface.tsx` uses `useChat` from `@ai-sdk/react`. The Next.js API route at `app/api/chat/route.ts` proxies to the FastAPI backend's LangServe `/chat/stream` endpoint.

## Conventions

### Python (Backend)
- Async functions for all I/O operations
- Pydantic for request/response models
- `@lru_cache` singletons for clients and settings
- Type hints on all function signatures
- Logging via `logging.getLogger(__name__)`
- Imports: stdlib → third-party → local (`app.`)

### TypeScript (Frontend)
- Path alias: `@/` → project root (apps/web/)
- Server components by default, `"use client"` only when needed
- Radix UI primitives wrapped with Tailwind styling in `components/ui/`
- `cn()` helper from `lib/utils.ts` for class merging

### Document Types
Valid: `AIP`, `AIP_SUP`, `UNIT_MANUAL`, `ICAO_DOC`, `EASA_REG`, `PROCEDURE_CHANGE`, `LOA`

### ICAO Codes
Must be exactly 4 uppercase letters (regex: `^[A-Z]{4}$`) or the string `GLOBAL`.

## Local Development Mode

Set `USE_LOCAL_MODE=true` in `services/ai-backend/.env`:
- SQLite database at `services/ai-backend/celestia_local.db`
- sentence-transformers `all-MiniLM-L6-v2` for embeddings
- Ollama at `localhost:11434` for LLM
- Auth middleware bypassed (dev user with admin role)
- No Pinecone, Supabase, OpenRouter, or Cohere needed

## Adding New Features

### New Document Type
1. Add to `VALID_DOC_TYPES` in `services/ai-backend/app/ingest/metadata.py`
2. Add to `DocumentType` union in `packages/shared-types/src/documents.ts`
3. Add to `DOC_TYPES` array in `apps/web/components/documents/UploadDialog.tsx`

### New Agent Node
1. Create `services/ai-backend/app/agents/nodes/your_node.py`
2. Define async function matching `AgentState → dict` signature
3. Add node to graph in `services/ai-backend/app/agents/graph.py`
4. Add any new state fields to `services/ai-backend/app/agents/state.py`

### New API Endpoint
1. Create route in `services/ai-backend/app/api/routes/`
2. Include router in `services/ai-backend/app/main.py`
