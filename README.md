# Celestia Memoria

[![CI](https://github.com/JanKonradK/Celestia-Memoria/actions/workflows/ci.yml/badge.svg)](https://github.com/JanKonradK/Celestia-Memoria/actions/workflows/ci.yml)

AI-powered aviation regulatory document intelligence platform. Celestia Memoria uses Retrieval-Augmented Generation (RAG) to help air traffic controllers quickly find and understand information from ICAO documents, EASA regulations, AIPs, unit manuals, and other official aviation publications.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js 15)                      │
│  Login Page  │  Chat Interface  │  Document Upload Dialog     │
│  NextAuth 5 + Supabase  │  AI SDK Streaming  │  Radix UI     │
└──────────────────────────┬───────────────────────────────────┘
                           │ /api/chat (SSE proxy)
┌──────────────────────────┴───────────────────────────────────┐
│                    Backend (FastAPI)                           │
│                                                               │
│  ┌─ Agent Graph (LangGraph) ────────────────────────────┐    │
│  │  Router Node → Retrieval Node → Synthesis Node       │    │
│  │  (Gemini Flash)  (Hybrid Search)  (Claude Sonnet)    │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─ Ingestion Pipeline ─────────────────────────────────┐    │
│  │  PDF Parse → Chunk → Embed → BM25 → Vector Store    │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
│  File Watcher (optional) │ Auth Middleware │ REST API         │
└──────────────────────────────────────────────────────────────┘
         │              │              │
    ┌────┴────┐   ┌────┴────┐   ┌────┴────┐
    │Pinecone │   │Supabase │   │OpenRouter│
    │(vectors)│   │(auth/db)│   │  (LLM)  │
    └─────────┘   └─────────┘   └─────────┘
```

## Project Structure

```
celestia-memoria/
├── apps/web/                    Next.js 15 frontend
│   ├── app/                     App Router pages & layouts
│   ├── components/              React components (UI, chat, documents)
│   └── lib/                     Auth, Supabase clients, utilities
├── packages/shared-types/       Shared TypeScript type definitions
├── services/ai-backend/         FastAPI backend
│   ├── app/
│   │   ├── agents/              LangGraph agent (router, retrieval, synthesis)
│   │   ├── api/                 REST endpoints & auth middleware
│   │   ├── db/                  Supabase + SQLite (local) clients
│   │   ├── ingest/              PDF parsing, chunking, embedding pipeline
│   │   ├── llm/                 OpenRouter + Ollama LLM abstraction
│   │   ├── retrieval/           Hybrid search (Pinecone + BM25 + reranking)
│   │   └── watcher/             File system watcher for auto-ingestion
│   └── tests/                   Backend test suite
├── data/                        Aviation regulatory documents (user-supplied)
│   ├── icao/                    ICAO documents
│   ├── easa/                    EASA regulations
│   ├── local/                   Country/aerodrome-specific docs
│   └── other/                   Miscellaneous docs
└── README.md
```

## Prerequisites

- **Node.js** >= 20.0.0
- **pnpm** >= 9.0.0 (frontend package manager)
- **Python** >= 3.12 (3.14 recommended)
- **uv** (Python package manager — install from [astral.sh/uv](https://astral.sh/uv))

### Production Mode (external services required)
- [Supabase](https://supabase.com) project (auth + database)
- [Pinecone](https://www.pinecone.io) index (vector storage)
- [OpenRouter](https://openrouter.ai) API key (LLM access)
- [Cohere](https://cohere.com) API key (reranking)

### Local Development Mode (no API keys needed)
- [Ollama](https://ollama.com) running locally with a model pulled (e.g., `ollama pull llama3.2`)
- Uses SQLite for storage, sentence-transformers for embeddings, Ollama for LLM

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/JanKonradK/Celestia-Memoria.git
cd Celestia-Memoria

# Install frontend dependencies
pnpm install

# Install backend dependencies
cd services/ai-backend
uv sync
cd ../..
```

### 2. Configure Environment

```bash
# Backend
cp services/ai-backend/.env.example services/ai-backend/.env
# Edit services/ai-backend/.env with your API keys

# Frontend
cp apps/web/.env.example apps/web/.env.local
# Edit apps/web/.env.local with your Supabase credentials
```

**For local development without API keys**, set in `services/ai-backend/.env`:
```
USE_LOCAL_MODE=true
ENABLE_WATCHER=true
```

### 3. Add Aviation Documents

Place PDF files in the `data/` directory:
```
data/icao/     → ICAO documents (Doc 4444, Annexes, etc.)
data/easa/     → EASA regulations
data/local/    → Country AIPs (use ICAO code subfolders for aerodrome-specific)
data/other/    → Miscellaneous
```

See [`data/README.md`](data/README.md) for detailed conventions.

### 4. Run

```bash
# Terminal 1: Backend
uv --directory services/ai-backend run uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
pnpm dev
```

Or use the combined command:
```bash
pnpm dev:all
```

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Key Features

### RAG Pipeline
- **Hybrid retrieval**: 60% dense (semantic) + 40% sparse (BM25 keyword) search
- **Embedding prefix strategy**: Structured metadata `[DOC:type|ICAO:code|...]` prepended to chunks improves domain-specific retrieval
- **Cohere reranking**: Final results reranked for query relevance
- **Citation tracking**: All answers include `[Source N]` references back to original documents

### Agent Graph
- **Router Node** (fast model): Classifies intent, rewrites queries, decides if RAG is needed
- **Retrieval Node**: Executes hybrid search filtered by aerodrome and document currency
- **Synthesis Node** (powerful model): Generates cited answers with strict aviation accuracy rules

### Document Ingestion
- PDF to structured Markdown via PyMuPDF
- Heading-aware chunking (~800 tokens) with sentence overlap
- Automatic metadata inference from directory placement
- File watcher for drop-and-forget ingestion

### Local Development Mode
Set `USE_LOCAL_MODE=true` to run entirely locally:
- SQLite replaces Supabase
- sentence-transformers replaces OpenAI embeddings
- Ollama replaces OpenRouter
- Score-based ranking replaces Cohere reranking
- Auth middleware bypassed with dev user

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check and mode info |
| POST | `/chat/stream` | LangServe streaming chat (SSE) |
| POST | `/chat/invoke` | LangServe synchronous chat |
| POST | `/query` | Direct query with JSON response |
| POST | `/ingest` | Trigger document ingestion (admin only) |
| GET | `/docs` | Interactive API documentation |

## Environment Variables

### Backend (`services/ai-backend/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `USE_LOCAL_MODE` | No | `false` | Enable local dev mode |
| `ENABLE_WATCHER` | No | `false` | Enable data/ directory watcher |
| `SUPABASE_URL` | Prod | — | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Prod | — | Supabase service role key |
| `SUPABASE_JWT_SECRET` | Prod | — | JWT secret for token validation |
| `OPENROUTER_API_KEY` | Prod | — | OpenRouter API key |
| `PINECONE_API_KEY` | Prod | — | Pinecone API key |
| `COHERE_API_KEY` | Prod | — | Cohere API key for reranking |
| `OLLAMA_BASE_URL` | Local | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | Local | `llama3.2` | Ollama model name |

### Frontend (`apps/web/.env.local`)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXTAUTH_URL` | Yes | App URL (http://localhost:3000) |
| `NEXTAUTH_SECRET` | Yes | Random secret for session encryption |
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | Supabase anonymous key |
| `BACKEND_URL` | No | Backend URL (default: http://localhost:8000) |

## Docker

```bash
# Full stack (frontend + backend + Ollama)
docker compose up

# Backend only
docker compose up backend
```

See [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment with Vercel + Railway.

## Testing

```bash
# Backend unit tests
cd services/ai-backend
uv run pytest

# With coverage
uv run pytest --cov=app --cov-report=term-missing

# Frontend type checking + linting
pnpm typecheck && pnpm lint

# All checks (CI equivalent)
pnpm typecheck && pnpm lint && cd services/ai-backend && uv run ruff check . && uv run pytest
```

See [TESTING.md](TESTING.md) for full testing documentation.

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend Framework | Next.js 15, React 19, TypeScript 5.9 |
| UI Components | Radix UI, Tailwind CSS, Lucide Icons |
| State Management | TanStack React Query, Vercel AI SDK |
| Authentication | NextAuth 5 + Supabase |
| Backend Framework | FastAPI, Python 3.12+ |
| Agent Orchestration | LangGraph |
| Vector Database | Pinecone (prod) / SQLite (local) |
| Embeddings | text-embedding-3-small (prod) / all-MiniLM-L6-v2 (local) |
| LLM Provider | OpenRouter (prod) / Ollama (local) |
| Reranking | Cohere rerank-english-v3.0 |
| PDF Processing | PyMuPDF / pymupdf4llm |
| Monitoring | Sentry (error tracking + performance) |
| Package Managers | pnpm (JS), uv (Python) |
| CI/CD | GitHub Actions |
| Containerization | Docker, Docker Compose |

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture, data flow diagrams, design decisions |
| [API.md](API.md) | Complete API reference with curl examples |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production deployment guide (Vercel + Railway) |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development setup, code style, PR process |
| [TESTING.md](TESTING.md) | Testing strategy, running tests, writing tests |
| [SECURITY.md](SECURITY.md) | Security model, auth flow, threat assessment |
| [CLAUDE.md](CLAUDE.md) | Developer conventions, adding features |
| [data/README.md](data/README.md) | Document placement and ingestion guidelines |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide. Quick summary:

1. Read [CLAUDE.md](CLAUDE.md) for project conventions
2. Create a feature branch from `main`
3. Run all checks: `pnpm typecheck && pnpm lint && cd services/ai-backend && uv run ruff check . && uv run pytest`
4. Open a PR with a conventional commit title

## License

Private — not open source.
