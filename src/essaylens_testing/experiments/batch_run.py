from __future__ import annotations

from pathlib import Path


def iter_batch_file(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]
