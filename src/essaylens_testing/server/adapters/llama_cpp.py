from __future__ import annotations

from pathlib import Path

from essaylens_testing.config.schema import ProfileConfig


def find_default_binary(repo_root: Path) -> Path:
    candidates = [
        repo_root / "third_party/llama-cpp-turboquant/build/bin/llama-server",
        repo_root / "third_party/llama-cpp-turboquant/build/bin/Release/llama-server",
        repo_root / "third_party/llama-cpp-turboquant/build/bin/Debug/llama-server",
        repo_root / "third_party/llama-cpp-turboquant/build/llama-server",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def resolve_binary(profile: ProfileConfig, repo_root: Path) -> Path:
    if profile.server.binary:
        binary = Path(profile.server.binary)
        if not binary.is_absolute():
            binary = (repo_root / binary).resolve()
        return binary
    return find_default_binary(repo_root)


def build_server_command(profile: ProfileConfig, repo_root: Path) -> list[str]:
    binary = resolve_binary(profile, repo_root)
    model_path = Path(profile.model.model_path)
    if not model_path.is_absolute():
        model_path = (repo_root / model_path).resolve()

    cmd = [
        str(binary),
        "--host",
        profile.server.host,
        "--port",
        str(profile.server.port),
        "--model",
        str(model_path),
    ]

    alias = profile.model.alias or profile.model.name
    cmd.extend(["--alias", alias])

    if profile.server.threads is not None:
        cmd.extend(["--threads", str(profile.server.threads)])
    if profile.server.ctx_size is not None:
        cmd.extend(["--ctx-size", str(profile.server.ctx_size)])
    if profile.server.batch_size is not None:
        cmd.extend(["--batch-size", str(profile.server.batch_size)])
    if profile.server.ubatch_size is not None:
        cmd.extend(["--ubatch-size", str(profile.server.ubatch_size)])
    if profile.server.n_predict is not None:
        cmd.extend(["--n-predict", str(profile.server.n_predict)])
    if profile.model.n_gpu_layers is not None:
        cmd.extend(["--n-gpu-layers", str(profile.model.n_gpu_layers)])
    if profile.model.chat_template:
        cmd.extend(["--chat-template", profile.model.chat_template])

    if not profile.server.webui:
        cmd.append("--no-webui")

    cmd.extend(["--cache-type-k", profile.server.kv_cache.type_k])
    cmd.extend(["--cache-type-v", profile.server.kv_cache.type_v])

    if profile.server.kv_cache.prompt_cache:
        cmd.append("--cache-prompt")
    else:
        cmd.append("--no-cache-prompt")

    if profile.server.kv_cache.kv_offload:
        cmd.append("--kv-offload")
    else:
        cmd.append("--no-kv-offload")

    if profile.server.kv_cache.cache_reuse:
        cmd.extend(["--cache-reuse", str(profile.server.kv_cache.cache_reuse)])

    if profile.server.kv_cache.slot_save_path:
        slot_path = Path(profile.server.kv_cache.slot_save_path)
        if not slot_path.is_absolute():
            slot_path = (repo_root / slot_path).resolve()
        cmd.extend(["--slot-save-path", str(slot_path)])

    cmd.extend(profile.server.extra_args)
    return cmd


def base_url(profile: ProfileConfig) -> str:
    return f"http://{profile.server.host}:{profile.server.port}"
