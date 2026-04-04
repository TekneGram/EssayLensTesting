from __future__ import annotations

import tomllib
from dataclasses import asdict
from pathlib import Path
from typing import Any

from essaylens_testing.config.types import (
    ModelConfig,
    PresetConfig,
    ProfileConfig,
    RequestConfig,
    ResolvedConfig,
    ServerConfig,
)
from essaylens_testing.paths import ProjectPaths, get_project_paths


def load_model_config(name: str, paths: ProjectPaths | None = None) -> ModelConfig:
    raw = _read_named_toml(_paths(paths).config_models_dir, name)
    return _model_from_raw(name, raw, _paths(paths))


def load_server_config(name: str, paths: ProjectPaths | None = None) -> ServerConfig:
    raw = _read_named_toml(_paths(paths).config_servers_dir, name)
    return _server_from_raw(name, raw)


def load_request_config(name: str, paths: ProjectPaths | None = None) -> RequestConfig:
    raw = _read_named_toml(_paths(paths).config_requests_dir, name)
    return _request_from_raw(name, raw)


def load_preset_config(name: str, paths: ProjectPaths | None = None) -> PresetConfig:
    raw = _read_named_toml(_paths(paths).config_presets_dir, name)
    return PresetConfig(
        name=name,
        description=_pop_optional_str(raw, "description"),
        model_overrides=_dict_value(raw.pop("model", {})),
        server_overrides=_dict_value(raw.pop("server", {})),
        request_overrides=_dict_value(raw.pop("request", {})),
    )


def load_profile_config(name: str, paths: ProjectPaths | None = None) -> ProfileConfig:
    raw = _read_named_toml(_paths(paths).config_profiles_dir, name)
    return ProfileConfig(
        name=name,
        model=_required_str(raw, "model"),
        server=_required_str(raw, "server"),
        request=_required_str(raw, "request"),
        presets=_tuple_of_strings(raw.pop("presets", ())),
        model_overrides=_dict_value(raw.pop("model_overrides", {})),
        server_overrides=_dict_value(raw.pop("server_overrides", {})),
        request_overrides=_dict_value(raw.pop("request_overrides", {})),
    )


def resolve_profile(
    profile_name: str,
    *,
    preset_names: list[str] | tuple[str, ...] = (),
    cli_overrides: dict[str, dict[str, Any]] | None = None,
    paths: ProjectPaths | None = None,
) -> ResolvedConfig:
    resolved_paths = _paths(paths)
    profile = load_profile_config(profile_name, resolved_paths)

    model_data = asdict(load_model_config(profile.model, resolved_paths))
    server_data = asdict(load_server_config(profile.server, resolved_paths))
    request_data = asdict(load_request_config(profile.request, resolved_paths))

    _merge_into(model_data, profile.model_overrides)
    _merge_into(server_data, profile.server_overrides)
    _merge_into(request_data, profile.request_overrides)

    ordered_presets = [*profile.presets, *preset_names]
    for preset_name in ordered_presets:
        preset = load_preset_config(preset_name, resolved_paths)
        _merge_into(model_data, preset.model_overrides)
        _merge_into(server_data, preset.server_overrides)
        _merge_into(request_data, preset.request_overrides)

    if cli_overrides:
        _merge_into(model_data, cli_overrides.get("model", {}))
        _merge_into(server_data, cli_overrides.get("server", {}))
        _merge_into(request_data, cli_overrides.get("request", {}))

    model = _model_from_data(model_data, resolved_paths)
    server = _server_from_data(server_data)
    request = _request_from_data(request_data)
    return ResolvedConfig(
        profile_name=profile_name,
        preset_names=tuple(ordered_presets),
        model=model,
        server=server,
        request=request,
    )


def resolved_config_payload(config: ResolvedConfig) -> dict[str, Any]:
    return {
        "profile": config.profile_name,
        "presets": list(config.preset_names),
        "model": _serialize_dataclass(config.model),
        "server": _serialize_dataclass(config.server),
        "request": _serialize_dataclass(config.request),
    }


def parse_cli_overrides(values: list[str] | None) -> dict[str, dict[str, Any]]:
    overrides: dict[str, dict[str, Any]] = {"model": {}, "server": {}, "request": {}}
    for value in values or []:
        key, separator, raw_value = value.partition("=")
        if not separator:
            raise RuntimeError(f"Invalid override '{value}'. Expected section.key=value.")
        section, dot, field_name = key.partition(".")
        if section not in overrides or not dot or not field_name:
            raise RuntimeError(f"Invalid override '{value}'. Expected section.key=value.")
        overrides[section][field_name] = _coerce_cli_value(raw_value)
    return overrides


def _paths(paths: ProjectPaths | None) -> ProjectPaths:
    return paths or get_project_paths()


