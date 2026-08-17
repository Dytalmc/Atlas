from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path


def setup_logging(log_dir_name: str = "Logs") -> logging.Logger:
    """Configure a shared application logger that writes to a file in a Logs folder."""
    candidate = Path(log_dir_name).expanduser()
    if not candidate.is_absolute():
        workspace_root = Path(__file__).resolve().parent.parent
        candidate = workspace_root / candidate
    log_dir = candidate
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("atlas")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_name = log_dir / f"atlas_{datetime.now():%Y%m%d_%H%M%S}.log"
    file_handler = logging.FileHandler(file_name, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    logger.info("Logging initialized. File: %s", file_name)
    return logger
