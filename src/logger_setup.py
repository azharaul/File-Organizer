"""
logger_setup.py
---------------
Centralised logging configuration.
Writes to both the console (stdout) and a rotating log file.
"""

import logging
import logging.handlers
from pathlib import Path


def setup_logging(log_file: str, log_level: str = "INFO") -> None:
    """
    Configure the root logger with:
      - A StreamHandler  (coloured INFO+ output to the terminal)
      - A RotatingFileHandler (full DEBUG+ output to log_file, 5 MB × 3 backups)
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # handlers filter independently

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # --- Console handler ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)

    # --- Rotating file handler ---
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Avoid adding duplicate handlers on re-import
    if not root_logger.handlers:
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
