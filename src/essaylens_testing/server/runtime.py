from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from essaylens_testing.paths import get_project_paths


@dataclass(frozen=True)
class ServerRuntimeInfo:
    repo_root: Path
    llama_cpp_dir: Path
    llama_server_binary: Path
    binary_exists: bool


def get_server_runtime_info() -> ServerRuntimeInfo:
    paths = get_project_paths()
    return ServerRuntimeInfo(
        repo_root=paths.root,
        llama_cpp_dir=paths.llama_cpp_dir,
        llama_server_binary=paths.llama_server_binary,
        binary_exists=paths.llama_server_binary.exists(),
    )