def _read_named_toml(directory: Path, name: str) -> dict[str, Any]:
    path = directory / f"{name}.toml"
    if not path.exists():
        raise FileNotFoundError(f"Config '{name}' not found at {path}")
    with path.open("rb") as handle:
        payload = tomllib.load(handle)
    if not isinstance(payload, dict):
        raise RuntimeError(f"Invalid config file at {path}")
    return payload


def _model_from_raw(name: str, raw: dict[str, Any], paths: ProjectPaths) -> ModelConfig:
    payload = {"name": name, **raw}
    return _model_from_data(payload, paths)


def _model_from_data(data: dict[str, Any], paths: ProjectPaths) -> ModelConfig:
    raw_path = data.get("path")
    if not raw_path:
        raise RuntimeError(f"Model config '{data.get('name', '<unknown>')}' is missing path")
    return ModelConfig(
        name=str(data["name"]),
        path=_resolve_project_path(paths, str(raw_path)),
        alias=_optional_str(data.get("alias")),
        chat_template=_optional_str(data.get("chat_template")),
        metadata=_dict_value(data.get("metadata", {})),
    )


def _server_from_raw(name: str, raw: dict[str, Any]) -> ServerConfig:
    payload = {"name": name, **raw}
    return _server_from_data(payload)


def _server_from_data(data: dict[str, Any]) -> ServerConfig:
    return ServerConfig(
        name=str(data["name"]),
        host=str(data.get("host", "127.0.0.1")),
        port=int(data.get("port", 8080)),
        device=str(data.get("device", "MTL0")),
        ctx_size=int(data.get("ctx_size", 8192)),
        flash_attn=str(data.get("flash_attn", "auto")),
        cache_type_k=str(data.get("cache_type_k", "f16")),
        cache_type_v=str(data.get("cache_type_v", "f16")),
        enable_props=bool(data.get("enable_props", False)),
        enable_rerank=bool(data.get("enable_rerank", False)),
        embeddings_only=bool(data.get("embeddings_only", False)),
        extra_args=_tuple_of_strings(data.get("extra_args", ())),
    )


def _request_from_raw(name: str, raw: dict[str, Any]) -> RequestConfig:
    payload = {"name": name, **raw}
    return _request_from_data(payload)


def _request_from_data(data: dict[str, Any]) -> RequestConfig:
    return RequestConfig(
        name=str(data["name"]),
        api_mode=str(data.get("api_mode", "chat")),
        system_prompt=_optional_str(data.get("system_prompt")),
        system_prompt_file=_optional_str(data.get("system_prompt_file")),
        prompt_template=_optional_str(data.get("prompt_template")),
        prompt_file=_optional_str(data.get("prompt_file")),
        input_file=_optional_str(data.get("input_file")),
        max_tokens=int(data.get("max_tokens", 256)),
        temperature=_optional_float(data.get("temperature")),
        top_k=_optional_int(data.get("top_k")),
        top_p=_optional_float(data.get("top_p")),
        min_p=_optional_float(data.get("min_p")),
        repeat_penalty=_optional_float(data.get("repeat_penalty")),
        presence_penalty=_optional_float(data.get("presence_penalty")),
        frequency_penalty=_optional_float(data.get("frequency_penalty")),
        seed=_optional_int(data.get("seed")),
        stop=_tuple_of_strings(data.get("stop", ())),
        stream=bool(data.get("stream", False)),
        schema_file=_optional_str(data.get("schema_file")),
        metadata=_dict_value(data.get("metadata", {})),
    )


def _merge_into(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge_into(target[key], value)
            continue
        target[key] = value


def _resolve_project_path(paths: ProjectPaths, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return paths.root / candidate


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.pop(key, None)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"Missing required string field '{key}'")
    return value


def _pop_optional_str(payload: dict[str, Any], key: str) -> str | None:
    return _optional_str(payload.pop(key, None))


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise RuntimeError(f"Expected string value, got {type(value).__name__}")
    stripped = value.strip()
    return stripped or None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _tuple_of_strings(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if not isinstance(value, list) and not isinstance(value, tuple):
        raise RuntimeError(f"Expected list of strings, got {type(value).__name__}")
    return tuple(str(item) for item in value)


def _dict_value(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected table value, got {type(value).__name__}")
    return dict(value)


def _coerce_cli_value(raw_value: str) -> Any:
    lowered = raw_value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "none" or lowered == "null":
        return None
    if "," in raw_value:
        return tuple(part.strip() for part in raw_value.split(",") if part.strip())
    try:
        return int(raw_value)
    except ValueError:
        pass
    try:
        return float(raw_value)
    except ValueError:
        pass
    return raw_value


def _serialize_dataclass(value: Any) -> dict[str, Any]:
    payload = asdict(value)
    for key, item in tuple(payload.items()):
        if isinstance(item, Path):
            payload[key] = str(item)
    return payload
