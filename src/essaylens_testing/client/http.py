from __future__ import annotations

import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ServerConnection:
    host: str
    port: int

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def start_hint(self) -> str:
        return (
            "Start a server first, for example: "
            f"`essaylens-server start --port {self.port}`"
        )


def request_json(
    connection: ServerConnection,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    timeout_seconds: float = 120.0,
) -> Any:
    url = f"{connection.base_url}{path}"
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, method=method.upper(), headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
            if not raw:
                return {}
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method.upper()} {path} failed with {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(_format_connection_error(connection, method.upper(), path, exc)) from exc


def request_stream(
    connection: ServerConnection,
    path: str,
    payload: dict[str, Any],
    timeout_seconds: float = 120.0,
) -> list[dict[str, Any] | str]:
    url = f"{connection.base_url}{path}"
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
        },
    )
    events: list[dict[str, Any] | str] = []
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    events.append(data)
                    continue
                try:
                    events.append(json.loads(data))
                except json.JSONDecodeError:
                    events.append(data)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"POST {path} stream failed with {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(_format_connection_error(connection, "POST", path, exc)) from exc
    return events


def get_models(connection: ServerConnection) -> Any:
    return request_json(connection, "GET", "/v1/models")


def post_completion(connection: ServerConnection, prompt: str) -> Any:
    return request_json(
        connection,
        "POST",
        "/completion",
        {"prompt": prompt, "n_predict": 32, "temperature": 0.2},
    )


def post_chat(connection: ServerConnection, content: str) -> Any:
    return request_json(
        connection,
        "POST",
        "/v1/chat/completions",
        {
            "model": "local",
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 64,
            "temperature": 0.2,
        },
    )


def post_chat_stream(connection: ServerConnection, content: str) -> list[dict[str, Any] | str]:
    return request_stream(
        connection,
        "/v1/chat/completions",
        {
            "model": "local",
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 64,
            "temperature": 0.2,
            "stream": True,
        },
    )


def post_chat_json(connection: ServerConnection, content: str) -> Any:
    schema = {
        "type": "object",
        "properties": {"answer": {"type": "string"}},
        "required": ["answer"],
        "additionalProperties": False,
    }
    return request_json(
        connection,
        "POST",
        "/v1/chat/completions",
        {
            "model": "local",
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 64,
            "temperature": 0.2,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "answer_payload", "schema": schema},
            },
        },
    )


def post_completion_json(connection: ServerConnection, prompt: str) -> Any:
    return request_json(
        connection,
        "POST",
        "/completion",
        {
            "prompt": prompt,
            "n_predict": 64,
            "temperature": 0.2,
            "json_schema": {
                "type": "object",
                "properties": {"answer": {"type": "string"}},
                "required": ["answer"],
                "additionalProperties": False,
            },
        },
    )


def post_embeddings(connection: ServerConnection, text: str) -> Any:
    return request_json(
        connection,
        "POST",
        "/v1/embeddings",
        {"input": text},
    )


def post_responses(connection: ServerConnection, text: str) -> Any:
    return request_json(
        connection,
        "POST",
        "/v1/responses",
        {
            "model": "local",
            "input": text,
            "max_output_tokens": 64,
        },
    )


def post_anthropic_messages(connection: ServerConnection, text: str) -> Any:
    return request_json(
        connection,
        "POST",
        "/v1/messages",
        {
            "model": "local",
            "messages": [{"role": "user", "content": text}],
            "max_tokens": 64,
        },
    )


def post_anthropic_count_tokens(connection: ServerConnection, text: str) -> Any:
    return request_json(
        connection,
        "POST",
        "/v1/messages/count_tokens",
        {
            "model": "local",
            "messages": [{"role": "user", "content": text}],
        },
    )


def post_rerank(connection: ServerConnection, query: str) -> Any:
    return request_json(
        connection,
        "POST",
        "/v1/rerank",
        {
            "model": "local",
            "query": query,
            "documents": [
                "Essay feedback should be specific and actionable.",
                "Bananas are usually yellow.",
            ],
        },
    )


def get_props(connection: ServerConnection) -> Any:
    return request_json(connection, "GET", "/props")


def post_props(connection: ServerConnection) -> Any:
    return request_json(connection, "POST", "/props", {})


def _format_connection_error(
    connection: ServerConnection,
    method: str,
    path: str,
    exc: urllib.error.URLError,
) -> str:
    reason = exc.reason
    if isinstance(reason, ConnectionRefusedError):
        return (
            f"{method} {path} could not connect to {connection.base_url}. "
            f"Connection refused. {connection.start_hint}"
        )
    if isinstance(reason, socket.timeout):
        return (
            f"{method} {path} timed out connecting to {connection.base_url}. "
            f"Verify the server is running and healthy."
        )
    return (
        f"{method} {path} could not connect to {connection.base_url}: {reason}. "
        f"{connection.start_hint}"
    )
