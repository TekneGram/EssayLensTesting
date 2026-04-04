from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    assets_dir: Path
    models_dir: Path
    configs_dir: Path
    config_models_dir: Path
    config_servers_dir: Path
    config_requests_dir: Path
    config_profiles_dir: Path
    config_presets_dir: Path
    prompts_dir: Path
    inputs_dir: Path
    third_party_dir: Path
    llama_cpp_dir: Path
    llama_server_binary: Path
    var_dir: Path
    run_dir: Path
    log_dir: Path
    runs_dir: Path


def get_project_paths() -> ProjectPaths:
    root = repo_root()
    third_party_dir = root / "third_party"
    llama_cpp_dir = third_party_dir / "llama-cpp-turboquant"

    return ProjectPaths(
        root=root,
        assets_dir=root / "assets",
        models_dir=root / "assets" / "models",
        configs_dir=root / "configs",
        config_models_dir=root / "configs" / "models",
        config_servers_dir=root / "configs" / "servers",
        config_requests_dir=root / "configs" / "requests",
        config_profiles_dir=root / "configs" / "profiles",
        config_presets_dir=root / "configs" / "presets",
        prompts_dir=root / "prompts",
        inputs_dir=root / "inputs",
        third_party_dir=third_party_dir,
        llama_cpp_dir=llama_cpp_dir,
        llama_server_binary=llama_cpp_dir / "build" / "bin" / "llama-server",
        var_dir=root / "var",
        run_dir=root / "var" / "run",
        log_dir=root / "var" / "log",
        runs_dir=root / "runs",
    )


def ensure_runtime_directories() -> ProjectPaths:
    paths = get_project_paths()
    paths.configs_dir.mkdir(parents=True, exist_ok=True)
    paths.config_models_dir.mkdir(parents=True, exist_ok=True)
    paths.config_servers_dir.mkdir(parents=True, exist_ok=True)
    paths.config_requests_dir.mkdir(parents=True, exist_ok=True)
    paths.config_profiles_dir.mkdir(parents=True, exist_ok=True)
    paths.config_presets_dir.mkdir(parents=True, exist_ok=True)
    paths.prompts_dir.mkdir(parents=True, exist_ok=True)
    paths.inputs_dir.mkdir(parents=True, exist_ok=True)
    paths.var_dir.mkdir(parents=True, exist_ok=True)
    paths.run_dir.mkdir(parents=True, exist_ok=True)
    paths.log_dir.mkdir(parents=True, exist_ok=True)
    paths.runs_dir.mkdir(parents=True, exist_ok=True)
    return paths
