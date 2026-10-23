"""
config_loader.py
----------------
Loads and validates config.json, resolving paths like ~/Downloads.
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config.json"


def load_config(config_path: Path = DEFAULT_CONFIG_PATH) -> dict:
    """Load configuration from a JSON file and resolve the watch_folder path."""
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Resolve ~ to actual home directory
    config["watch_folder"] = str(Path(config["watch_folder"]).expanduser().resolve())

    # Validate watch folder exists
    watch_folder = Path(config["watch_folder"])
    if not watch_folder.exists():
        logger.warning(
            "Watch folder does not exist, attempting to create: %s", watch_folder
        )
        watch_folder.mkdir(parents=True, exist_ok=True)

    # Build a flat reverse-lookup: extension -> category folder (absolute path)
    config["extension_map"] = _build_extension_map(config)

    # Resolve log file path relative to project root
    project_root = Path(__file__).parent.parent
    config["log_file"] = str(project_root / config.get("log_file", "logs/organizer.log"))

    return config


def _build_extension_map(config: dict) -> dict[str, Path]:
    """
    Build a flat dict mapping each extension to its destination Path.

    Example:
        {".pdf": Path("~/Downloads/Documents"), ".mp3": Path("~/Downloads/Audio"), ...}

    Extensions in 'Others' map to a generic Others folder. Extensions with no
    matching category fall back to 'Others' as well.
    """
    watch_folder = Path(config["watch_folder"])
    extension_map: dict[str, Path] = {}

    for category, extensions in config["categories"].items():
        dest_folder = watch_folder / category
        for ext in extensions:
            extension_map[ext.lower()] = dest_folder

    # 'Others' is the catch-all; store it separately for easy access
    config["others_folder"] = watch_folder / "Others"

    return extension_map
