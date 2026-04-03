from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any


def _drop_none(value: Any) -> Any:
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, dict):
        return {key: _drop_none(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [_drop_none(item) for item in value]
    return value


@dataclass
class ModelConfig:
    name: str
    model_path: str
    alias: str | None = None
    chat_template: str | None = None
    n_gpu_layers: int | str | None = None
    notes: str | None = None


@dataclass
class KVCacheConfig:
    prompt_cache: bool = True
    cache_reuse: int = 0
    type_k: str = "f16"
    type_v: str = "f16"
    kv_offload: bool = True
    slot_save_path: str | None = None


@dataclass
class ServerConfig:
    backend: str
    host: str = "127.0.0.1"
    port: int = 8080
    threads: int | None = None
    ctx_size: int | None = None
    batch_size: int | None = None
    ubatch_size: int | None = None
    n_predict: int | None = None
    binary: str | None = None
    webui: bool = False
    extra_args: list[str] = field(default_factory=list)
    kv_cache: KVCacheConfig = field(default_factory=KVCacheConfig)


@dataclass
class RequestConfig:
    temperature: float = 0.2
    top_p: float = 0.95
    max_tokens: int = 512
    stream: bool = False
    timeout_seconds: int = 600
    response_format: str = "text"
    json_schema_path: str | None = None
    seed: int | None = None


@dataclass
class ContextConfig:
    max_input_chars: int = 24000
    strategy: str = "truncate_head"
    persist_messages: bool = False
    system_prompt_path: str | None = None


@dataclass
class RuntimeConfig:
    pid_file: str = "var/run/essaylens-server.pid"
    log_file: str = "var/log/essaylens-server.log"
    startup_timeout_seconds: int = 60


@dataclass
class ProfileConfig:
    name: str
    model: ModelConfig
    server: ServerConfig
    request: RequestConfig
    context: ContextConfig
    runtime: RuntimeConfig
    profile_path: Path
    server_config_path: Path
    request_config_path: Path
    model_config_path: Path
    preset_paths: list[Path] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _drop_none(self)
