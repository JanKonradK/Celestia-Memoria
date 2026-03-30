"""FastAPI application factory and entry point for Celestia Memoria backend."""

from __future__ import annotations

import logging
import platform
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.middleware.auth import SupabaseAuthMiddleware
from app.api.routes.ingest import router as ingest_router
from app.api.routes.query import router as query_router

logger = logging.getLogger(__name__)


# Fix Windows console encoding for UTF-8 output
if platform.system() == "Windows":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown tasks."""
    settings = get_settings()

    # Validate configuration
    missing = settings.validate_production_keys()
    if missing:
        if settings.USE_LOCAL_MODE:
            logger.info("Running in LOCAL mode — external API keys not required")
        else:
            logger.warning(
                "Missing required environment variables for production mode: %s. "
                "Set USE_LOCAL_MODE=true for local development.",
                ", ".join(missing),
            )

    mode = "LOCAL" if settings.USE_LOCAL_MODE else "PRODUCTION"
    logger.info("Celestia Memoria backend starting in %s mode", mode)

    # Initialize local database if in local mode
    if settings.USE_LOCAL_MODE:
        from app.db.local_client import init_local_db
        init_local_db()
        logger.info("Local SQLite database initialized")

    # Start file watcher if enabled
    watcher = None
    if settings.ENABLE_WATCHER:
        from app.watcher.directory_watcher import DirectoryWatcher
        from app.watcher.auto_ingest import ingest_local_file, scan_data_directory

        watcher = DirectoryWatcher()
        watcher.start(ingest_local_file)

        # Initial scan for unprocessed files
        pending = scan_data_directory()
        if pending:
            logger.info("Queuing %d existing files for ingestion", len(pending))
            import threading
            for file_path in pending:
                t = threading.Thread(target=ingest_local_file, args=(file_path,), daemon=True)
                t.start()

    yield

    # Shutdown
    if watcher and watcher.is_running:
        watcher.stop()
    logger.info("Celestia Memoria backend shutting down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Celestia Memoria AI Backend",
        description="RAG-powered AI assistant for Air Traffic Controllers — "
        "query ICAO, EASA, and local aerodrome regulatory documents.",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            settings.FRONTEND_URL,
            "http://localhost:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Authentication
    app.add_middleware(SupabaseAuthMiddleware)

    # LangServe chat endpoint
    from app.agents.graph import get_graph
    from langserve import add_routes

    add_routes(app, get_graph(), path="/chat")

    # API routes
    app.include_router(ingest_router)
    app.include_router(query_router)

    @app.get("/health", tags=["health"])
    async def health_check():
        return {
            "status": "ok",
            "version": "0.1.0",
            "mode": "local" if settings.USE_LOCAL_MODE else "production",
        }

    return app


# Module-level app instance for uvicorn
app = create_app()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
