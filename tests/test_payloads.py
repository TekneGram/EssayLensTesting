from __future__ import annotations

import unittest

from essaylens_testing.client.payloads import build_request_payload
from essaylens_testing.config import resolve_profile
from essaylens_testing.io import load_schema_payload, load_system_prompt, read_text_file, render_user_prompt


class PayloadBuilderTests(unittest.TestCase):
    def test_chat_payload_contains_system_sampling_and_schema(self) -> None:
        resolved = resolve_profile("essay-feedback-json", preset_names=["kv-turbo3", "ctx-32k"])
        input_text = read_text_file("inputs/sample_essay.md")
        user_prompt = render_user_prompt(resolved.request, input_text=input_text)
        system_prompt = load_system_prompt(resolved.request)
        schema = load_schema_payload(resolved.request)

        path, payload = build_request_payload(
            resolved.request,
            model=resolved.model,
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            schema=schema,
        )

        self.assertEqual(path, "/v1/chat/completions")
        self.assertEqual(payload["model"], "local")
        self.assertEqual(payload["max_tokens"], 512)
        self.assertEqual(payload["temperature"], 0.0)
        self.assertIn("response_format", payload)
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertEqual(payload["messages"][1]["role"], "user")


if __name__ == "__main__":
    unittest.main()
