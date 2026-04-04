from __future__ import annotations

import json
from dataclasses import replace
from typing import Any, Callable

from essaylens_testing.client.http import (
    ServerConnection,
    get_models,
    get_props,
    post_anthropic_count_tokens,
    post_anthropic_messages,
    post_chat,
    post_chat_json,
    post_chat_stream,
    post_completion,
    post_completion_json,
    post_embeddings,
    post_props,
    post_rerank,
    post_responses,
)
from essaylens_testing.server.manager import ServerLaunchOptions, start_server, stop_server


ModeHandler = Callable[[ServerConnection], Any]


def verify_all_server_modes(options: ServerLaunchOptions) -> dict[str, Any]:
    runs = [
        ("core", options, _core_modes()),
        ("props", replace(options, enable_props=True), _props_modes()),
        ("rerank", replace(options, enable_rerank=True), _rerank_modes()),
        ("embeddings", replace(options, embeddings_only=True), _embeddings_modes()),
    ]

    results: list[dict[str, Any]] = []
    overall_ok = True
    for index, (suffix, run_options, modes) in enumerate(runs):
        run_result = _run_verification_group(
            replace(
                run_options,
                name=f"{options.name}-{suffix}",
                port=options.port + index,
            ),
            modes,
        )
        results.append(run_result)
        overall_ok = overall_ok and bool(run_result["ok"])

    return {
        "ok": overall_ok,
        "requested_device": options.device,
        "runs": results,
    }


def _run_verification_group(
    options: ServerLaunchOptions,
    modes: list[tuple[str, ModeHandler]],
) -> dict[str, Any]:
    used_device = options.device
    start_error: str | None = None

    try:
        start_server(options)
    except Exception as exc:
        start_error = str(exc)
        if options.device == "none":
            return _failed_run_result(options.name, used_device, start_error)
        used_device = "none"
        options = replace(options, device="none")
        try:
            start_server(options)
        except Exception as retry_exc:
            return _failed_run_result(options.name, used_device, str(retry_exc), start_error)

    connection = ServerConnection(host=options.host, port=options.port)
    mode_results: list[dict[str, Any]] = []
    ok = True
    try:
        for mode_name, handler in modes:
            try:
                result = handler(connection)
                _validate_mode_result(mode_name, result)
                mode_results.append({"mode": mode_name, "ok": True})
            except Exception as exc:
                mode_results.append({"mode": mode_name, "ok": False, "error": str(exc)})
                ok = False
    finally:
        stop_server(options.name)

    run_result: dict[str, Any] = {
        "name": options.name,
        "ok": ok,
        "device": used_device,
        "modes": mode_results,
    }
    if start_error is not None and used_device == "none":
        run_result["fallback_reason"] = start_error
    return run_result


def _failed_run_result(
    name: str,
    device: str,
    error: str,
    fallback_reason: str | None = None,
) -> dict[str, Any]:
    result = {
        "name": name,
        "ok": False,
        "device": device,
        "error": error,
        "modes": [],
    }
    if fallback_reason is not None:
        result["fallback_reason"] = fallback_reason
    return result


def _core_modes() -> list[tuple[str, ModeHandler]]:
    return [
        ("models", get_models),
        ("completion", lambda connection: post_completion(connection, "Say hello in one short sentence.")),
        ("chat", lambda connection: post_chat(connection, "Say hello in one short sentence.")),
        ("chat-stream", lambda connection: post_chat_stream(connection, "Count from 1 to 3.")),
        (
            "chat-json",
            lambda connection: post_chat_json(
                connection,
                "Return a JSON object with answer set to hello.",
            ),
        ),
        (
            "completion-json",
            lambda connection: post_completion_json(
                connection,
                "Return a JSON object with answer set to hello.",
            ),
        ),
        (
            "responses",
            lambda connection: post_responses(connection, "Say hello in one short sentence."),
        ),
        (
            "anthropic-messages",
            lambda connection: post_anthropic_messages(connection, "Say hello in one short sentence."),
        ),
        (
            "anthropic-count-tokens",
            lambda connection: post_anthropic_count_tokens(connection, "Say hello in one short sentence."),
        ),
    ]


