# Contributing

Guide for contributing to Celestia Memoria.

## Getting Started

### Prerequisites

- **Node.js** >= 20.0.0
- **pnpm** >= 9.0.0
- **Python** >= 3.12
- **uv** — Python package manager ([astral.sh/uv](https://astral.sh/uv))
- **Ollama** — for local mode ([ollama.com](https://ollama.com))

### Setup

```bash
git clone https://github.com/JanKonradK/Celestia-Memoria.git
cd Celestia-Memoria

# Install frontend dependencies
pnpm install

# Install backend dependencies
cd services/ai-backend && uv sync && cd ../..

# Configure environment
cp services/ai-backend/.env.example services/ai-backend/.env
cp apps/web/.env.example apps/web/.env.local
```

For local development without API keys, set in `services/ai-backend/.env`:

```env
USE_LOCAL_MODE=true
ENABLE_WATCHER=true
```

Then pull an Ollama model: `ollama pull llama3.2`

## Development Workflow

### Running Locally

```bash
pnpm dev:all          # Both frontend (3000) + backend (8000)
pnpm dev              # Frontend only
pnpm dev:backend      # Backend only
```

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Branch Strategy

| Prefix | Purpose |
|--------|---------|
| `main` | Stable, deployable |
| `feat/` | New features |
| `fix/` | Bug fixes |
| `docs/` | Documentation |
| `refactor/` | Code improvements |
| `test/` | Test additions |

### Commit Conventions

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(backend): add document expiry date filtering
fix(frontend): prevent XSS in markdown rendering
docs(api): add curl examples to API reference
refactor(backend): extract retrieval timeout config
test(backend): add integration tests for ingestion pipeline
chore(infra): add GitHub Actions CI workflow
```

**Scopes**: `frontend`, `backend`, `shared`, `infra`, `data`

### Pull Request Process

1. Create a feature branch from `main`
2. Make changes, write tests
3. Run all checks (see below)
4. Push and open a PR against `main`
5. PR title follows conventional commit format
6. Include a description of changes and a test plan
7. Link related issues

### Running All Checks

```bash
# Frontend
pnpm typecheck
pnpm lint

# Backend
cd services/ai-backend
uv run ruff check .
uv run pytest

# Or all at once from root
pnpm typecheck && pnpm lint && cd services/ai-backend && uv run ruff check . && uv run pytest
```

## Code Style

### Python (Backend)

- **Linter**: Ruff (line length 100, Python 3.12 target)
- **Rules**: E, F, I, N, W, UP (errors, pyflakes, imports, naming, warnings, upgrades)
- All functions must have **type hints**
- **Async** functions for all I/O operations
- **Pydantic** models for request/response schemas
- `@lru_cache` singletons for clients and settings
- Logging via `logging.getLogger(__name__)`
- **Import order**: stdlib → third-party → local (`app.`)

### TypeScript (Frontend)

- **Strict mode** enabled
- Path alias: `@/` → project root (`apps/web/`)
- Server components by default, `"use client"` only when needed
- Radix UI primitives wrapped with Tailwind in `components/ui/`
- `cn()` helper from `lib/utils.ts` for class merging
- **No `any` types** — use proper type declarations

### Shared Types

- All API contracts defined in `packages/shared-types/src/`
- When adding a new API type, add to both TypeScript types and Python Pydantic models
- Export new types from the barrel `index.ts`

## Adding Features

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
2. Define Pydantic request/response models
3. Include router in `services/ai-backend/app/main.py`
4. Add TypeScript types to `packages/shared-types/src/api.ts`

### New UI Component

1. For primitives: wrap Radix UI in `apps/web/components/ui/`
2. For features: add to appropriate subdirectory in `apps/web/components/`
3. Use `cn()` for class merging, CVA for variants

## Testing

```bash
# Backend unit tests
cd services/ai-backend && uv run pytest

# With coverage
uv run pytest --cov=app --cov-report=term-missing

# Evaluation tests (require Ollama or API keys)
uv run pytest -m evaluation

# Integration tests
uv run pytest -m integration

# Frontend type checking + linting
pnpm typecheck && pnpm lint
```

See [TESTING.md](TESTING.md) for full testing documentation.

## Project Structure

```
celestia-memoria/
├── apps/web/                    Next.js 15 frontend
│   ├── app/                     App Router pages & layouts
│   │   ├── (auth)/              Auth route group (login)
│   │   └── api/                 API routes (chat proxy, NextAuth)
│   ├── components/              React components
│   │   ├── chat/                Chat UI (ChatInterface, MessageBubble, etc.)
│   │   ├── documents/           Document management (UploadDialog)
│   │   ├── providers/           Context providers (Auth, Query)
│   │   └── ui/                  Radix UI primitives
│   └── lib/                     Auth config, Supabase clients, utilities
├── packages/shared-types/       Shared TypeScript type definitions
│   └── src/                     Type source files (api, auth, chat, documents)
├── services/ai-backend/         FastAPI backend
│   ├── app/
│   │   ├── agents/              LangGraph agent (state, graph, nodes/)
│   │   ├── api/                 REST endpoints & auth middleware
│   │   ├── db/                  Database clients (Supabase, SQLite)
│   │   ├── ingest/              Ingestion pipeline (PDF, chunk, embed)
│   │   ├── llm/                 LLM abstraction (OpenRouter, Ollama)
│   │   ├── retrieval/           Hybrid search + reranking
│   │   └── watcher/             File system watcher
│   └── tests/                   Backend test suite
└── data/                        Aviation regulatory documents
```
