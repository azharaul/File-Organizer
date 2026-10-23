"""
main.py
-------
Entry point for the File Organizer.

Usage:
    python main.py                   # uses default config.json
    python main.py --config my.json  # uses a custom config file

Press Ctrl+C to stop.
"""

import argparse
import logging
import signal
import sys
import time
from pathlib import Path

from src.config_loader import load_config
from src.logger_setup import setup_logging
from src.file_handler import scan_existing_files
from src.watcher import create_observer

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="File Organizer — real-time Downloads folder sorter"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent / "config.json",
        help="Path to the JSON configuration file (default: config.json)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # --- Load config first (before logging so we know the log path) ---
    try:
        config = load_config(args.config)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

    # --- Configure logging ---
    setup_logging(
        log_file=config["log_file"],
        log_level=config.get("log_level", "INFO"),
    )

    logger.info("=" * 60)
    logger.info("File Organizer starting up")
    logger.info("Watching : %s", config["watch_folder"])
    logger.info("Log file : %s", config["log_file"])
    logger.info("=" * 60)

    # --- Scan files that already exist before we started watching ---
    logger.info("Running initial scan for existing files...")
    scan_existing_files(config)

    # --- Create and start the observer ---
    observer, handler = create_observer(config)

    # Graceful shutdown on SIGINT (Ctrl+C) and SIGTERM
    def _shutdown(signum, frame):  # noqa: ANN001
        logger.info("Shutdown signal received (%s), stopping...", signum)
        observer.stop()
        handler.shutdown()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    observer.start()
    logger.info("Observer started. Press Ctrl+C to stop.")

    try:
        while observer.is_alive():
            time.sleep(1)
    finally:
        observer.join()
        logger.info("File Organizer stopped. Goodbye.")


if __name__ == "__main__":
    main()


