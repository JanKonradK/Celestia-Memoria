"""File system watcher for automatic document ingestion from data/ directory."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from watchdog.events import FileCreatedEvent, FileMovedEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"


class PDFHandler(FileSystemEventHandler):
    """Handles new PDF files appearing in the data/ directory."""

    def __init__(self, ingest_callback):
        super().__init__()
        self._ingest = ingest_callback

    def on_created(self, event):
        if isinstance(event, FileCreatedEvent) and event.src_path.lower().endswith(".pdf"):
            logger.info("New PDF detected: %s", event.src_path)
            self._ingest(event.src_path)

    def on_moved(self, event):
        if isinstance(event, FileMovedEvent) and event.dest_path.lower().endswith(".pdf"):
            logger.info("PDF moved in: %s", event.dest_path)
            self._ingest(event.dest_path)


class DirectoryWatcher:
    """Watches the data/ directory for new PDF files and triggers auto-ingestion."""

    def __init__(self):
        self._observer: Observer | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self, ingest_callback) -> None:
        """Start watching the data/ directory.

        Args:
            ingest_callback: Function to call with the file path when a new PDF is detected.
        """
        if self._running:
            logger.warning("Directory watcher is already running")
            return

        if not DATA_DIR.exists():
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            logger.info("Created data directory: %s", DATA_DIR)

        handler = PDFHandler(ingest_callback)
        self._observer = Observer()
        self._observer.schedule(handler, str(DATA_DIR), recursive=True)
        self._observer.daemon = True
        self._observer.start()
        self._running = True

        logger.info("Directory watcher started: monitoring %s", DATA_DIR)

    def stop(self) -> None:
        """Stop watching."""
        if self._observer and self._running:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._running = False
            logger.info("Directory watcher stopped")

    @property
    def is_running(self) -> bool:
        return self._running
