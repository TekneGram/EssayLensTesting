from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ModelConfig:
    name: str
    path: Path
    alias: str | None = None
    chat_template: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ServerConfig:
    name: str
    host: str = "127.0.0.1"
    port: int = 8080
    device: str = "MTL0"
    ctx_size: int = 8192
    flash_attn: str = "auto"
    cache_type_k: str = "f16"
    cache_type_v: str = "f16"
    enable_props: bool = False
    enable_rerank: bool = False
    embeddings_only: bool = False
    extra_args: tuple[str, ...] = ()


@dataclass(frozen=True)
class RequestConfig:
    name: str
    api_mode: str = "chat"
    system_prompt: str | None = None
    system_prompt_file: str | None = None
    prompt_template: str | None = None
    prompt_file: str | None = None
    input_file: str | None = None
    max_tokens: int = 256
    temperature: float | None = 0.2
    top_k: int | None = None
    top_p: float | None = None
    min_p: float | None = None
    repeat_penalty: float | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    seed: int | None = None
    stop: tuple[str, ...] = ()
    stream: bool = False
    schema_file: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PresetConfig:
    name: str
    description: str | None = None
    model_overrides: dict[str, Any] = field(default_factory=dict)
    server_overrides: dict[str, Any] = field(default_factory=dict)
    request_overrides: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProfileConfig:
    name: str
    model: str
    server: str
    request: str
    presets: tuple[str, ...] = ()
    model_overrides: dict[str, Any] = field(default_factory=dict)
    server_overrides: dict[str, Any] = field(default_factory=dict)
    request_overrides: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResolvedConfig:
    profile_name: str
    preset_names: tuple[str, ...]
    model: ModelConfig
    server: ServerConfig
    request: RequestConfig
