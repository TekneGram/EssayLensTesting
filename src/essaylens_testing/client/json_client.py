from __future__ import annotations

from pathlib import Path

from essaylens_testing.client.chat_client import ChatClient
from essaylens_testing.config.schema import ProfileConfig


class JSONChatClient:
    def __init__(self, profile: ProfileConfig):
        self.profile = profile
        self.chat_client = ChatClient(profile)

    def chat(self, messages: list[dict[str, str]], schema_path: Path) -> dict:
        return self.chat_client.chat_json(messages, schema_path)
