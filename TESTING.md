# Testing

Testing strategy and guide for Celestia Memoria.

## Running Tests

### Backend

```bash
cd services/ai-backend

# All unit tests
uv run pytest

# With coverage report
uv run pytest --cov=app --cov-report=term-missing

# Specific test file
uv run pytest tests/test_chunker.py

# Evaluation tests (require Ollama or API keys)
uv run pytest -m evaluation

# Integration tests
uv run pytest -m integration

# Unit tests only (exclude slow tests)
uv run pytest -m "not evaluation and not integration"
```

### Frontend

```bash
# Type checking (from root)
pnpm typecheck

# Linting
pnpm lint
```

### All Checks (CI equivalent)

```bash
pnpm typecheck && pnpm lint && cd services/ai-backend && uv run ruff check . && uv run pytest
```

## Test Structure

```
services/ai-backend/tests/
├── test_config.py                  Settings validation
├── test_chunker.py                 Heading-aware chunking logic
├── test_metadata.py                ICAO code and doc type validation
├── test_auth_middleware.py          JWT validation and local mode bypass
├── test_hybrid_retriever.py        Hybrid search and deduplication
├── test_reranker.py                Reranking and score thresholds
├── test_embedder.py                Embedding generation and batching
├── test_api_endpoints.py           API endpoint integration tests
├── conftest.py                     Shared fixtures
└── evaluation/
    ├── test_citation_accuracy.py   Citation format and accuracy
    ├── test_grounding.py           Answer grounding in sources
    └── test_refusal.py             Out-of-scope query refusal
```

## Test Categories

### Unit Tests

Fast, no external dependencies. Test individual functions and classes in isolation.

- **Chunker**: heading detection, token counting, overlap, clause extraction
- **Metadata**: ICAO code validation, doc type validation, date parsing
- **Config**: settings loading, production key validation
- **Auth middleware**: JWT validation, local mode bypass, role extraction
- **Retriever**: deduplication, namespace filtering, score merging
- **Reranker**: score thresholds, fallback behavior
- **Embedder**: prefix construction, batch sizing

### Evaluation Tests (`@pytest.mark.evaluation`)

Test AI behavior quality. Require Ollama (local mode) or API keys (production mode).

- **Citation accuracy**: correct `[Source N]` format, citations reference real retrieved chunks
- **Grounding**: answers derived only from provided sources, no hallucination
- **Refusal**: appropriate refusal for out-of-scope questions (e.g., "What's the weather?")

### Integration Tests (`@pytest.mark.integration`)

Test full system flows. Require running services (database, embeddings).

- **Full ingestion pipeline**: PDF → chunks → embeddings → vector store
- **Full query pipeline**: question → router → retrieval → synthesis → answer
- **API endpoints**: HTTP requests via FastAPI TestClient

## Writing Tests

### Conventions

- File naming: `test_<module>.py`
- Use pytest fixtures in `conftest.py` for shared setup
- Organize with test classes: `class TestComponentName:`
- Descriptive test names: `test_chunker_preserves_heading_hierarchy`
- Mock external services — never call real APIs in unit tests
- Mark slow/external tests with `@pytest.mark.evaluation` or `@pytest.mark.integration`

### Example

```python
import pytest
from app.ingest.chunker import chunk_markdown


class TestChunker:
    def test_splits_on_headings(self):
        md = "# Section 1\nContent here.\n# Section 2\nMore content."
        chunks = chunk_markdown(md, metadata={"doc_name": "test"})
        assert len(chunks) >= 2
        assert chunks[0]["section_path"].startswith("Section 1")

    def test_respects_max_tokens(self):
        long_text = "word " * 2000
        chunks = chunk_markdown(f"# Title\n{long_text}", metadata={"doc_name": "test"})
        for chunk in chunks:
            assert chunk["token_count"] <= 1000

    def test_extracts_clause_ids(self):
        md = "# Chapter 5\n5.2.1.1 The minimum separation shall be..."
        chunks = chunk_markdown(md, metadata={"doc_name": "test"})
        assert any("5.2.1.1" in c.get("clause_ids", []) for c in chunks)
```

### Mocking External Services

```python
import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture
def mock_pinecone():
    with patch("app.retrieval.pinecone_client.get_pinecone_index") as mock:
        index = AsyncMock()
        index.query.return_value = {"matches": []}
        mock.return_value = index
        yield index


@pytest.fixture
def mock_cohere():
    with patch("app.retrieval.reranker.get_cohere_client") as mock:
        client = AsyncMock()
        client.rerank.return_value.results = []
        mock.return_value = client
        yield client
```

## Coverage Goals

| Category | Target |
|----------|--------|
| Core modules (chunker, metadata, config, retrieval) | > 80% |
| Evaluation tests pass rate | > 95% |
| Integration tests | All critical paths covered |

## CI Integration

Tests run automatically on every pull request via GitHub Actions (`.github/workflows/ci.yml`):

1. **ruff check** — Python linting
2. **pytest** — Backend unit tests
3. **pnpm typecheck** — TypeScript type checking
4. **pnpm lint** — Frontend linting
5. **pnpm build** — Build verification
