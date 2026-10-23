"""
watcher.py
----------
Watchdog event handler and observer setup.

DownloadEventHandler reacts to two events:
  - on_created : fired when a new file appears in the watch folder
  - on_moved   : fired when a browser renames a temp file to its final name
                 (e.g. Chrome: file.crdownload -> file.pdf)

Both events are routed through a ThreadPoolExecutor so that large files being
stability-checked don't block the watchdog observer thread.
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from watchdog.events import (
    FileCreatedEvent,
    FileMovedEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

from src.file_handler import is_temp_file, move_file

logger = logging.getLogger(__name__)

# Maximum number of concurrent file-move workers
MAX_WORKERS = 4


class DownloadEventHandler(FileSystemEventHandler):
    """Handles filesystem events inside the watched Downloads folder."""

    def __init__(self, config: dict) -> None:
        super().__init__()
        self.config = config
        self._executor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="organizer")
        # Track files already submitted to avoid duplicate processing
        self._in_progress: set[str] = set()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Watchdog event hooks
    # ------------------------------------------------------------------

    def on_created(self, event: FileCreatedEvent) -> None:
        """Triggered when a new file is created in the watch folder."""
        if event.is_directory:
            return
        self._submit(Path(event.src_path))

    def on_moved(self, event: FileMovedEvent) -> None:
        """
        Triggered when a file is renamed.

        Browsers like Chrome save files as `.crdownload` first, then rename
        them to the real filename once the download completes. We act on the
        destination path (the final file).
        """
        if event.is_directory:
            return
        dest_path = Path(event.dest_path)
        temp_exts: list[str] = self.config.get("temp_extensions", [])

        # Only care about the rename if the destination is NOT a temp file
        if not is_temp_file(dest_path, temp_exts):
            logger.debug("Rename detected (download complete?): %s", dest_path.name)
            self._submit(dest_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _submit(self, file_path: Path) -> None:
        """Submit a file-move task to the thread pool (deduplicated)."""
        key = str(file_path)
        with self._lock:
            if key in self._in_progress:
                logger.debug("Already queued, skipping: %s", file_path.name)
                return
            self._in_progress.add(key)

        self._executor.submit(self._process, file_path)

    def _process(self, file_path: Path) -> None:
        """Worker function: move the file and remove it from the in-progress set."""
        try:
            move_file(file_path, self.config)
        finally:
            with self._lock:
                self._in_progress.discard(str(file_path))

    def shutdown(self) -> None:
        """Gracefully shut down the thread pool."""
        logger.info("Shutting down worker pool...")
        self._executor.shutdown(wait=True)
        logger.info("Worker pool shut down.")


# ------------------------------------------------------------------
# Public factory
# ------------------------------------------------------------------

def create_observer(config: dict) -> tuple[Observer, DownloadEventHandler]:
    """
    Create and return a configured (but not yet started) watchdog Observer
    together with the event handler, so the caller can start/stop them.
    """
    watch_folder = config["watch_folder"]
    handler = DownloadEventHandler(config)
    observer = Observer()
    # recursive=False — we only watch the top-level Downloads folder
    observer.schedule(handler, path=watch_folder, recursive=False)
    logger.info("Observer scheduled for: %s", watch_folder)
    return observer, handler
