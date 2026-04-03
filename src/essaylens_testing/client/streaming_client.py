from __future__ import annotations

import json
from typing import Any, Iterator
from urllib.request import Request, urlopen

from essaylens_testing.client.chat_client import ChatClient
from essaylens_testing.config.schema import ProfileConfig
from essaylens_testing.server.adapters.llama_cpp import base_url


class StreamingChatClient:
    def __init__(self, profile: ProfileConfig):
        self.profile = profile
        self.chat_client = ChatClient(profile)

    def stream(self, messages: list[dict[str, str]]) -> Iterator[dict[str, Any]]:
        payload = self.chat_client.build_payload(messages, stream=True)
        request = Request(
            url=f"{base_url(self.profile)}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.profile.request.timeout_seconds) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line or not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                yield json.loads(data)
