"""
file_handler.py
---------------
Core logic for resolving destination folders and safely moving files.
Handles:
  - Skipping temporary/in-progress download files
  - Resolving destination category folder
  - Duplicate filename resolution with sequential numbering
  - PermissionError and other OS-level errors
"""

import logging
import shutil
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def is_temp_file(file_path: Path, temp_extensions: list[str]) -> bool:
    """Return True if the file is a temporary/incomplete download artifact."""
    return file_path.suffix.lower() in temp_extensions


def is_file_ready(file_path: Path, stable_seconds: float = 1.5) -> bool:
    """
    Check whether a file is fully written by comparing its size over a short
    interval. Returns True when the file size is stable.

    This prevents acting on files that are still being written to disk.
    """
    try:
        size_before = file_path.stat().st_size
        time.sleep(stable_seconds)
        size_after = file_path.stat().st_size
        return size_before == size_after
    except (FileNotFoundError, PermissionError) as exc:
        logger.debug("Stability check skipped for %s: %s", file_path.name, exc)
        return False


def resolve_destination(file_path: Path, config: dict) -> Path:
    """
    Determine the destination folder for the given file based on its extension.
    Falls back to the 'Others' folder when the extension is unmapped.
    """
    ext = file_path.suffix.lower()
    extension_map: dict[str, Path] = config["extension_map"]
    others_folder: Path = Path(config["others_folder"])

    return extension_map.get(ext, others_folder)


def get_unique_path(destination_folder: Path, filename: str) -> Path:
    """
    Return a destination path that does not conflict with existing files.

    If `filename` already exists, appends an incrementing counter:
        document.pdf  ->  document_1.pdf  ->  document_2.pdf  ...
    """
    dest_path = destination_folder / filename
    if not dest_path.exists():
        return dest_path

    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1

    while True:
        new_name = f"{stem}_{counter}{suffix}"
        candidate = destination_folder / new_name
        if not candidate.exists():
            return candidate
        counter += 1


def move_file(file_path: Path, config: dict) -> bool:
    """
    Orchestrate the full move workflow for a single file:

      1. Skip temp/incomplete download files.
      2. Wait until the file is stable (fully written).
      3. Resolve destination category folder, create it if needed.
      4. Resolve a unique filename to avoid overwriting duplicates.
      5. Move the file and log the result.

    Returns True on success, False if the file was skipped or an error occurred.
    """
    temp_extensions: list[str] = config.get("temp_extensions", [])
    move_delay: float = float(config.get("move_delay_seconds", 1.5))

    # --- Guard: skip temp files ---
    if is_temp_file(file_path, temp_extensions):
        logger.debug("Skipping temporary file: %s", file_path.name)
        return False

    # --- Guard: skip if file no longer exists (e.g., deleted before we acted) ---
    if not file_path.exists():
        logger.warning("File no longer exists, skipping: %s", file_path)
        return False

    # --- Guard: wait for file to finish writing ---
    if not is_file_ready(file_path, stable_seconds=move_delay):
        logger.warning("File not stable yet, skipping: %s", file_path.name)
        return False

    # --- Resolve destination ---
    destination_folder = resolve_destination(file_path, config)

    try:
        destination_folder.mkdir(parents=True, exist_ok=True)
    except PermissionError as exc:
        logger.error(
            "Cannot create destination folder %s: %s", destination_folder, exc
        )
        return False

    # --- Handle duplicates ---
    unique_dest = get_unique_path(destination_folder, file_path.name)

    # --- Move ---
    try:
        shutil.move(str(file_path), str(unique_dest))
        logger.info(
            "Moved: '%s'  ->  '%s'",
            file_path.name,
            unique_dest.relative_to(Path(config["watch_folder"]).parent),
        )
        return True

    except PermissionError as exc:
        logger.error(
            "PermissionError moving '%s': %s (file may still be in use)",
            file_path.name,
            exc,
        )
    except FileNotFoundError as exc:
        logger.error("FileNotFoundError moving '%s': %s", file_path.name, exc)
    except OSError as exc:
        logger.error("OSError moving '%s': %s", file_path.name, exc)

    return False


def scan_existing_files(config: dict) -> None:
    """
    Scan the watch folder for files that already exist at startup and move them.

    Only processes direct children of watch_folder (non-recursive) and skips:
      - Sub-directories (category folders like Documents/, Images/, etc.)
      - Temporary/incomplete download files
    """
    watch_folder = Path(config["watch_folder"])
    temp_extensions: list[str] = config.get("temp_extensions", [])

    # Collect only files (not dirs) directly inside watch_folder
    existing_files = [
        p for p in watch_folder.iterdir()
        if p.is_file() and not is_temp_file(p, temp_extensions)
    ]

    if not existing_files:
        logger.info("Initial scan: no existing files found in %s", watch_folder)
        return

    logger.info(
        "Initial scan: found %d existing file(s) — organising now...",
        len(existing_files),
    )

    moved = 0
    skipped = 0
    for file_path in existing_files:
        success = move_file(file_path, config)
        if success:
            moved += 1
        else:
            skipped += 1

    logger.info(
        "Initial scan complete: %d moved, %d skipped.", moved, skipped
    )