def _props_modes() -> list[tuple[str, ModeHandler]]:
    return [
        ("props-get", get_props),
        ("props-set", post_props),
    ]


def _rerank_modes() -> list[tuple[str, ModeHandler]]:
    return [
        ("rerank", lambda connection: post_rerank(connection, "Which sentence is about essay feedback?")),
    ]


def _embeddings_modes() -> list[tuple[str, ModeHandler]]:
    return [
        (
            "embeddings",
            lambda connection: post_embeddings(connection, "Essay feedback should be specific."),
        ),
    ]


def _validate_mode_result(mode: str, result: Any) -> None:
    if mode == "models":
        if not _has_sequence(result, "data"):
            raise RuntimeError("models response was empty")
        return
    if mode == "chat-stream":
        if not isinstance(result, list) or not result:
            raise RuntimeError("stream returned no events")
        if not any(_stream_event_has_content(item) for item in result):
            raise RuntimeError("stream returned no content-bearing events")
        return
    if mode in {"chat-json", "completion-json"}:
        text = _extract_text(result)
        if not text:
            raise RuntimeError("JSON mode returned no text")
        payload = json.loads(text)
        if not isinstance(payload, dict) or not payload.get("answer"):
            raise RuntimeError("JSON mode did not return an answer field")
        return
    if mode == "embeddings":
        data = result.get("data") if isinstance(result, dict) else None
        if not isinstance(data, list) or not data:
            raise RuntimeError("embeddings response was empty")
        first_item = data[0]
        if not isinstance(first_item, dict):
            raise RuntimeError("embeddings response item was invalid")
        embedding = first_item.get("embedding")
        if not isinstance(embedding, list) or not embedding:
            raise RuntimeError("embedding vector was empty")
        return
    if mode == "rerank":
        if not _has_sequence(result, "results") and not _has_sequence(result, "data"):
            raise RuntimeError("rerank response was empty")
        return
    if mode in {"props-get", "props-set"}:
        if not isinstance(result, dict):
            raise RuntimeError("props response was not JSON")
        return
    if mode == "anthropic-count-tokens":
        if not _contains_int(result):
            raise RuntimeError("token count response had no integer fields")
        return

    text = _extract_text(result)
    if not text:
        raise RuntimeError(f"{mode} returned no text")


def _has_sequence(result: Any, key: str) -> bool:
    if not isinstance(result, dict):
        return False
    value = result.get(key)
    return isinstance(value, list) and len(value) > 0


def _contains_int(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, dict):
        return any(_contains_int(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_int(item) for item in value)
    return False


def _stream_event_has_content(value: Any) -> bool:
    if isinstance(value, str):
        return value != "[DONE]" and bool(value.strip())
    return bool(_extract_text(value))


def _extract_text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, list):
        for item in value:
            text = _extract_text(item)
            if text:
                return text
        return None
    if not isinstance(value, dict):
        return None

    block_type = value.get("type")
    if block_type in {"text", "output_text"}:
        text = value.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
    if block_type == "thinking":
        thinking = value.get("thinking")
        if isinstance(thinking, str) and thinking.strip():
            return thinking.strip()

    for key in ("text", "content", "output_text", "response"):
        text = value.get(key)
        extracted = _extract_text(text)
        if extracted:
            return extracted

    choices = value.get("choices")
    if isinstance(choices, list):
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            text = _extract_text(choice.get("text"))
            if text:
                return text
            text = _extract_text(choice.get("message"))
            if text:
                return text
            text = _extract_text(choice.get("delta"))
            if text:
                return text

    message = value.get("message")
    text = _extract_text(message)
    if text:
        return text

    delta = value.get("delta")
    text = _extract_text(delta)
    if text:
        return text

    output = value.get("output")
    text = _extract_text(output)
    if text:
        return text

    part = value.get("part")
    text = _extract_text(part)
    if text:
        return text

    data = value.get("data")
    text = _extract_text(data)
    if text:
        return text

    return None
