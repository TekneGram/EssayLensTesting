from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from essaylens_testing.paths import ensure_runtime_directories


def create_run_directory(label: str) -> Path:
    paths = ensure_runtime_directories()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_label = "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in label).strip("-")
    run_dir = paths.runs_dir / f"{timestamp}-{safe_label or 'run'}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
