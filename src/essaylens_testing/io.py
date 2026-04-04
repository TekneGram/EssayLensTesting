from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from essaylens_testing.config.types import RequestConfig
from essaylens_testing.paths import ProjectPaths, get_project_paths


def resolve_text_path(raw_path: str, paths: ProjectPaths | None = None) -> Path:
    resolved_paths = paths or get_project_paths()
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    local_candidate = Path.cwd() / candidate
    if local_candidate.exists():
        return local_candidate
    return resolved_paths.root / candidate


def read_text_file(raw_path: str, paths: ProjectPaths | None = None) -> str:
    path = resolve_text_path(raw_path, paths)
    if path.suffix.lower() not in {".md", ".txt", ".json", ".prompt"}:
        raise RuntimeError(f"Unsupported text file type for {path}")
    return path.read_text(encoding="utf-8")


def render_user_prompt(
    request: RequestConfig,
    *,
    input_text: str | None,
    paths: ProjectPaths | None = None,
) -> str:
    template = request.prompt_template
    if request.prompt_file:
        template = read_text_file(request.prompt_file, paths)
    if template:
        return template.replace("{{input}}", input_text or "")
    if input_text is not None:
        return input_text
    raise RuntimeError("No prompt_template, prompt_file, or input text was provided.")


def load_system_prompt(request: RequestConfig, paths: ProjectPaths | None = None) -> str | None:
    if request.system_prompt_file:
        return read_text_file(request.system_prompt_file, paths).strip() or None
    if request.system_prompt:
        return request.system_prompt.strip() or None
    return None


def load_schema_payload(request: RequestConfig, paths: ProjectPaths | None = None) -> dict[str, Any] | None:
    if not request.schema_file:
        return None
    raw = read_text_file(request.schema_file, paths)
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise RuntimeError("Schema file must contain a JSON object.")
    return payload
