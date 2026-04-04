from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ClientCapabilityMatrix:
    model_discovery: bool = True
    plain_completion: bool = True
    chat_completion: bool = True
    streaming_chat: bool = True
    json_chat: bool = True
    json_completion: bool = True
    embeddings: bool = True
    responses_api: bool = True
    anthropic_messages: bool = True
    anthropic_count_tokens: bool = True
    rerank: bool = True
    props_read: bool = True
    props_write: bool = True


REQUEST_MODES = (
    "models",
    "completion",
    "chat",
    "chat-stream",
    "chat-json",
    "completion-json",
    "embeddings",
    "responses",
    "anthropic-messages",
    "anthropic-count-tokens",
    "rerank",
    "props-get",
    "props-set",
)


def get_client_capability_matrix() -> ClientCapabilityMatrix:
    return ClientCapabilityMatrix()


def capability_payload() -> dict[str, object]:
    payload = asdict(get_client_capability_matrix())
    payload["request_modes"] = list(REQUEST_MODES)
    return payload
