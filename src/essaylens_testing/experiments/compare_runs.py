from __future__ import annotations

from pathlib import Path


def list_run_dirs(repo_root: Path) -> list[Path]:
    runs_dir = repo_root / "runs"
    if not runs_dir.exists():
        return []
    return sorted(path for path in runs_dir.iterdir() if path.is_dir())
