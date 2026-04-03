from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class RunArtifactsWriter:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def create_run_dir(self, label: str | None = None) -> Path:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        suffix = f"_{label}" if label else ""
        run_dir = self.repo_root / "runs" / f"{timestamp}{suffix}"
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir

    def write_json(self, run_dir: Path, filename: str, payload: Any) -> None:
        (run_dir / filename).write_text(json.dumps(payload, indent=2, default=str))

    def write_text(self, run_dir: Path, filename: str, content: str) -> None:
        (run_dir / filename).write_text(content)

    def append_ndjson(self, run_dir: Path, filename: str, payload: Any) -> None:
        with (run_dir / filename).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
