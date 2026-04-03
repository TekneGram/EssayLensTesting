from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from essaylens_testing.config.schema import ProfileConfig
from essaylens_testing.server.adapters.llama_cpp import base_url


class ChatClient:
    def __init__(self, profile: ProfileConfig):
        self.profile = profile

    def build_payload(
        self,
        messages: list[dict[str, str]],
        *,
        stream: bool | None = None,
        json_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.profile.model.alias or self.profile.model.name,
            "messages": messages,
            "temperature": self.profile.request.temperature,
            "top_p": self.profile.request.top_p,
            "max_tokens": self.profile.request.max_tokens,
            "stream": self.profile.request.stream if stream is None else stream,
        }
        if self.profile.request.seed is not None:
            payload["seed"] = self.profile.request.seed
        if json_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "essaylens_schema",
                    "strict": True,
                    "schema": json_schema,
                },
            }
        return payload

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            url=f"{base_url(self.profile)}/v1/chat/completions",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.profile.request.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def chat(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        return self._post(self.build_payload(messages, stream=False))

    def chat_json(self, messages: list[dict[str, str]], schema_path: Path) -> dict[str, Any]:
        schema = json.loads(schema_path.read_text())
        return self._post(self.build_payload(messages, stream=False, json_schema=schema))
