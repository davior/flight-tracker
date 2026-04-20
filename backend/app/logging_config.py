from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path


def setup_logging(
    level: str = "INFO",
    log_file: Path | None = None,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> None:
    root = logging.getLogger()
    if root.handlers:
        return

    root.setLevel(level.upper())
    fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)

        def _padded_namer(default_name: str) -> str:
            base, _, suffix = default_name.rpartition(".")
            return f"{base}.{int(suffix):03d}" if suffix.isdigit() else default_name

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.namer = _padded_namer
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)
