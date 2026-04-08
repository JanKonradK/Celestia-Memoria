FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies for pymupdf and sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for caching
COPY pyproject.toml uv.lock* ./

# Install dependencies
RUN uv sync --frozen --no-dev --no-editable

# Copy application code
COPY app/ app/

# Create data directory
RUN mkdir -p /data

ENV PORT=8000
ENV PYTHONUNBUFFERED=1

EXPOSE ${PORT}

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
