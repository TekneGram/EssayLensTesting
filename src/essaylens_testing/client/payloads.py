from __future__ import annotations

from typing import Any

from essaylens_testing.config.types import ModelConfig, RequestConfig


def build_request_payload(
    request: RequestConfig,
    *,
    model: ModelConfig,
    user_prompt: str,
    system_prompt: str | None = None,
    schema: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any]]:
    mode = request.api_mode
    if mode == "chat":
        payload = _chat_payload(request, model, user_prompt, system_prompt, schema)
        return "/v1/chat/completions", payload
    if mode == "completion":
        payload = _completion_payload(request, user_prompt, system_prompt, schema)
        return "/completion", payload
    raise RuntimeError(f"Unsupported api_mode '{mode}'")


def _chat_payload(
    request: RequestConfig,
    model: ModelConfig,
    user_prompt: str,
    system_prompt: str | None,
    schema: dict[str, Any] | None,
) -> dict[str, Any]:
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    payload: dict[str, Any] = {
        "model": model.alias or model.name,
        "messages": messages,
        "max_tokens": request.max_tokens,
    }
    _apply_sampling_fields(payload, request)
    if request.stream:
        payload["stream"] = True
    if schema is not None:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "essaylens_schema",
                "schema": schema,
            },
        }
    return payload


def _completion_payload(
    request: RequestConfig,
    user_prompt: str,
    system_prompt: str | None,
    schema: dict[str, Any] | None,
) -> dict[str, Any]:
    prompt = user_prompt if not system_prompt else f"System:\n{system_prompt}\n\nUser:\n{user_prompt}\n\nAssistant:\n"
    payload: dict[str, Any] = {
        "prompt": prompt,
        "n_predict": request.max_tokens,
    }
    _apply_sampling_fields(payload, request)
    if schema is not None:
        payload["json_schema"] = schema
    return payload


def _apply_sampling_fields(payload: dict[str, Any], request: RequestConfig) -> None:
    field_map = {
        "temperature": request.temperature,
        "top_k": request.top_k,
        "top_p": request.top_p,
        "min_p": request.min_p,
        "repeat_penalty": request.repeat_penalty,
        "presence_penalty": request.presence_penalty,
        "frequency_penalty": request.frequency_penalty,
        "seed": request.seed,
    }
    for key, value in field_map.items():
        if value is not None:
            payload[key] = value
    if request.stop:
        payload["stop"] = list(request.stop)
