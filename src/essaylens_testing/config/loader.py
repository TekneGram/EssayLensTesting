from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

from essaylens_testing.config.schema import (
    ContextConfig,
    KVCacheConfig,
    ModelConfig,
    ProfileConfig,
    RequestConfig,
    RuntimeConfig,
    ServerConfig,
)


class ConfigError(ValueError):
    """Raised when configuration is invalid."""


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Missing config file: {path}")
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _require_key(data: dict[str, Any], key: str, source: Path) -> Any:
    if key not in data:
        raise ConfigError(f"Missing '{key}' in {source}")
    return data[key]


class ConfigLoader:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.config_root = repo_root / "configs"

    def resolve_path(self, value: str) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        return (self.repo_root / path).resolve()

    def load_profile(self, profile_name: str) -> ProfileConfig:
        profile_path = self.config_root / "profiles" / f"{profile_name}.toml"
        profile_data = _load_toml(profile_path)

        model_name = _require_key(profile_data, "model", profile_path)
        server_name = _require_key(profile_data, "server", profile_path)
        request_name = _require_key(profile_data, "request", profile_path)
        preset_names = profile_data.get("presets", [])

        model_path = self.config_root / "models" / f"{model_name}.toml"
        server_path = self.config_root / "servers" / f"{server_name}.toml"
        request_path = self.config_root / "requests" / f"{request_name}.toml"
        preset_paths = [self.config_root / "presets" / f"{name}.toml" for name in preset_names]

        model_data = _load_toml(model_path)
        server_data = _load_toml(server_path)
        request_data = _load_toml(request_path)

        merged_server = server_data
        merged_request = request_data
        merged_context = profile_data.get("context", {})
        merged_runtime = profile_data.get("runtime", {})

        for preset_path in preset_paths:
            preset_data = _load_toml(preset_path)
            merged_server = _deep_merge(merged_server, preset_data.get("server", {}))
            merged_request = _deep_merge(merged_request, preset_data.get("request", {}))
            merged_context = _deep_merge(merged_context, preset_data.get("context", {}))
            merged_runtime = _deep_merge(merged_runtime, preset_data.get("runtime", {}))

        merged_server = _deep_merge(merged_server, profile_data.get("server_overrides", {}))
        merged_request = _deep_merge(merged_request, profile_data.get("request_overrides", {}))
        merged_context = _deep_merge(merged_context, profile_data.get("context", {}))
        merged_runtime = _deep_merge(merged_runtime, profile_data.get("runtime", {}))

        model = ModelConfig(
            name=_require_key(model_data, "name", model_path),
            model_path=_require_key(model_data, "model_path", model_path),
            alias=model_data.get("alias"),
            chat_template=model_data.get("chat_template"),
            n_gpu_layers=model_data.get("n_gpu_layers"),
            notes=model_data.get("notes"),
        )

        kv_cache_data = merged_server.get("kv_cache", {})
        server = ServerConfig(
            backend=_require_key(merged_server, "backend", server_path),
            host=merged_server.get("host", "127.0.0.1"),
            port=int(merged_server.get("port", 8080)),
            threads=merged_server.get("threads"),
            ctx_size=merged_server.get("ctx_size"),
            batch_size=merged_server.get("batch_size"),
            ubatch_size=merged_server.get("ubatch_size"),
            n_predict=merged_server.get("n_predict"),
            binary=merged_server.get("binary"),
            webui=bool(merged_server.get("webui", False)),
            extra_args=list(merged_server.get("extra_args", [])),
            kv_cache=KVCacheConfig(
                prompt_cache=bool(kv_cache_data.get("prompt_cache", True)),
                cache_reuse=int(kv_cache_data.get("cache_reuse", 0)),
                type_k=kv_cache_data.get("type_k", "f16"),
                type_v=kv_cache_data.get("type_v", "f16"),
                kv_offload=bool(kv_cache_data.get("kv_offload", True)),
                slot_save_path=kv_cache_data.get("slot_save_path"),
            ),
        )

        request = RequestConfig(
            temperature=float(merged_request.get("temperature", 0.2)),
            top_p=float(merged_request.get("top_p", 0.95)),
            max_tokens=int(merged_request.get("max_tokens", 512)),
            stream=bool(merged_request.get("stream", False)),
            timeout_seconds=int(merged_request.get("timeout_seconds", 600)),
            response_format=merged_request.get("response_format", "text"),
            json_schema_path=merged_request.get("json_schema_path"),
            seed=merged_request.get("seed"),
        )

        context = ContextConfig(
            max_input_chars=int(merged_context.get("max_input_chars", 24000)),
            strategy=merged_context.get("strategy", "truncate_head"),
            persist_messages=bool(merged_context.get("persist_messages", False)),
            system_prompt_path=merged_context.get("system_prompt_path"),
        )

        runtime = RuntimeConfig(
            pid_file=merged_runtime.get("pid_file", "var/run/essaylens-server.pid"),
            log_file=merged_runtime.get("log_file", "var/log/essaylens-server.log"),
            startup_timeout_seconds=int(merged_runtime.get("startup_timeout_seconds", 60)),
        )

        return ProfileConfig(
            name=profile_name,
            model=model,
            server=server,
            request=request,
            context=context,
            runtime=runtime,
            profile_path=profile_path,
            server_config_path=server_path,
            request_config_path=request_path,
            model_config_path=model_path,
            preset_paths=preset_paths,
        )

    def render_profile_json(self, profile_name: str) -> str:
        profile = self.load_profile(profile_name)
        return json.dumps(profile.to_dict(), indent=2, default=str)
